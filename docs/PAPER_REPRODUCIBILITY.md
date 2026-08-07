# Paper-level reproducibility boundary

The formal audit workbook can be checked with:

```powershell
court35 audit-paper-workbook `
  --workbook "<PAPER_AUDIT_WORKBOOK.xlsx>" `
  --report "reports/paper_workbook_audit.json"
```

The audit independently verifies the 87 retained participant-action units, the four
variable-specific quality-gate counts, the 12-feature PCA variance, the 19/23 FDR
membership and P10 sensitivity, all 87 out-of-fold probability rows, accuracy,
balanced accuracy, micro/macro and per-action AUCs, and the 2,000-iteration
participant-cluster bootstrap confidence intervals using seed `20260805`.

For each of the 23 predefined variables, the action test is independently refitted as
`ln(1+x) ~ Action + Participant`, with participant as a fixed blocking factor. Action
sum of squares is obtained from the full-versus-reduced model comparison, partial
eta-squared is reported, and all 23 p-values are corrected together by the
Benjamini-Hochberg procedure. The same pipeline is repeated after excluding P10.

The workbook does not record the classifier family, hyperparameters or fitting code.
Consequently, the published out-of-fold probabilities and every reported ROC statistic
are auditable, but model training is not yet reproducible. The repository must describe
this as a limitation until an authoritative training script or specification is found.
