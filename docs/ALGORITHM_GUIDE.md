# Algorithm guide

See the [detailed Chinese guide](ALGORITHMS_ZH.md), [file/function index](CODE_INDEX.md),
[legacy-reference guide](../legacy_reference/README.md), and [verification record](RELEASE_VERIFICATION_20261005.md).
This is a source-only update. Existing public demos are unchanged; no new participant
videos, sensor records, workbooks or observation-level results are published.

## Responsibilities

| Package/file | Responsibility |
|---|---|
| `calibration/control_points.py` | Generate/validate the 35-point court geometry and point ordering |
| `calibration/audit.py`, `resilience.py` | Audit pixel residuals, point loss and camera coverage; not anatomical accuracy |
| `calibration/deployment.py` | Scaffold and validate a new-site evidence package; actual local calibration is required |
| `pipeline/pose2sim.py` | Explicit adapter to upstream Pose2Sim stages; dry-run by default, no bundled model weights |
| `io/trc.py` | TRC parser and segmentation-reference motion energy |
| `imu/timebase.py` | Reconstruct batched host timestamps and audit the resulting timebase |
| `alignment/nearest.py` | Nearest-sample mapping after clock alignment; does not estimate hardware synchronization |
| `imu/filtering.py`, `imu/features.py` | Gap-preserving low-pass filtering, interpolation and IMU feature primitives |
| `analysis/kinematics.py` | v2 adjacent-valid-frame trajectory/speed/angle/ROM descriptors |
| `analysis/aggregation.py` | Summaries of valid repetitions, grouped by supplied identifiers |
| `qc/inclusion.py` | Variable-specific optical/IMU quality gates |
| `analysis/stats.py` | Generic BH FDR, sample-SD PCA and participant-blocked action effects |
| `analysis/study.py` | Extracted fixed/mixed models, cluster bootstrap, missingness and nested logistic classification |
| `analysis/pca_study.py` | Manuscript-figure log1p/population-SD/SVD PCA with explicit sign orientation |
| `analysis/paper.py` | Audit existing workbook and historical prediction probabilities; not historical model retraining |
| `analysis/validation.py` | Recalculate supplied scene-coordinate and paired-event errors |
| `real_demo.py`, `visualization/` | Controlled demonstration exports, checksums and evidence summaries |
| `pipeline/evidence_chain.py` | Audit existing raw-to-player evidence, not a complete upstream model rerun |
| `legacy_reference/p01/` | Twelve original reference programs for manual segmentation, alignment, extraction and QC |
| `desktop_app/`, `visualizer/`, `scripts/build_blender_scene.py` | Local/browser/Blender viewing; not additional scientific validation |

Library paths above are relative to `src/badminton_court35/`. All operational scripts
are indexed separately in `CODE_INDEX.md`.

## Retained numerical definitions

Visual XYZ is in metres and time in seconds. Derivatives use adjacent valid frames
only. Geometric angles use the proximal–centre and distal–centre vectors. ROM is
max minus min; these are not independently validated musculoskeletal joint angles.

The reference IMU pipeline resamples at 50 Hz, averages duplicated timestamps,
does not interpolate gaps longer than 0.12 s or extrapolate, and applies a fourth-order
10 Hz zero-phase Butterworth separately to finite blocks. Blocks too short for the
filter are returned unchanged. Gyroscope RMS is based on the three-axis magnitude.
The acceleration proxy is `abs(norm(a_in_g)-1)`, not world-frame gravity-compensated
linear acceleration. Magnitude integrals are activity descriptors, not joint rotation.

Default joint inclusion: optical eligibility plus IMU validity >=95% for main analysis;
90% to <95% sensitivity only; below 90% excluded. These rules do not justify inventing
missing exclusion-reason records or participant-specific repair history.

The statistical runner accepts a QC-retained wide table, one row per participant–action,
with `Participant`, `Action` and the 23 fields in `study.FEATURE_NAMES`. XLSX defaults to
the `质量门控数据` sheet. It does not reconstruct this workbook from raw signals. The
complete executed assembly code for all 23 fields, including asymmetry indices,
has not been established; no formula was guessed from column names.

Fixed model: `ln(1+x) ~ Participant + Action`; nested-model action F-test; BH correction
over 23 features. Partial eta-squared intervals resample whole participant clusters
(2,000 iterations, seed 20260813). Random-intercept ML fits are a sensitivity analysis;
optimizer/near-boundary warnings remain in the output. The retained action LRT uses
df=9 and the guarded runner requires all ten A01–A10 actions. Missingness association
tests are exploratory and retain expected-count diagnostics.

Nested LOPO uses 12 IMU fields and multinomial logistic regression. Each outer test
participant is isolated; inner participant-held-out CV selects L2 from
`[0.01,0.1,1,10]` by mean inner accuracy (smallest L2 on ties). Standardization uses
only each training fold. Objective: summed cross-entropy plus `0.5*L2*sum(W**2)`;
intercepts are unpenalized. There is no feature selection. **This reproducible later
analysis is not recovery of the unarchived historical classifier.**

Study PCA: log1p, centring, population SD (`ddof=0`), SVD; orient each component so
its largest-absolute coefficient is positive. The generic `stats.py` PCA uses
`ddof=1`; variance proportions agree under this overall scaling but scores differ.
PCA is descriptive and is not used to preprocess the held-out classification folds.

Scene error is 100 times the Euclidean difference of estimated/truth metre coordinates.
Event audit subtracts the mean video-minus-IMU offset estimated on the same supplied
events unless `--fixed-offset-ms` is provided. Neither operation establishes independent
holdout status, event identity, anatomical validity or rapid-action adequacy.

## Commands

```powershell
python -m pip install -e ".[study]"
python -m unittest discover -s tests -v
python scripts/run_study_analysis.py --synthetic-demo --bootstrap-iterations 5 --skip-mixed --output outputs/synthetic-study
python scripts/run_study_analysis.py --input "<authorized-workbook.xlsx>" --output outputs/study
python scripts/reproduce_study_pca.py --input outputs/study/S2_observation_level_diagnostics.csv --output outputs/pca --plot
python scripts/extract_visual_features.py --trc "<local-trial.trc>" --start 1.0 --end 2.0 --output outputs/segment.json
python scripts/audit_validation_tables.py --scene "<scene.csv>" --events "<events.csv>" --output outputs/validation.json
```

New entry points refuse nonempty/existing outputs. `--exclude-participant` records
explicit sensitivity exclusions; `--skip-mixed` and `--skip-classification` mark partial
runs. Synthetic runs are software tests, not research evidence.

Outputs S1–S8 contain model results, observation diagnostics, missingness summaries,
nested predictions, folds and per-class metrics. `run_manifest.json` records input/output
hashes, parameters, versions and limitations. **S2, S6 and PCA scores can contain private
derived records: keep them local.** Do not upload them merely because the code is public.

Legacy scripts require explicit local-root/write configuration and may overwrite derived
files. They were syntax-checked, not executed on all participants. Desktop/Blender tools
were not rerun in this source release. Upstream dependencies retain their own licenses;
the repository code license is not consent to distribute participant data.
