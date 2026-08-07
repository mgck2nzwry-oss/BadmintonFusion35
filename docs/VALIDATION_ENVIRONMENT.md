# Validation environment

The local formal-data regression recorded on 2026-08-07 used:

| Component | Version |
|---|---:|
| Python | 3.12.13 |
| Pose2Sim | 0.10.49 |
| NumPy | 2.4.6 |
| pandas | 3.0.3 |
| SciPy | 1.18.0 |

The formal-data regression is read-only. It checks the locked control-point table,
reconstructs the P01 IMU timebase, reproduces the P03 A01 60-to-50 Hz mapping, applies
the P01 quality gates and verifies that missing segments in a P06 IMU channel remain
missing after filtering. It does not copy raw participant inputs into this repository.

The paper-workbook audit uses `openpyxl` only to read the workbook. The workbook is not
saved or modified. Statistical calculations are performed by the package itself.
