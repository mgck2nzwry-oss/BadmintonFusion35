from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PUBLIC_TIMESERIES_COLUMNS = (
    "device",
    "relative_time_s",
    "valid",
    "dynamic_acceleration_proxy_g",
    "gyro_magnitude_deg_s",
)


def export_public_dashboard_data(
    imu_csv: str | Path,
    metrics_csv: str | Path,
    output_dir: str | Path,
) -> dict[str, object]:
    """Export the de-identified derived fields used by CourtScope.

    The function deliberately excludes raw accelerometer axes, raw gyroscope axes,
    participant names, source paths and provenance hashes. It never edits input files.
    """
    imu_path = Path(imu_csv)
    metrics_path = Path(metrics_csv)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    imu = pd.read_csv(imu_path)
    missing = [column for column in PUBLIC_TIMESERIES_COLUMNS if column not in imu]
    if missing:
        raise ValueError(f"IMU table is missing public dashboard columns: {missing}")

    series = imu.loc[:, PUBLIC_TIMESERIES_COLUMNS].rename(
        columns={
            "relative_time_s": "time",
            "dynamic_acceleration_proxy_g": "dynamicAcceleration",
            "gyro_magnitude_deg_s": "gyroMagnitude",
        }
    )
    series_path = output / "timeseries.json"
    series_path.write_text(
        json.dumps(series.to_dict(orient="records"), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    metrics = pd.read_csv(metrics_path)
    required_metrics = (
        "Device", "BodyLocation", "ValidPercent", "DynamicAccelerationRMS_g",
        "DynamicAccelerationPeak_g", "GyroMagnitudeRMS_deg_s",
        "GyroMagnitudePeak_deg_s", "GyroPeakTime_s", "MetricStatus",
    )
    missing_metrics = [column for column in required_metrics if column not in metrics]
    if missing_metrics:
        raise ValueError(f"Metric table is missing public dashboard columns: {missing_metrics}")
    metrics_path_out = output / "metrics.json"
    metrics_path_out.write_text(
        json.dumps(metrics.loc[:, required_metrics].to_dict(orient="records"), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return {
        "status": "PASS",
        "timeseries_rows": int(len(series)),
        "metric_rows": int(len(metrics)),
        "output_dir": output.as_posix(),
        "privacy_boundary": "derived signals only; no names, raw host paths or raw sensor axes",
    }
