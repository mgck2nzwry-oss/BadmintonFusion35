# Verification record — 2026-10-05

This records checks performed for the algorithm-source update, not a new experiment.
No private observations or local verification tables are included in this report.

## Completed checks

- 80 source files indexed, including 61 Python files syntax-checked. Web-template and build files are explicitly separated from experimental algorithms in the [index](CODE_INDEX.md).
- 33 Python unit/regression tests passed locally. New tests use artificial observations; existing tests also verify the already-public A10-R10 demonstration and checksums.
- All 15 functions extracted into `analysis/study.py` are AST-identical to the corresponding functions in the locally retained `build_sci_supplement.py`. Source SHA-256 and names are recorded in [study_algorithm_provenance.json](study_algorithm_provenance.json).
- The two v2 visual derivative functions match their reference functions except for redirecting the identical `base.safe_stat` helper to its local name. This is checked by a unit test.
- A synthetic statistical smoke run completed, including nested classification; it intentionally skipped the mixed-model sensitivity run and used only five bootstrap iterations. It is not paper evidence.
- A full local-workbook run completed with 2,000 participant-cluster bootstrap iterations, random-intercept sensitivity and nested LOPO. Fixed-model F, p, partial eta-squared, bootstrap interval bounds and FDR q-values matched the prior supplementary table within stated numerical comparison tolerances (rtol=1e-9, atol=1e-11). Nested predicted labels matched exactly; class probabilities matched within rtol=1e-7, atol=1e-9.
- Study PCA recalculation from the existing local diagnostic table reproduced the previously documented first two variance proportions; the portable PNG/PDF plotting entry executed successfully. This verifies numerical processing, not scientific generalization.
- The local scene-coordinate and event-timing tables were successfully checked against their coordinate/time-derived values. No new validation measurements were created. Same-event mean-offset residuals are labeled as such, not as independent holdout validation.

## Not run / not established

- Full raw-video Pose2Sim inference and all camera calibrations were not rerun.
- The twelve path-bound reference programs were syntax-checked but not executed across P01–P10. Interactive manual segmentation and participant-specific repairs require their original records and review.
- Desktop GUI playback, Blender rendering and the web build/deployment were not rerun in this update. Their existing source is preserved.
- CI configuration now installs the optional study dependencies. Local success is not a claim that a remote CI run has already passed.
- The original historical classifier/training settings have not been recovered. The implemented nested logistic classifier is a distinct, explicitly specified later analysis.
- The complete executed pipeline assembling all 23 wide-table fields, including asymmetry indices, has not been established. No missing formula or repair history was invented.
- Numerical agreement and source publication do not establish anatomical validity, independent validation, training benefit or broad population generalization.

## Environment and privacy

Local scientific runtime: Python 3.12; NumPy 2.4.6; pandas 3.0.3; SciPy 1.18.0;
statsmodels 0.14.6; matplotlib 3.11.1; openpyxl 3.1.5. The exact run manifest and
observation-level outputs remain outside the repository. Dependency minimums in
`pyproject.toml` support installation; they are not a frozen claim that every version
combination has been tested.

Only source, tests, documentation, provenance and dependency/CI configuration are
changed by this release. Existing public example/assets files are retained unchanged.
No new CSV/XLSX/TRC, participant images/videos, sensor streams, API credentials or
local analysis output directories are part of the intended upload.
