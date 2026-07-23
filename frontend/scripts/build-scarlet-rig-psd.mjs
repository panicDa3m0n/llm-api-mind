import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { readPsd, writePsdBuffer } from "ag-psd";
import sharp from "sharp";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const frontendDirectory = path.resolve(scriptDirectory, "..");
const manifestArgument = process.argv[2] ?? "public/prototype/avatar/scarlet-rig-workspace.json";
const manifestPath = path.resolve(frontendDirectory, manifestArgument);
const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
const { width, height } = manifest.canvas;

function resolveFrontend(relativePath) {
  return path.resolve(frontendDirectory, relativePath);
}

if (manifest.structural_reference) {
  const audit = JSON.parse(
    await fs.readFile(resolveFrontend(manifest.structural_reference.audit), "utf8")
  );
  if (audit.source_sha256 !== manifest.structural_reference.sha256) {
    throw new Error("Structural PSD reference changed after the Scarlet workspace was designed");
  }
}

function pixelData(buffer, imageWidth, imageHeight) {
  return {
    data: new Uint8ClampedArray(buffer.buffer, buffer.byteOffset, buffer.byteLength),
    width: imageWidth,
    height: imageHeight
  };
}

async function imageDataFor(filePath) {
  const { data, info } = await sharp(filePath).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  return { imageData: pixelData(data, info.width, info.height), imageWidth: info.width, imageHeight: info.height };
}

function groupFromSpec(spec) {
  return {
    name: spec.name,
    opened: false,
    blendMode: spec.blend_mode ?? "pass through",
    hidden: spec.hidden ?? false,
    children: (spec.children ?? []).map(groupFromSpec)
  };
}

function findGroup(rootGroups, groupPath) {
  let current = { children: rootGroups };
  for (const groupName of groupPath) {
    const next = current.children.find((child) => child.name === groupName);
    if (!next?.children) throw new Error(`Unknown rig group path: ${groupPath.join(" / ")}`);
    current = next;
  }
  return current;
}

function hierarchyNames(layers) {
  return layers.map((layer) => ({ name: layer.name, children: layer.children ? hierarchyNames(layer.children) : undefined }));
}

function layerPaths(layers, parentPath = []) {
  const paths = [];
  for (const layer of layers) {
    const currentPath = [...parentPath, layer.name];
    paths.push({
      path: currentPath,
      hidden: Boolean(layer.hidden),
      blend_mode: layer.blendMode ?? "normal",
      clipping: Boolean(layer.clipping)
    });
    if (layer.children) paths.push(...layerPaths(layer.children, currentPath));
  }
  return paths;
}

const referencePath = resolveFrontend(manifest.reference);
const reference = await imageDataFor(referencePath);
if (reference.imageWidth !== width || reference.imageHeight !== height) {
  throw new Error(`Reference must be ${width}x${height}`);
}

const rigGroups = manifest.rig_groups.map(groupFromSpec);
for (const asset of manifest.assets) {
  const native = await imageDataFor(resolveFrontend(asset.native_asset));
  const targetGroup = findGroup(rigGroups, asset.group_path);
  targetGroup.children.push({
    name: asset.layer_name ?? `UNREGISTERED__${asset.id}__OWNER_TRANSFORM_REQUIRED`,
    imageData: native.imageData,
    left: Math.round((width - native.imageWidth) / 2),
    top: Math.round((height - native.imageHeight) / 2),
    hidden: asset.hidden ?? true,
    clipping: asset.clipping ?? false,
    blendMode: asset.blend_mode ?? "normal",
    opacity: asset.opacity ?? 1
  });
}

const referenceLayer = {
  name: "REFERENCE__SCARLET_PORTRAIT__LOCKED_BOTTOM",
  imageData: reference.imageData,
  protected: { transparency: true, composite: true, position: true }
};
const children = [referenceLayer, ...rigGroups];
const outputPath = resolveFrontend(manifest.output_psd);
await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.writeFile(outputPath, writePsdBuffer({
  width,
  height,
  imageData: reference.imageData,
  children
}));

const parsed = readPsd(await fs.readFile(outputPath), {
  skipLayerImageData: true,
  skipCompositeImageData: true
});
const expectedHierarchy = hierarchyNames(children);
const actualHierarchy = hierarchyNames(parsed.children ?? []);
if (JSON.stringify(actualHierarchy) !== JSON.stringify(expectedHierarchy)) {
  throw new Error("PSD hierarchy changed after serialization");
}
if (!parsed.children?.[0]?.name.startsWith("REFERENCE__")) {
  throw new Error("Reference is not the first/bottom PSD layer");
}

const parsedPaths = layerPaths(parsed.children ?? []);
const expectedAssets = manifest.assets.map((asset) => {
  const layerName = asset.layer_name ?? `UNREGISTERED__${asset.id}__OWNER_TRANSFORM_REQUIRED`;
  const expectedPath = [...asset.group_path, layerName];
  const matches = parsedPaths.filter((entry) => entry.path.join(" / ") === expectedPath.join(" / "));
  if (matches.length !== 1) {
    throw new Error(`Asset ${asset.id} is not present exactly once in ${asset.group_path.join(" / ")}`);
  }
  return { id: asset.id, path_key: expectedPath.join(" / ") };
});
const expectedAssetsByPath = new Map(expectedAssets.map((asset) => [asset.path_key, asset.id]));
const placedAssets = parsedPaths
  .filter((entry) => expectedAssetsByPath.has(entry.path.join(" / ")))
  .map((entry) => ({ id: expectedAssetsByPath.get(entry.path.join(" / ")), ...entry }));

const reportPath = resolveFrontend(manifest.psd_report);
await fs.writeFile(reportPath, `${JSON.stringify({
  schema_version: manifest.schema_version,
  status: "owner-placement-required",
  output_psd: manifest.output_psd,
  structural_reference: manifest.structural_reference,
  canvas: manifest.canvas,
  layer_order_semantics: "bottom-to-top",
  reference_layer: parsed.children[0].name,
  hierarchy: actualHierarchy,
  asset_stack_order: "Each path follows the PSD bottom-to-top hierarchy; Photoshop displays the inverse panel order.",
  placed_assets: placedAssets,
  unregistered_assets: manifest.assets.map((asset) => asset.id)
}, null, 2)}\n`);

console.log(`Built rig PSD with ${manifest.assets.length} unregistered generated assets and ${rigGroups.length} root rig groups`);
