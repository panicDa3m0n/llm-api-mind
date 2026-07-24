import fs from "node:fs/promises";
import crypto from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { readPsd } from "ag-psd";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const frontendDirectory = path.resolve(scriptDirectory, "..");
const sourceArgument =
  process.argv[2] ?? "avatar-authoring/psd/Poopoo.psd";
const outputArgument = process.argv[3] ?? "public/prototype/avatar/poopoo-structural-reference.json";
const sourcePath = path.resolve(frontendDirectory, sourceArgument);
const outputPath = path.resolve(frontendDirectory, outputArgument);

const sourceBuffer = await fs.readFile(sourcePath);
const psd = readPsd(sourceBuffer, {
  skipLayerImageData: true,
  skipCompositeImageData: true,
  skipThumbnail: true
});

function boundsFor(layer) {
  const values = [layer.left, layer.top, layer.right, layer.bottom];
  return values.every(Number.isFinite)
    ? { left: layer.left, top: layer.top, right: layer.right, bottom: layer.bottom }
    : null;
}

function summarizeLayer(layer, parentPath = []) {
  const group = Array.isArray(layer.children);
  const layerPath = [...parentPath, layer.name];
  return {
    name: layer.name,
    path: layerPath,
    kind: group ? "group" : "raster-layer",
    bounds: boundsFor(layer),
    hidden: Boolean(layer.hidden),
    clipping: Boolean(layer.clipping),
    blend_mode: layer.blendMode ?? "normal",
    opacity: layer.opacity ?? 1,
    children: group ? layer.children.map((child) => summarizeLayer(child, layerPath)) : undefined
  };
}

function flatten(layers) {
  const flattened = [];
  for (const layer of layers) {
    flattened.push(layer);
    if (layer.children) flattened.push(...flatten(layer.children));
  }
  return flattened;
}

const hierarchy = (psd.children ?? []).map((layer) => summarizeLayer(layer));
const flattened = flatten(hierarchy);
const blendModes = {};
for (const layer of flattened) {
  blendModes[layer.blend_mode] = (blendModes[layer.blend_mode] ?? 0) + 1;
}

const report = {
  schema_version: "layered-avatar-structural-reference-v1",
  source: sourceArgument,
  source_sha256: crypto.createHash("sha256").update(sourceBuffer).digest("hex"),
  source_bytes: sourceBuffer.byteLength,
  usage_boundary: {
    permitted: [
      "layer hierarchy reference",
      "anatomical asset inventory reference",
      "clipping and blend-mode reference",
      "z-order and grouping reference"
    ],
    forbidden: [
      "copying source pixels into Scarlet assets",
      "using source artwork as a Scarlet texture",
      "deriving Scarlet identity, colors, anatomy, or costume from this character"
    ],
    scarlet_visual_authority: [
      "public/prototype/scarlet-character-v1.png",
      "public/prototype/avatar/source/scarlet-full-body-tpose-reference-v1.png"
    ]
  },
  canvas: { width: psd.width, height: psd.height },
  order_semantics: "bottom-to-top",
  counts: {
    roots: hierarchy.length,
    groups: flattened.filter((layer) => layer.kind === "group").length,
    raster_layers: flattened.filter((layer) => layer.kind === "raster-layer").length,
    hidden: flattened.filter((layer) => layer.hidden).length,
    clipped: flattened.filter((layer) => layer.clipping).length,
    non_normal_blend: flattened.filter(
      (layer) => !["normal", "pass through"].includes(layer.blend_mode)
    ).length
  },
  blend_modes: blendModes,
  clipped_layers: flattened
    .filter((layer) => layer.clipping)
    .map((layer) => ({ path: layer.path, blend_mode: layer.blend_mode, opacity: layer.opacity })),
  non_normal_layers: flattened
    .filter((layer) => !["normal", "pass through"].includes(layer.blend_mode))
    .map((layer) => ({ path: layer.path, blend_mode: layer.blend_mode, opacity: layer.opacity })),
  hidden_layers: flattened.filter((layer) => layer.hidden).map((layer) => layer.path),
  hierarchy
};

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.writeFile(outputPath, `${JSON.stringify(report, null, 2)}\n`);
console.log(
  `Analyzed ${report.counts.raster_layers} raster layers and ${report.counts.groups} groups from ${sourceArgument}`
);
