# BadmintonCourt35

BadmintonCourt35 is a reproducibility package for a court-standardized badminton
training study using four fixed cameras, 35 non-coplanar scene control points and four
limb-mounted IMUs. It converts the original participant-specific scripts into explicit,
testable functions and a single command-line interface.

This repository is currently a **private v0.1 development snapshot**. It does not claim
that the full paper is reproducible yet, and it must not be made public until the release
checklist and human-data review are complete.

## What is already implemented

- locked P01-P35 control-point generation and validation;
- TRC reading and motion-energy construction;
- reconstruction of batched or repeated IMU host timestamps;
- 50 Hz, fourth-order, 10 Hz zero-phase Butterworth filtering without bridging gaps;
- nearest-sample mapping from 60 Hz visual data to 50 Hz IMU data with timing audit;
- variable-specific optical/IMU inclusion gates;
- camera residual audit that keeps pixel error separate from spatial accuracy;
- Benjamini-Hochberg FDR correction and standardized PCA;
- paper-workbook audit for PCA, FDR sensitivity, out-of-fold ROC and clustered bootstrap CIs;
- a safe Pose2Sim stage adapter that defaults to a dry run;
- an anonymous synthetic end-to-end example.

## Installation

Use the existing Pose2Sim Python environment:

```powershell
$Python = "$env:USERPROFILE\.venv\pose2sim\Scripts\python.exe"
Set-Location "<path-to-BadmintonCourt35>"
& $Python -m pip install -e .
```

The core package requires NumPy, pandas and SciPy. Pose2Sim is imported only when a
real Pose2Sim stage is explicitly executed.

## First verification

```powershell
court35 validate-control-points `
  --csv "<FORMAL_PROJECT>\calibration\scene_points_click_order.csv" `
  --trc "<FORMAL_PROJECT>\calibration\Object_points.trc"
```

Audit the retained calibration residual evidence:

```powershell
court35 audit-calibration `
  --residuals "<ANALYSIS_READY>\P01\01_Protocol_Config\calibration\extrinsics_point_residuals.csv" `
  --summary "reports\P01_calibration_residual_summary.csv" `
  --report "reports\P01_calibration_residual_audit.json"
```

Generate the non-identifiable demonstration:

```powershell
court35 demo --output-dir "examples\demo\generated"
```

Audit the formal paper statistics (requires `pip install -e ".[paper]"`):

```powershell
court35 audit-paper-workbook `
  --workbook "<PAPER_AUDIT_WORKBOOK.xlsx>" `
  --report "reports\paper_workbook_audit.json"
```

Run all standard-library tests:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests -v
```

## Pose2Sim safety boundary

The adapter is a dry run unless `--execute` is provided:

```powershell
court35 pose2sim `
  --config "<FORMAL_PROJECT>\Config.toml" `
  --stages calibration poseEstimation synchronization triangulation filtering
```

Only after reviewing the printed plan should a real run use `--execute`. The code never
deletes the original participant directory.

## Data policy

Do not commit participant videos, raw IMU dumps, C3D files, archives or identifiable
renderings. Git should contain only code, configuration, small de-identified tables and
synthetic examples. Public data and code licenses must be approved separately.

## Reproducibility status

| Component | v0.1 status |
|---|---|
| Formal 35-point geometry | Implemented and checked against P01 formal files |
| Pose2Sim orchestration | Implemented; real execution requires explicit opt-in |
| IMU time reconstruction/filtering | Implemented and checked against formal local files |
| 60-to-50 Hz nearest mapping | Implemented and timing-audited |
| Variable-specific QC | Implemented |
| PCA and FDR | Implemented |
| LOPO outputs | All OOF probabilities, ROC curves and clustered-bootstrap CIs are auditable |
| Exact LOPO model training | Blocked until the authoritative classifier specification is identified |
| Raw human data release | Blocked pending consent, ethics and access-policy confirmation |
| Public software license/citation | Pending author and institution details |

See [method provenance](docs/METHOD_PROVENANCE.md) and the
[paper reproducibility boundary](docs/PAPER_REPRODUCIBILITY.md), the
[relationship to existing projects](docs/RELATED_WORK.md), then the
[validation environment](docs/VALIDATION_ENVIRONMENT.md) and
[release checklist](docs/RELEASE_CHECKLIST.md), before any public push.
