# Relationship to existing open-source projects

## MultiSenseBadminton

Repository: https://github.com/dailyminiii/MultiSenseBadminton

MultiSenseBadminton provides examples for HDF5 parsing, preprocessing, network training,
t-SNE and sensor-data visualization for a 25-player wearable-sensor badminton dataset.
It is the closest publication-style code-release precedent for this project, but it does
not implement this study's four-camera court geometry, formal P01-P35 non-coplanar
control field, Pose2Sim reconstruction, 60-to-50 Hz time mapping or participant-specific
variable gates. BadmintonFusion35 should cite it as related work, not present itself as a
fork or a replacement dataset.

## Pose2Sim

Repository: https://github.com/perfanalytics/pose2sim

Pose2Sim is the upstream multi-camera markerless-kinematics engine used by the formal
workflow. It already provides camera calibration, pose estimation, synchronization,
triangulation, 3D filtering and downstream kinematics. BadmintonFusion35 therefore keeps
only a thin, dry-run-by-default adapter and concentrates on study-specific geometry,
provenance, IMU reconstruction, cross-modal mapping, exclusions and paper statistics.
Pose2Sim remains a separate dependency governed by its own license and citation terms.

## Scope of the present repository

The distinct contribution of this code release is the auditable combination of:

- four fixed cameras in court coordinates;
- 25 ground plus ten elevated control points;
- four hand/knee IMUs with gap-preserving preprocessing;
- participant-specific camera and modality exceptions;
- exact 60 Hz visual to 50 Hz IMU nearest-sample mapping;
- variable-specific quality gates and participant-blocked inference;
- paper-output audits that explicitly separate verified results from unrecorded model
  training details.
