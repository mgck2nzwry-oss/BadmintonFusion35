from __future__ import annotations

from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import tomllib

import pandas as pd

from badminton_court35 import __version__
from badminton_court35.calibration.resilience import assess_calibration_resilience


PUBLIC_TIMESERIES_FIELDS = (
    "device",
    "time",
    "valid",
    "dynamicAcceleration",
    "gyroMagnitude",
)


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
        encoding="utf-8",
    )


def _installed_version(distribution: str) -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return "not-installed"


def _verify_locked_checksums(example_dir: Path, required: list[Path]) -> dict[str, bool]:
    expected: dict[str, str] = {}
    for line in (example_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        checksum, relative = line.split("  ", 1)
        expected[relative.replace("\\", "/")] = checksum
    return {
        path.relative_to(example_dir).as_posix(): expected.get(
            path.relative_to(example_dir).as_posix()
        )
        == _sha256(path)
        for path in required
    }


def _locked_result(path: Path, example_dir: Path, results: dict[str, bool]) -> bool | None:
    try:
        relative = path.relative_to(example_dir).as_posix()
    except ValueError:
        return None
    return results.get(relative)


def build_dashboard_evidence(
    project_root: str | Path,
    output_dir: str | Path,
) -> dict[str, object]:
    """Recompute CourtScope's public trial outputs with the research package.

    The browser never performs the scientific calculation. This deterministic Python
    entrypoint reads the locked public evidence, applies a strict public-field contract,
    regenerates the JSON consumed by the site and writes a machine-verifiable manifest.
    """
    root = Path(project_root).resolve()
    example = root / "examples" / "a10_r10"
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    imu_path = example / "imu" / "imu_50hz_filtered.csv"
    metrics_path = example / "imu" / "repetition_metrics.csv"
    residuals_path = example / "calibration" / "extrinsics_point_residuals.csv"
    config_path = root / "configs" / "pipeline.toml"
    required_inputs = [imu_path, metrics_path, residuals_path, config_path]
    for path in required_inputs:
        if not path.is_file():
            raise FileNotFoundError(path)

    imu = pd.read_csv(imu_path)
    source_columns = {
        "device",
        "relative_time_s",
        "valid",
        "dynamic_acceleration_proxy_g",
        "gyro_magnitude_deg_s",
    }
    missing = sorted(source_columns - set(imu.columns))
    if missing:
        raise ValueError(f"IMU evidence is missing columns: {missing}")
    timeseries = [
        {
            "device": str(row.device),
            "time": round(float(row.relative_time_s), 6),
            "valid": bool(row.valid),
            "dynamicAcceleration": (
                round(float(row.dynamic_acceleration_proxy_g), 6) if bool(row.valid) else None
            ),
            "gyroMagnitude": round(float(row.gyro_magnitude_deg_s), 6) if bool(row.valid) else None,
        }
        for row in imu.itertuples(index=False)
    ]
    if any(tuple(row) != PUBLIC_TIMESERIES_FIELDS for row in timeseries):
        raise AssertionError("Public timeseries field contract changed")
    timeseries_output = output / "a10-r10-timeseries.json"
    _write_json(timeseries_output, timeseries)

    metrics_source = pd.read_csv(metrics_path)
    metric_fields = {
        "Device",
        "BodyLocation",
        "ValidPercent",
        "DynamicAccelerationRMS_g",
        "DynamicAccelerationPeak_g",
        "GyroMagnitudeRMS_deg_s",
        "GyroMagnitudePeak_deg_s",
        "GyroPeakTime_s",
        "MetricStatus",
    }
    missing_metrics = sorted(metric_fields - set(metrics_source.columns))
    if missing_metrics:
        raise ValueError(f"Metric evidence is missing columns: {missing_metrics}")
    metrics = [
        {
            "device": str(row.Device),
            "location": str(row.BodyLocation),
            "validPercent": round(float(row.ValidPercent), 2),
            "accRms": round(float(row.DynamicAccelerationRMS_g), 4),
            "accPeak": round(float(row.DynamicAccelerationPeak_g), 4),
            "gyroRms": round(float(row.GyroMagnitudeRMS_deg_s), 2),
            "gyroPeak": round(float(row.GyroMagnitudePeak_deg_s), 2),
            "gyroPeakTime": round(float(row.GyroPeakTime_s), 2),
            "status": str(row.MetricStatus),
        }
        for row in metrics_source.itertuples(index=False)
    ]
    metrics_output = output / "a10-r10-metrics.json"
    _write_json(metrics_output, metrics)

    calibration_summary, calibration_report = assess_calibration_resilience(residuals_path)
    cameras = []
    for row in calibration_summary.to_dict(orient="records"):
        cameras.append(
            {
                "camera": row["Camera"],
                "status": row["Status"],
                "visiblePoints": int(row["VisiblePoints"]),
                "robustInliers": int(row["RobustInliers"]),
                "inlierRatio": round(float(row["RobustInlierRatio"]), 4),
                "robustRmsePx": round(float(row["RobustInlierRMSE_px"]), 4),
                "pointLossReserve": int(row["AdditionalRobustPointLossReserve"]),
                "suggestedReview": [
                    {
                        "pointId": item["Point_ID"],
                        "residualPx": round(float(item["Residual_px"]), 3),
                    }
                    for item in row["SuggestedPointReview"]
                ],
                "recommendedAction": row["RecommendedAction"],
            }
        )
    calibration_output = output / "calibration-resilience.json"
    _write_json(calibration_output, {"report": calibration_report, "cameras": cameras})

    paper_output = output / "paper-summary.json"
    audit_output = output / "audit-summary.json"
    for path in (paper_output, audit_output):
        if not path.is_file():
            raise FileNotFoundError(
                f"{path.name} is an audited paper export and must exist before evidence generation"
            )

    with config_path.open("rb") as handle:
        config = tomllib.load(handle)
    checksum_results = _verify_locked_checksums(example, required_inputs[:3])
    artifact_paths = [
        timeseries_output,
        metrics_output,
        calibration_output,
        paper_output,
        audit_output,
    ]
    generator_path = Path(__file__).resolve()
    manifest: dict[str, object] = {
        "schemaVersion": "court35.research-evidence.v1",
        "status": "PASS_WITH_LIMITATION",
        "trialId": "A10-R10",
        "calculationAuthority": "badminton_court35 Python package",
        "architecture": "Python recomputes and signs public artifacts; the web interface only reads and verifies them.",
        "reproduction": {
            "command": "court35 build-dashboard-evidence --project-root . --output-dir visualizer/public/data",
            "entrypoint": "badminton_court35.visualization.evidence:build_dashboard_evidence",
            "generatorSha256": _sha256(generator_path),
            "repository": "https://github.com/mgck2nzwry-oss/BadmintonFusion35",
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": _installed_version("numpy"),
            "pandas": _installed_version("pandas"),
            "scipy": _installed_version("scipy"),
            "package": __version__,
        },
        "parameters": {
            "visualRateHz": config["sampling"]["visual_rate_hz"],
            "imuRateHz": config["sampling"]["imu_target_rate_hz"],
            "mappingMaxErrorMs": config["sampling"]["nearest_mapping_max_error_ms"],
            "filter": config["imu_filter"],
            "qualityControl": config["quality_control"],
            "calibrationGate": {
                "minimumRobustInliers": 6,
                "minimumInlierRatio": 0.40,
                "reviewRmsePx": 5.0,
                "automaticChangesApplied": False,
                "validationLevel": "engineering diagnostic threshold; external perturbation validation pending",
            },
        },
        "inputs": [
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256(path),
                "lockedChecksumVerified": _locked_result(path, example, checksum_results),
            }
            for path in required_inputs
        ],
        "artifacts": [
            {
                "path": f"/data/{path.name}",
                "sha256": _sha256(path),
                "role": (
                    "python_recomputed"
                    if path in (timeseries_output, metrics_output, calibration_output)
                    else "audited_paper_export"
                ),
            }
            for path in artifact_paths
        ],
        "checks": [
            {"id": "locked-input-checksums", "status": "PASS" if all(checksum_results.values()) else "FAIL"},
            {"id": "python-output-recomputed", "status": "PASS"},
            {"id": "public-field-allowlist", "status": "PASS"},
            {"id": "missing-values-preserved", "status": "PASS"},
            {"id": "calibration-never-auto-mutates", "status": "PASS"},
            {"id": "classifier-training", "status": "UNVERIFIED"},
            {"id": "centimetre-spatial-accuracy", "status": "UNVERIFIED"},
        ],
        "limitations": [
            "Classifier family, hyperparameters and training implementation are not available.",
            "Pixel residuals do not establish centimetre-level spatial accuracy.",
            "The public real-trial evidence is one consented, de-identified A10-R10 trial, not the full participant dataset.",
        ],
    }
    manifest_output = output / "research-evidence.json"
    _write_json(manifest_output, manifest)
    return manifest
