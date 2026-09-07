# Deploy BadmintonFusion35 on a new regulation court

## What this protocol reproduces

This protocol makes the **measurement system and its analysis workflow**
re-deployable at another regulation badminton court. It recreates the locked
Court35 calibration geometry, four-camera acquisition record, IMU record,
time-alignment workflow and quality-control trail used by this repository.

It does not transfer the original cameras' intrinsic or extrinsic parameters to
another venue, and it does not guarantee absolute 3-D accuracy. Every new venue
must be calibrated and validated locally. A regulation court is a stable
geometric reference, not a substitute for local camera calibration.

## Coordinate convention and nominal court geometry

Use metres. Put the origin at the centre of the net on the analysed half court:
`X` is lateral (left/right), `Y` runs from the net toward the back boundary and
`Z` is vertical. The generated package uses the following nominal regulation
doubles-court dimensions:

| Quantity | Nominal value (m) |
| --- | ---: |
| Full court length | 13.40 |
| Doubles width | 6.10 |
| Singles width | 5.18 |
| Net height at centre | 1.524 |
| Net height at posts | 1.55 |
| Short-service line from net | 1.98 |
| Doubles long-service line from back boundary | 0.76 |

Before use, compare these values with the current governing-body court laws and
record the locally surveyed measurements. The code applies a 0.02 m nominal
geometry check to catch transcription or coordinate-system errors; it is not a
venue certification tool.

## Create a site package

```powershell
court35 scaffold-site --site-name "Venue-2026-01" --output-dir .\Venue-2026-01
Set-Location .\Venue-2026-01
```

The command creates the following items. Do not replace the P01--P35 order in
the calibration CSV; that order is the formal object-point identity.

| File | Purpose |
| --- | --- |
| `site.toml` | Court survey, coordinate convention, sample rates and validation declarations |
| `calibration/scene_points_click_order.csv` | 25 ground and 10 elevated non-coplanar object points |
| `camera_manifest.csv` | Four camera hardware, calibration, fixation and coverage evidence |
| `imu_manifest.csv` | Sensor model, placement, axis convention and sync record |

## Field procedure

1. Survey the court, mark the net-centre origin and document the coordinate axes.
2. Place P01--P25 as the 5 x 5 floor grid; place P26--P30 and P31--P35 on the
   two vertical crossed-target masts. Check every physical label against the
   generated CSV.
3. Install four fixed cameras outside the action area. Their exact tripod
   locations may vary by venue, but every camera must see the calibration
   targets and pass a live whole-body plus racket-apex coverage test.
4. Record individual intrinsic calibration for each camera. Lock the lens,
   exposure, resolution and frame rate, then do not move any camera.
5. Record all 35 targets from all cameras and estimate local extrinsics. Archive
   the calibration inputs, result files and per-camera residual table in the
   site folder.
6. Record one shared synchronisation event visible or measurable in every
   relevant stream (for example LED, clap, or impact event). Record the IMU
   axis convention, mounting orientation, firmware and sample rate.
7. Perform coverage testing using the actions needed at that venue (at minimum:
   stance, lunge, jump and overhead reach). Then capture the planned trials.
8. Run 2-D pose estimation, local 3-D reconstruction, IMU timestamp rebuilding,
   filtering and visual-to-IMU mapping with the supplied commands and configs.

## Deployment gate

After completing the manifests and `site.toml`, run:

```powershell
court35 validate-site --site-dir . --report deployment_report.json
```

Interpret the result conservatively:

| Status | Meaning |
| --- | --- |
| `BLOCKED` | The target geometry, nominal court dimensions, or four-camera record is invalid or missing. Do not acquire or analyse as a Court35 deployment. |
| `REVIEW_REQUIRED` | The package exists but one or more local calibration, coverage, fixation or synchronisation confirmations are incomplete. |
| `READY_FOR_RELATIVE_ANALYSIS` | All recorded deployment prerequisites are complete. The system may be used for the stated comparative motion/visualisation workflow. Absolute spatial accuracy is not established. |
| `READY_WITH_HELD_OUT_VALIDATION` | The package additionally declares a documented held-out 3-D validation. Retain its protocol and results before making an accuracy claim. |

## Minimum reproducibility archive for each venue

Keep the generated site package together with: camera intrinsic and extrinsic
files; 35-point image observations; residual/audit output; camera settings;
the four synchronised videos; IMU files and device metadata; time-mapping and
QC reports; software versions; and a de-identified example output. Do not
publish participant video or raw data unless the consent and data-governance
conditions allow it.

## Claim boundary for the manuscript

Appropriate wording is: *“The open workflow permits site-specific deployment
of the court-standardised four-camera/IMU protocol on a regulation badminton
court, subject to local survey, calibration, coverage testing and quality
control.”* Do not claim that a standard court alone makes a new installation
accurate, or that the present study demonstrates training efficacy.
