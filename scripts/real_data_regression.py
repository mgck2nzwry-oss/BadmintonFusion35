from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from badminton_court35.alignment.nearest import nearest_time_mapping
from badminton_court35.calibration.control_points import read_control_points, validate_control_points
from badminton_court35.imu.filtering import filter_contiguous_segments
from badminton_court35.imu.timebase import reconstruct_timestamp
from badminton_court35.io.trc import read_trc
from badminton_court35.qc.inclusion import apply_inclusion_rules


def main() -> int:
    parser = ArgumentParser(description="Run non-destructive regressions against formal local evidence")
    parser.add_argument("--points", required=True)
    parser.add_argument("--imu-merged", required=True)
    parser.add_argument("--joint-mapping", required=True)
    parser.add_argument(
        "--visual-trc",
        required=True,
        help="Original visual TRC used to build the authoritative joint table",
    )
    parser.add_argument(
        "--imu-source",
        required=True,
        help="Original action-level 50 Hz IMU table used for nearest mapping",
    )
    parser.add_argument("--imu-source-time", default="P03_IMU_50Hz_time_s")
    parser.add_argument("--qc-input", required=True)
    parser.add_argument("--qc-authoritative", required=True)
    parser.add_argument("--filtered-imu", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    results: dict[str, object] = {}
    results["control_points"] = validate_control_points(read_control_points(args.points))

    time_data = pd.read_csv(
        args.imu_merged,
        usecols=["HostTime_s", "ReconstructedHostTime_s"],
        low_memory=False,
    )
    rebuilt = reconstruct_timestamp(pd.to_numeric(time_data["HostTime_s"], errors="coerce"))
    authoritative_time = pd.to_numeric(
        time_data["ReconstructedHostTime_s"], errors="coerce"
    ).to_numpy(float)
    difference = np.abs(rebuilt - authoritative_time)
    results["timebase"] = {
        "status": "PASS" if np.nanmax(difference) <= 1e-6 else "FAIL",
        "rows": int(len(rebuilt)),
        "strictly_increasing": bool(np.all(np.diff(rebuilt) > 0)),
        "max_abs_difference_from_authoritative_s": float(np.nanmax(difference)),
    }

    # Use the original pre-export time vectors here. The joint CSV rounds decimal
    # timestamps, and midpoint rows can therefore lose the floating-point ordering
    # that selected the authoritative earlier/later 50 Hz sample.
    authoritative = pd.read_csv(
        args.joint_mapping,
        usecols=["P03_IMU_nearest_sample_index"],
        low_memory=False,
    )
    visual = read_trc(args.visual_trc)
    visual_time = pd.to_numeric(visual["Time"], errors="coerce").to_numpy(float)
    visual_elapsed = visual_time - visual_time[0]
    imu_source = pd.read_csv(
        args.imu_source,
        usecols=[args.imu_source_time],
        low_memory=False,
    )
    imu_time = pd.to_numeric(
        imu_source[args.imu_source_time], errors="coerce"
    ).to_numpy(float)
    mapping, mapping_audit = nearest_time_mapping(visual_elapsed, imu_time)
    authoritative_indices = authoritative["P03_IMU_nearest_sample_index"].to_numpy(int)
    same_length = len(mapping) == len(authoritative_indices)
    if same_length:
        index_match = (
            mapping["imu_nearest_sample_index"].to_numpy(int) == authoritative_indices
        )
        match_fraction = float(index_match.mean())
        all_match = bool(index_match.all())
    else:
        match_fraction = 0.0
        all_match = False
    mapping_audit["authoritative_index_match_fraction"] = match_fraction
    mapping_audit["authoritative_row_count_match"] = same_length
    mapping_audit["source_precision"] = "original_trc_and_original_50hz_imu"
    mapping_audit["status"] = (
        "PASS" if mapping_audit["status"] == "PASS" and all_match else "FAIL"
    )
    results["nearest_mapping"] = mapping_audit

    qc_input = pd.read_csv(args.qc_input, low_memory=False)
    qc_expected = pd.read_csv(
        args.qc_authoritative, usecols=["JointAnalysisStatus"], low_memory=False
    )
    qc_actual = apply_inclusion_rules(qc_input)
    qc_match = (
        qc_actual["JointAnalysisStatus"].astype(str).to_numpy()
        == qc_expected["JointAnalysisStatus"].astype(str).to_numpy()
    )
    results["quality_control"] = {
        "status": "PASS" if len(qc_actual) == len(qc_expected) and qc_match.all() else "FAIL",
        "rows": int(len(qc_actual)),
        "authoritative_status_match_fraction": float(qc_match.mean()),
    }

    imu = pd.read_csv(args.filtered_imu, low_memory=False)
    acceleration_columns = [column for column in imu.columns if "加速度" in column]
    if not acceleration_columns:
        raise ValueError("No acceleration column found in filtered IMU regression input")
    regression_column = acceleration_columns[0]
    values = pd.to_numeric(imu[regression_column], errors="coerce").to_numpy(float)
    filtered, filter_audit = filter_contiguous_segments(values)
    filter_audit["regression_column"] = regression_column
    filter_audit["missing_mask_unchanged"] = bool(
        np.array_equal(np.isnan(values), np.isnan(filtered))
    )
    filter_audit["status"] = "PASS" if filter_audit["missing_mask_unchanged"] else "FAIL"
    results["filtering"] = filter_audit

    component_statuses = [
        str(value.get("status"))
        for value in results.values()
        if isinstance(value, dict)
    ]
    report = {
        "status": "PASS" if all(status == "PASS" for status in component_statuses) else "FAIL",
        "non_destructive": True,
        "results": results,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
