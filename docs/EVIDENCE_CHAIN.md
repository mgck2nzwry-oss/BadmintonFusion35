# Complete trial evidence chain

`court35 build-evidence-chain` is the auditable, trial-level control point linking
the experimental workflow to the desktop player and to the paper's code statement.
For a completed trial it verifies, rather than silently recreating, this chain:

`four raw videos → 35-point calibration → camera synchronisation → Pose2Sim 2D → filtered 3D TRC → IMU alignment → QC reports → desktop visualisation`.

For A01 repeat 1 on the formal project:

```powershell
Set-Location "<BadmintonFusion35>"
powershell -ExecutionPolicy Bypass -File scripts\run_complete_evidence_chain.ps1
```

If Pose2Sim resides in another virtual environment, specify it explicitly:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_complete_evidence_chain.ps1 `
  -PythonPath "$env:USERPROFILE\.venv\pose2sim\Scripts\python.exe"
```

The first command is a Pose2Sim dry run.  It has no processing side effect.  Pass
`-ExecutePose2Sim` only after reviewing that plan.  The script then produces
`reports\A01_R01_evidence_chain\evidence_chain.json` next to the formal project.

`COMPLETE_WITH_REVIEW_REQUIRED` is a valid operational result: it means every
required data-bearing stage is present but a review-level quality gate (for example,
camera pixel residuals) requires documented assessment.  It never means absolute
spatial accuracy is proven.  A held-out 3D validation remains necessary for that
claim.
