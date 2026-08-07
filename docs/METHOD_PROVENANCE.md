# Method provenance and locked decisions

## Formal geometry

The formal configuration is P01-P35: 25 ground points on a 5 x 5 grid and ten elevated
points on two vertical masts at 0.50, 1.00, 1.50, 2.00 and 2.30 m. The authoritative
local evidence is `scene_points_click_order.csv`, `Object_points.trc` and the formal
`Config.toml` under the P01 project.

An earlier T02 pilot conversation used P01-P33, four heights per mast and different pole
coordinates. That pilot must remain excluded from formal analysis and public examples.

## Sampling and cross-modal mapping

Formal visual trajectories are normally 60 Hz. IMU streams are reconstructed, resampled
to 50 Hz and filtered at 10 Hz with a fourth-order zero-phase Butterworth filter. A visual
row is mapped to the nearest 50 Hz IMU row; the theoretical maximum nearest-sample error
is 10 ms. Missing spans are retained as missing and are not filled with zero.

## Audited exceptions that must remain visible

- P04 contains eight visual-IMU actions and two IMU-only visual exclusions.
- P05 uses a documented three-camera branch for most actions and four cameras for A05.
- P06 retains six actions and has four visual-quality exclusions.
- P07 retains four actions, has six visual-quality exclusions and keeps an unresolved
  nominal no-shift cross-modal decision.
- Other participant-specific missing spans and exclusions remain in their manifests.

These are data-quality facts, not software errors. The software must encode them through
manifests and variable-specific gates rather than silently replacing values.

## Calibration interpretation

The retained residual tables contain raw and robust pixel residuals. Pixel residuals alone
cannot prove centimetre-level three-dimensional accuracy. Before the paper claims accuracy,
add a held-out control-point, known-distance or repeated-calibration spatial validation.
