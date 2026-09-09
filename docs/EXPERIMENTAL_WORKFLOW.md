# Experimental workflow and reproducibility protocol

This protocol describes the operating sequence implemented by
BadmintonFusion35. It is a reproducibility guide for a new regulation badminton
court and an audit guide for a completed trial. It does not replace ethical
approval, participant consent, local data governance, or independent spatial
accuracy validation.

## 1. Define a site before recording

1. Confirm a regulation doubles court and establish the court coordinate system.
2. Fix four cameras (`cam01`--`cam04`) on stable supports. Record lens choice,
   resolution, frame rate, exposure, and physical camera placement in the site
   manifest.
3. Lay out the locked 35-point geometry: 25 ground points plus 10 elevated
   targets distributed across the capture volume. Do not change camera poses or
   lens settings after extrinsic calibration.
4. Place the IMUs consistently and record a shared synchronization event.
5. Complete movement/coverage tests that include a lunge, jump, and overhead
   reach. Preserve the test result with the site record.

Create a portable site package for a new court:

```powershell
court35 scaffold-site --site-name "Venue-2026-01" --output-dir ".\Venue-2026-01"
court35 validate-site --site-dir ".\Venue-2026-01" --report ".\Venue-2026-01\deployment_report.json"
```

`READY_FOR_RELATIVE_ANALYSIS` means that the documented operational gates have
been completed. It does **not** support a centimetre-level accuracy claim without
a held-out 3-D validation.

## 2. Calibrate and retain calibration evidence

For every camera, retain the intrinsic calibration file, the 35-point click order,
the 3-D object-point file, image points, camera parameters and per-point residual
table. Audit the locked point layout and residuals before interpreting motion
outputs:

```powershell
court35 validate-control-points `
  --csv "<PROJECT>\calibration\scene_points_click_order.csv" `
  --trc "<PROJECT>\calibration\Object_points.trc"

court35 audit-calibration `
  --residuals "<PROJECT>\calibration\extrinsics_point_residuals.csv" `
  --summary "<PROJECT>\reports\calibration_residual_summary.csv" `
  --report "<PROJECT>\reports\calibration_residual_audit.json"
```

The audit intentionally reports residuals in pixels. Do not relabel them as an
independent 3-D spatial error estimate.

## 3. Acquire and preserve raw inputs

Each trial requires four original camera files and the paired IMU recording.
Use a participant/action/repeat identifier, retain original media privately, and
record the common event used for timing alignment. The public repository must not
receive full participant video, raw IMU dumps, identifiers, or site records without
documented permission and governance review.

## 4. Run Pose2Sim in explicit stages

The repository never reruns Pose2Sim silently. First inspect the plan:

```powershell
court35 pose2sim `
  --config "<PROJECT>\A01\Config.toml" `
  --stages calibration poseEstimation synchronization triangulation filtering
```

Only after reviewing paths and output implications, add `--execute`. The expected
derived evidence is: 2-D keypoint JSON for every camera, synchronized JSON,
filtered 3-D TRC, and a Pose2Sim log containing the final synchronization and
triangulation settings.

## 5. Align visual and inertial time bases

Reconstruct any discontinuous IMU host time base, filter valid contiguous IMU
segments, then map visual frames to IMU samples. The default analytical rates are
60 Hz visual and 50 Hz IMU. Keep the mapping offset, time scale, maximum correlation,
correlation margin, included interval, and sample count in the evidence record.

```powershell
court35 reconstruct-time --input "<RAW_IMU>.csv" --time-column "<TIME_COLUMN>" `
  --output "<DERIVED_IMU>.csv"
court35 filter-imu --input "<DERIVED_IMU>.csv" --output "<FILTERED_IMU>.csv"
court35 map-nearest --visual "<VISUAL>.csv" --imu "<FILTERED_IMU>.csv" `
  --visual-time relative_time_s --imu-time relative_time_s --output "<MAPPING>.csv"
```

## 6. Build the trial evidence chain

For a completed trial, run the single audit entrypoint. It verifies the chain without
fabricating a new model output:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_complete_evidence_chain.ps1 `
  -ProjectRoot "<PROJECT>" -Action A01 -Repeat 1 `
  -PythonPath "$env:USERPROFILE\.venv\pose2sim\Scripts\python.exe"
```

The resulting `evidence_chain.json` records:

- existence and identity of the four raw videos;
- 35-point geometry audit and calibration residual boundary;
- final `cam01`-referenced timing offsets and synchronization correlations;
- 2-D JSON frame coverage and mean keypoint confidence per camera;
- 3-D filtered TRC frame and coordinate coverage;
- visual--IMU offset, scale, correlation and selected 50 Hz samples;
- PASS, FAIL, or REVIEW_REQUIRED status for every stage.

## 7. Inspect with the desktop player

Run `desktop_app\run_a01_demo.ps1`, or build the native executable with
`desktop_app\build_desktop_exe.ps1`. The player provides four synchronized Pose2Sim
2-D-overlay views, five live signals (right hand and knee gyroscope, combined IMU
energy, right wrist speed and right knee angle), a common time cursor, and the linked
evidence-chain state. It is an inspection and communication interface; it does not
replace the upstream processing or QC steps.

## 8. Report responsibly

In the manuscript and repository, distinguish the following:

- **implemented and audited:** control-point geometry, operational four-camera
  synchronisation, derived 2-D/3-D coverage, IMU alignment and trial visualization;
- **review required:** any calibration residual or data-quality flag emitted by the
  evidence chain;
- **not established by this pipeline alone:** held-out 3-D accuracy, generalization
  to untested venues, clinical efficacy, or causal training benefit.

This distinction makes the code useful to readers without overstating what its
evidence supports.
