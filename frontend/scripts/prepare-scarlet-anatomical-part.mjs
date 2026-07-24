import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import sharp from "sharp";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const frontendDirectory = path.resolve(scriptDirectory, "..");
const manifestArgument = process.argv[2] ?? "public/prototype/avatar/scarlet-rig-workspace.json";
const manifestPath = path.resolve(frontendDirectory, manifestArgument);
const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));

function resolveFrontend(relativePath) {
  return path.resolve(frontendDirectory, relativePath);
}

async function makeProof(assetBuffer, width, height) {
  const panelWidth = 480;
  const panelHeight = 300;
  const checker = Buffer.from(`
    <svg xmlns="http://www.w3.org/2000/svg" width="${panelWidth}" height="${panelHeight}">
      <defs><pattern id="c" width="24" height="24" patternUnits="userSpaceOnUse">
        <rect width="24" height="24" fill="#f5f5f7"/>
        <path d="M0 0h12v12H0zM12 12h12v12H12z" fill="#c7c9cf"/>
      </pattern></defs><rect width="100%" height="100%" fill="url(#c)"/>
    </svg>
  `);
  const fit = await sharp(assetBuffer)
    .resize(panelWidth - 40, panelHeight - 40, { fit: "inside", withoutEnlargement: true })
    .png()
    .toBuffer();
  const meta = await sharp(fit).metadata();
  const left = Math.round((panelWidth - meta.width) / 2);
  const top = Math.round((panelHeight - meta.height) / 2);
  const panels = await Promise.all([
    sharp({ create: { width: panelWidth, height: panelHeight, channels: 4, background: "#fff" } }).composite([{ input: fit, left, top }]).png().toBuffer(),
    sharp({ create: { width: panelWidth, height: panelHeight, channels: 4, background: "#000" } }).composite([{ input: fit, left, top }]).png().toBuffer(),
    sharp(checker).composite([{ input: fit, left, top }]).png().toBuffer()
  ]);
  const label = Buffer.from(`
    <svg xmlns="http://www.w3.org/2000/svg" width="${panelWidth * 3}" height="44">
      <rect width="100%" height="100%" fill="#17151b"/>
      <text x="16" y="29" fill="#fff" font-family="Arial, sans-serif" font-size="18">
        Native generated crop ${width}x${height} - no placement or scaling applied
      </text>
    </svg>
  `);
  return sharp({ create: { width: panelWidth * 3, height: panelHeight + 44, channels: 4, background: "#fff" } })
    .composite([
      { input: label, left: 0, top: 0 },
      ...panels.map((input, index) => ({ input, left: panelWidth * index, top: 44 }))
    ])
    .png()
    .toBuffer();
}

async function prepareAsset(asset) {
  const inputPath = resolveFrontend(asset.source_transparent);
  const outputPath = resolveFrontend(asset.native_asset);
  const proofPath = resolveFrontend(asset.alpha_proof);
  await fs.access(inputPath);
  const metadata = await sharp(inputPath).metadata();
  if (!metadata.hasAlpha) throw new Error(`${asset.id}: generated source has no alpha channel`);

  const nativeBuffer = await sharp(inputPath)
    .trim({ background: { r: 0, g: 0, b: 0, alpha: 0 }, threshold: 2 })
    .png()
    .toBuffer();
  const nativeMetadata = await sharp(nativeBuffer).metadata();
  if (!nativeMetadata.width || !nativeMetadata.height) throw new Error(`${asset.id}: empty native crop`);

  await Promise.all([
    fs.mkdir(path.dirname(outputPath), { recursive: true }),
    fs.mkdir(path.dirname(proofPath), { recursive: true })
  ]);
  await Promise.all([
    fs.writeFile(outputPath, nativeBuffer),
    fs.writeFile(proofPath, await makeProof(nativeBuffer, nativeMetadata.width, nativeMetadata.height))
  ]);

  return {
    id: asset.id,
    group_path: asset.group_path,
    native_asset: asset.native_asset,
    width: nativeMetadata.width,
    height: nativeMetadata.height,
    placement: "unregistered-owner-controlled",
    source_kind: "image-generation"
  };
}

const prepared = [];
for (const asset of manifest.assets) prepared.push(await prepareAsset(asset));
const reportPath = resolveFrontend(manifest.native_assets_report);
await fs.mkdir(path.dirname(reportPath), { recursive: true });
await fs.writeFile(reportPath, `${JSON.stringify({
  schema_version: "scarlet-native-anatomical-assets-v1",
  workflow: "generated-chroma-alpha-native-crop-v1",
  assets: prepared
}, null, 2)}\n`);

console.log(`Prepared ${prepared.length} native anatomical assets without placement or scaling`);
