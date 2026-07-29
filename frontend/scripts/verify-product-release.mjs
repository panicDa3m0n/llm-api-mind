#!/usr/bin/env node

import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const options = parseArguments(process.argv.slice(2));
const surface = requireOption(options, "surface");
const directory = resolve(frontendRoot, requireOption(options, "dir"));

const surfaceContract = {
  vps: {
    apiBaseUrl: "/scarlet-api",
    assetBasePath: "/scarlet/"
  },
  android: {
    apiBaseUrl: "https://honeylabs.cloud/scarlet-api",
    assetBasePath: "/"
  }
}[surface];

if (!surfaceContract) {
  fail(`Unsupported surface '${surface}'. Use 'vps' or 'android'.`);
}

const packageInfo = JSON.parse(
  readFileSync(resolve(frontendRoot, "package.json"), "utf8")
);
const indexPath = resolve(directory, "index.html");
if (!existsSync(indexPath)) {
  fail(`Missing built index: ${indexPath}`);
}

const index = readFileSync(indexPath, "utf8");
const references = extractStaticReferences(index);
if (references.length === 0) {
  fail(`No static assets were found in ${indexPath}.`);
}

const resolvedAssets = references.map((reference) => ({
  reference,
  path: resolveReference(directory, reference, surfaceContract.assetBasePath)
}));
for (const asset of resolvedAssets) {
  if (!existsSync(asset.path) || !statSync(asset.path).isFile()) {
    fail(`Referenced asset is missing: ${asset.reference} -> ${asset.path}`);
  }
}

const bundleFiles = listFiles(directory);
const bundleText = bundleFiles
  .filter((file) => /\.(?:js|css)$/i.test(file))
  .map((file) => readFileSync(file, "utf8"))
  .join("\n");

if (!bundleText.includes(surfaceContract.apiBaseUrl)) {
  fail(
    `Expected API base '${surfaceContract.apiBaseUrl}' is absent from the ${surface} bundle.`
  );
}

for (const fragment of [
  "/api/chat/sessions",
  "/turn/stream-live",
  "/api/dashboard/memories",
  `Versione ${packageInfo.version}`
]) {
  if (!bundleText.includes(fragment)) {
    fail(`Product UI contract fragment is absent from the bundle: ${fragment}`);
  }
}

const manifest = {
  schema: "scarlet-product-release-v1",
  product_version: packageInfo.version,
  source_commit: sourceCommit(),
  surface,
  asset_base_path: surfaceContract.assetBasePath,
  api_base_url: surfaceContract.apiBaseUrl,
  index_sha256: sha256(indexPath),
  static_references: references.sort()
};

if (surface === "android") {
  const androidVersion = inspectAndroidVersion();
  manifest.android = androidVersion;

  if (androidVersion.versionName !== packageInfo.version) {
    fail(
      `Android versionName ${androidVersion.versionName} does not match frontend version ${packageInfo.version}.`
    );
  }

  if (options.apk) {
    inspectAndroidArtifact(resolve(frontendRoot, options.apk), androidVersion);
  }
}

const manifestPath = resolve(directory, "release-manifest.json");
if (options.writeManifest) {
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
} else if (existsSync(manifestPath)) {
  verifyExistingManifest(manifestPath, manifest);
}

process.stdout.write(
  `${JSON.stringify(
    {
      ok: true,
      bundle_directory: relative(frontendRoot, directory),
      manifest_path: relative(frontendRoot, manifestPath),
      referenced_assets: resolvedAssets.length,
      surface,
      version: packageInfo.version,
      wrote_manifest: Boolean(options.writeManifest)
    },
    null,
    2
  )}\n`
);

function parseArguments(argumentsList) {
  const parsed = {};
  for (let index = 0; index < argumentsList.length; index += 1) {
    const argument = argumentsList[index];
    if (!argument.startsWith("--")) {
      fail(`Unexpected argument: ${argument}`);
    }
    const key = argument.slice(2);
    if (key === "write-manifest") {
      parsed.writeManifest = true;
      continue;
    }
    const value = argumentsList[index + 1];
    if (!value || value.startsWith("--")) {
      fail(`Missing value for --${key}.`);
    }
    parsed[toCamelCase(key)] = value;
    index += 1;
  }
  return parsed;
}

