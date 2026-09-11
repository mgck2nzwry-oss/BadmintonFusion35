# Blender 3-D court and motion visualisation

This repository includes a reproducible Blender scene builder for the released
`A10-R10` demonstration. It combines four public evidence items:

1. the 203-frame filtered 3-D keypoint table;
2. the locked 25 ground and 10 elevated court-control points;
3. the four-camera intrinsic and extrinsic calibration; and
4. the scene-generation script.

## Reproduce the public scene

Install Blender 4.5 LTS or a compatible later version. From the repository root,
run the following in PowerShell after replacing the executable path:

```powershell
$Blender = "C:\path\to\blender.exe"
& $Blender --background --python scripts\build_blender_scene.py -- `
  --keypoints-csv examples\a10_r10\visual\keypoints_3d_filtered.csv `
  --data-rate 60 `
  --control-points examples\a10_r10\calibration\scene_points_click_order.csv `
  --calibration examples\a10_r10\calibration\Calib_scene.toml `
  --action-label A10-R10 `
  --preview-frame 4080 `
  --output outputs\A10_R10_BadmintonFusion35.blend `
  --preview outputs\A10_R10_BadmintonFusion35_preview.png
```

The command creates a locally inspectable `.blend` animation and a PNG preview.
Press the space bar in Blender to play the reconstructed skeleton through the
source-frame interval. Camera frustums, the court, all 35 control targets and the
local right-wrist trace remain spatially registered in the scene.

For an authorized local Pose2Sim result, the same script also accepts `--trc`
instead of `--keypoints-csv`. Optional `--start-frame` and `--end-frame` arguments
select a source-frame interval. Missing observations are not silently interpolated.

## Interpretation boundary

This scene is an audit and communication layer, not an independent reconstruction
algorithm. Skeleton positions originate from the filtered Pose2Sim 3-D output. The
orange wrist trace is a local display aid and is not a shuttle trajectory. The
scene does not estimate ground-reaction forces, inverse dynamics, joint loading or
clinical accuracy, and it does not substitute a calibration-validation experiment.
Pixel residuals reported elsewhere in the repository must not be interpreted as
centimetre-level spatial accuracy.

Only the compact, consented A10-R10 demonstration is public. Complete participant
media and full-study trajectories remain controlled under the repository data policy.
