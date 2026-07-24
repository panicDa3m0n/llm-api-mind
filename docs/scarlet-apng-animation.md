# Scarlet APNG Animation Experiment

Last updated: 2026-07-21
Status: rejected and closed as an avatar construction path
Branch: `sca-48-product-ui-prototype`

## Result

The APNG experiments proved that a valid lossless animation container cannot
repair inconsistent or insufficient source motion.

- V1 preserved authored static poses but moved through visible jumps.
- V2 interpolated a local raster mesh but introduced unacceptable anatomical
  and texture distortion.

Both methods were rejected by the owner. Their generated frames, APNG files,
proofs, previews, and builders were removed during the reference-only reset.
The detailed implementation and evaluation history remains in
`docs/activity-log.md` and ADR-0120 in `docs/decisions.md`.

APNG may still be useful later as an export container for motion rendered by a
real layered rig. It is not an active method for constructing Scarlet's motion
or identity.

## Active Direction

The active path is a surgically separated raster PSD made from complete
anatomical surfaces. See `docs/scarlet-live2d-puppet.md` and
`frontend/public/prototype/avatar/scarlet-psd-authoring-contract.json`.