function toCamelCase(value) {
  return value.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
}

function requireOption(optionsMap, key) {
  const value = optionsMap[key];
  if (typeof value !== "string" || !value.trim()) {
    fail(`Missing required --${key.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)} option.`);
  }
  return value;
}

function extractStaticReferences(html) {
  return [...html.matchAll(/\b(?:src|href)="([^"]+)"/g)]
    .map((match) => match[1])
    .filter(
      (reference) =>
        reference &&
        !reference.startsWith("data:") &&
        !reference.startsWith("#") &&
        !/^https?:\/\//i.test(reference)
    );
}

function resolveReference(bundleDirectory, reference, basePath) {
  const pathname = reference.split(/[?#]/, 1)[0];
  if (!pathname.startsWith(basePath)) {
    fail(
      `Asset '${reference}' does not use the required ${surface} base path '${basePath}'.`
    );
  }

  const artifactRelativePath = pathname.slice(basePath.length);
  if (!artifactRelativePath) {
    fail(`Asset reference '${reference}' does not identify a file.`);
  }

  const resolved = resolve(bundleDirectory, artifactRelativePath);
  const relativePath = relative(bundleDirectory, resolved);
  if (relativePath.startsWith("..") || relativePath === "") {
    fail(`Asset reference escapes the built bundle: ${reference}`);
  }
  return resolved;
}

function listFiles(directory) {
  const files = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const entryPath = resolve(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...listFiles(entryPath));
    } else if (entry.isFile()) {
      files.push(entryPath);
    }
  }
  return files;
}

function inspectAndroidVersion() {
  const buildGradlePath = resolve(frontendRoot, "android/app/build.gradle");
  const buildGradle = readFileSync(buildGradlePath, "utf8");
  const versionCode = buildGradle.match(/\bversionCode\s+(\d+)/)?.[1];
  const versionName = buildGradle.match(/\bversionName\s+"([^"]+)"/)?.[1];
  if (!versionCode || !versionName) {
    fail(`Cannot read Android version metadata from ${buildGradlePath}.`);
  }
  return { versionCode: Number(versionCode), versionName };
}

function inspectAndroidArtifact(apkPath, expectedVersion) {
  if (!existsSync(apkPath) || statSync(apkPath).size === 0) {
    fail(`Android APK is missing or empty: ${apkPath}`);
  }

  const metadataPath = resolve(dirname(apkPath), "output-metadata.json");
  if (!existsSync(metadataPath)) {
    fail(`Android output metadata is missing: ${metadataPath}`);
  }
  const metadata = JSON.parse(readFileSync(metadataPath, "utf8"));
  const artifact = metadata.elements?.[0];
  if (!artifact) {
    fail(`Android output metadata contains no artifact: ${metadataPath}`);
  }
  if (
    artifact.versionName !== expectedVersion.versionName ||
    artifact.versionCode !== expectedVersion.versionCode
  ) {
    fail(
      `Android APK metadata ${artifact.versionName}/${artifact.versionCode} does not match Gradle ${expectedVersion.versionName}/${expectedVersion.versionCode}.`
    );
  }
}

function verifyExistingManifest(manifestPath, expectedManifest) {
  const existing = JSON.parse(readFileSync(manifestPath, "utf8"));
  for (const field of [
    "schema",
    "product_version",
    "surface",
    "asset_base_path",
    "api_base_url"
  ]) {
    if (existing[field] !== expectedManifest[field]) {
      fail(
        `Existing release manifest field '${field}' differs from the current artifact: ${manifestPath}`
      );
    }
  }
}

function sourceCommit() {
  try {
    return execFileSync("git", ["-C", frontendRoot, "rev-parse", "HEAD"], {
      encoding: "utf8"
    }).trim();
  } catch {
    return "unavailable";
  }
}

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function fail(message) {
  throw new Error(`Product release verification failed: ${message}`);
}
