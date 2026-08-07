# Legacy-code repair map

The original scripts remain untouched in the formal experiment directories. The new
package replaces participant-specific path-bound behavior with the following reusable
modules.

| Legacy responsibility | Representative legacy script | New implementation |
|---|---|---|
| 35-point geometry/configuration | `prepare_final_pose2sim_config.py` | `calibration/control_points.py` |
| TRC parsing and motion energy | `segment_repetitions.py` | `io/trc.py` |
| Batched host-time reconstruction | `merge_reconstruct_P01_IMU.py` | `imu/timebase.py` |
| IMU low-pass filtering | participant-specific filtering scripts | `imu/filtering.py` |
| Visual-IMU alignment/mapping | `align_P01_visual_IMU.py` and later participant scripts | `alignment/nearest.py` |
| Optical/IMU inclusion gates | `build_P01_visual_IMU_joint_inclusion.py` | `qc/inclusion.py` |
| Metrics audit | `audit_participant01_metrics.py` | CLI audits and regression reports |
| PCA/FDR analysis | manuscript figure/data scripts | `analysis/stats.py` |
| Pose2Sim stage execution | `run_Axx_*.py` | `pipeline/pose2sim.py` with dry-run default |

The inventory report records hashes and structural signals without copying raw data or
absolute source paths. Legacy scripts are evidence and may still be needed for provenance;
they should not be deleted after migration.
