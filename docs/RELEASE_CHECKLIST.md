# Public release checklist

- [ ] Confirm final paper title, author order, ORCIDs and repository owner.
- [x] Obtain co-author/institution approval for the software license (MIT; 2026-08-07).
- [ ] Choose a separate data license and controlled-access policy.
- [ ] Confirm participant consent permits each proposed data tier.
- [ ] Remove names, absolute local paths, device serials, face/voice data and location metadata.
- [ ] Pose2Sim 0.10.49 is recorded; still record the exact pose model and model weights.
- [ ] Record camera models, lens choices, resolution, frame rate and exposure settings.
- [ ] Record IMU model, axis convention, units, firmware and device-to-limb mapping.
- [ ] Reconcile every P01-P10 retained/excluded action from the authoritative manifests.
- [ ] Add held-out spatial calibration validation; do not infer it from pixel RMSE.
- [ ] Identify and implement the authoritative LOPO classifier and all hyperparameters.
- [ ] Reproduce every paper table and figure from a clean environment.
- [x] Add an approved software-level `CITATION.cff`; add the final paper citation after acceptance.
- [x] Run a local secret/path scan and verify that no oversized research data is in the repository.
- [ ] Tag the tested paper version and archive it with a DOI-capable repository.
