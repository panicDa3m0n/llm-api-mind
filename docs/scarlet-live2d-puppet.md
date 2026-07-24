# Scarlet Layered 2D Puppet

Last updated: 2026-07-22
Status: paused research; artifacts preserved, static portraits are the active Product UI direction
Branch: `sca-48-product-ui-prototype`

## Objective

> This document preserves the layered-puppet research state. ADR-0124 pauses
> active puppet production in favor of identity-locked static portrait states.
> Nothing below should be interpreted as current Product UI implementation work.

Build one identity-faithful Scarlet puppet from complete transparent raster
surfaces. The approved portrait is authoritative for face, hair, neck, visible
torso, rendering, and identity. The T-pose is secondary evidence for arms,
hands, legs, boots, and body regions absent from the portrait.

The layered PSD is renderer-neutral. It should remain usable by Live2D Cubism,
Spine, Cartoon Animator, or another 2D rig without redrawing Scarlet.

## Visual Sources

Only these files define Scarlet's appearance:

```text
frontend/public/prototype/scarlet-character-v1.png
frontend/public/prototype/avatar/source/scarlet-full-body-tpose-reference-v1.png
```

`frontend/avatar-authoring/psd/Poopoo.psd` is a structural reference only.
Its pixels, colors, character identity, anatomy, costume, and textures cannot
enter Scarlet artwork. Its parsed hierarchy is recorded in:

```text
frontend/public/prototype/avatar/poopoo-structural-reference.json
```

## Structural Evidence

The reference PSD contains 105 raster layers and 22 groups. Twelve layers use
clipping, six use `linear dodge`, one uses clipped `multiply`, and no authored
Photoshop masks or layer effects were found. Its practical construction is:

- painted texture, depth, shadows, highlights, and outlines are baked into the
  anatomical raster assets;
- clipping is reserved for local overlays such as blush, face shadow, tattoos,
  tongue, teeth, and iris base relationships;
- additive blending is reserved for iris light;
- eyes are divided into sclera, iris base, pupil/light details, lids, corners,
  lashes, liner, brow shadow, and brow;
- the mouth is divided into interior, tongue, teeth, lips, lip shadow, and a
  hidden tongue-out variant;
- hair is divided by depth into rear mass, rear locks, front mass, bangs,
  individual locks, ears, and accessories;
- torso and clothing preserve their painted rendering inside each layer.

The reference is not a complete rig standard. One arm is explicitly left
unsplit and each leg is one long layer. Scarlet improves this by separating
both sides into upper limb, joint cover, lower limb, wrist/ankle cover, and
hand/boot assets.

## Scarlet PSD Hierarchy

The active back-to-front root order is:

```text
REFERENCE__SCARLET_PORTRAIT__LOCKED_BOTTOM
10_REAR_HAIR
20_LOWER_BODY
30_ARMS
40_NECK
50_TORSO
60_HEAD
70_FOREGROUND_LIMBS_AND_FX
```

`60_HEAD` contains distinct face, mouth, bilateral eye, nose, front-hair, and
expression groups. Each iris further separates base, pupil, highlights, and
additive glow; teeth separate upper, lower, and rear oral-occlusion planes. The
tears and face shadows remain beneath front hair, while foreground hand/arm
variants and emotion symbols have a dedicated top-level foreground group. The
exact folder tree and asset routes live in:

```text
frontend/public/prototype/avatar/scarlet-rig-workspace.json
```

The generated PSD is:

```text
frontend/avatar-authoring/psd/rig/scarlet-layered-rig-workspace-v2.psd
```

## Artwork Workflow

Every organ uses the same workflow:

1. Generate one complete anatomical Scarlet asset from the correct Scarlet
   reference on removable chroma.
2. Remove only chroma and trim to the actual alpha silhouette.
3. Preserve the native generated dimensions. Do not infer a final transform.
4. Insert the asset hidden into its semantic PSD folder with an
   `UNREGISTERED__...__OWNER_TRANSFORM_REQUIRED` name.
5. The owner moves and scales the layer against the locked bottom portrait in
   Photoshop.
6. Accept the layer only after identity, anatomy, alpha, z-order, and neutral
   recomposition review.

The user-controlled transform is deliberate. Image-generated assets do not
share a trustworthy pixel coordinate system with the portrait, so automatic
registration created slow, inconsistent placement work without improving the
artwork.

## Rendering Rules

Each generated asset includes its own Scarlet-specific material rendering by
default. Separate shader layers are created only when they must animate or fade
independently:

- face shadow and blush: clipped normal layers;
- independent dark markings: clipped `multiply` where needed;
- iris, catchlight, and suit emission: reviewed `linear dodge` layers;
- hair texture, skin rendering, clothing folds, and ordinary highlights:
  painted into their owning asset.

This preserves the dimensional appearance of the approved Scarlet references
without turning the PSD into a stack of generic flat-color shapes.

## Current State

Nineteen generated assets are staged in the V2 PSD: bilateral sclerae,
iris/pupil assets, catchlights, upper/lower lid skin, upper/lower lashes,
upper/lower lips, nose, and brows. They are hidden and unregistered. Only
`eye_scarlet_right_upper_lash_liner` has owner-approved artwork; placement and
all other artwork remain owner-controlled review gates.

The PSD skeleton already contains the complete folder inventory for rear hair,
full body, articulated limbs, neck, torso, face, mouth, eyes, nose, front hair,
expressions, and foreground effects. Empty folders represent artwork still to
be generated, not completed surfaces.

## Verification

```text
cd frontend
npm run avatar:reference:audit
npm run avatar:rig-workspace
```

The first command reparses the structural PSD without loading its artwork. The
second regenerates native Scarlet assets and the V2 PSD, then reopens the PSD
and rejects hierarchy or bottom-reference drift.
