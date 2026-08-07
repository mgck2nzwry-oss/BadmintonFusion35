from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd

from .alignment.nearest import merge_visual_imu, nearest_time_mapping
from .calibration.control_points import expected_control_points, validate_control_points, write_control_points
from .imu.filtering import filter_contiguous_segments
from .qc.inclusion import apply_inclusion_rules


def build_demo(output_dir: str | Path) -> dict[str, object]:
    """Create a small synthetic, non-identifiable end-to-end demonstration."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    points = expected_control_points()
    points_path = write_control_points(points, output / "control_points_35.csv")

    visual_time = np.arange(0.0, 3.0, 1.0 / 60.0)
    imu_time = np.arange(0.0, 3.0, 1.0 / 50.0)
    visual = pd.DataFrame(
        {
            "time_s": visual_time,
            "wrist_height_m": 1.2 + 0.25 * np.sin(2 * np.pi * 1.2 * visual_time),
        }
    )
    raw_imu = np.sin(2 * np.pi * 1.2 * imu_time) + 0.05 * np.cos(2 * np.pi * 8 * imu_time)
    raw_imu[70:73] = np.nan
    filtered, filter_audit = filter_contiguous_segments(raw_imu)
    imu = pd.DataFrame({"time_s": imu_time, "gyro_y_deg_s": raw_imu, "gyro_y_filtered": filtered})
    mapping, mapping_audit = nearest_time_mapping(visual_time, imu_time)
    joint = merge_visual_imu(visual, imu, mapping)

    inclusion_input = pd.DataFrame(
        {
            "Participant": ["DEMO"] * 4,
            "Trial": ["A01"] * 4,
            "Device": ["WTRhand", "WTLhand", "WTRknee", "WTLknee"],
            "OpticalComparisonEligible": [True, True, False, True],
            "ValidPercent": [99.0, 93.0, 99.5, 88.0],
        }
    )
    inclusion = apply_inclusion_rules(inclusion_input)

    visual.to_csv(output / "visual_60hz.csv", index=False)
    imu.to_csv(output / "imu_50hz.csv", index=False)
    mapping.to_csv(output / "mapping_60_to_50.csv", index=False)
    joint.to_csv(output / "visual_imu_joint.csv", index=False)
    inclusion.to_csv(output / "qc_inclusion.csv", index=False)
    report = {
        "status": "PASS",
        "synthetic_only": True,
        "control_points": validate_control_points(points),
        "filter": filter_audit,
        "mapping": mapping_audit,
        "files": sorted(path.name for path in output.iterdir() if path.is_file()),
    }
    (output / "demo_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report["files"] = sorted(path.name for path in output.iterdir() if path.is_file())
    return report
