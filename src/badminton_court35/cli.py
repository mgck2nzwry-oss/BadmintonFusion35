from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

from .alignment.nearest import merge_visual_imu, nearest_time_mapping
from .analysis.paper import audit_paper_workbook
from .calibration.audit import audit_residual_table
from .calibration.control_points import (
    expected_control_points,
    read_control_points,
    trc_declared_marker_count,
    validate_control_points,
    write_control_points,
)
from .demo import build_demo
from .imu.filtering import filter_contiguous_segments
from .imu.timebase import reconstruct_timestamp, timebase_audit
from .pipeline.pose2sim import SUPPORTED_STAGES, run_pose2sim
from .qc.inclusion import apply_inclusion_rules


def _json_default(value: object) -> object:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def _emit(report: object, output: str | None = None) -> None:
    payload = json.dumps(report, ensure_ascii=False, indent=2, default=_json_default)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    print(payload)


def _validate_points(args: Namespace) -> int:
    points = read_control_points(args.csv) if args.csv else expected_control_points()
    report = validate_control_points(points)
    if args.trc:
        marker_count = trc_declared_marker_count(args.trc)
        report["trc_declared_marker_count"] = marker_count
        if marker_count != 35:
            report["status"] = "FAIL"
            report["issues"].append(f"TRC declares {marker_count} markers instead of 35")
    _emit(report, args.report)
    return 0 if report["status"] == "PASS" else 2


def _export_points(args: Namespace) -> int:
    path = write_control_points(expected_control_points(), args.output)
    _emit({"status": "PASS", "output": path, "point_count": 35})
    return 0


def _audit_calibration(args: Namespace) -> int:
    summary, report = audit_residual_table(
        args.residuals, robust_pixel_review_threshold=args.robust_pixel_review_threshold
    )
    if args.summary:
        path = Path(args.summary)
        path.parent.mkdir(parents=True, exist_ok=True)
        summary.to_csv(path, index=False, encoding="utf-8-sig")
        report["summary_csv"] = path.as_posix()
    report["cameras"] = summary.to_dict(orient="records")
    _emit(report, args.report)
    return 0


def _reconstruct_time(args: Namespace) -> int:
    data = pd.read_csv(args.input, low_memory=False)
    if args.time_column not in data:
        raise ValueError(f"Column not found: {args.time_column}")
    reconstructed = reconstruct_timestamp(pd.to_numeric(data[args.time_column], errors="coerce"))
    data[args.output_column] = reconstructed
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output, index=False, encoding="utf-8-sig")
    report = timebase_audit(reconstructed)
    report["output"] = output.as_posix()
    _emit(report, args.report)
    return 0


def _filter_imu(args: Namespace) -> int:
    data = pd.read_csv(args.input, low_memory=False)
    columns = args.columns or [
        column for column in data.columns if "加速度" in column or "角速度" in column
    ]
    if not columns:
        raise ValueError("No IMU columns selected or auto-detected")
    audits: dict[str, object] = {}
    for column in columns:
        if column not in data:
            raise ValueError(f"Column not found: {column}")
        filtered, audit = filter_contiguous_segments(
            pd.to_numeric(data[column], errors="coerce").to_numpy(dtype=float),
            sampling_rate_hz=args.rate,
            cutoff_hz=args.cutoff,
            order=args.order,
        )
        data[f"{column}__filtered_{args.cutoff:g}Hz"] = filtered
        audits[column] = audit
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output, index=False, encoding="utf-8-sig")
    _emit({"status": "PASS", "output": output.as_posix(), "columns": audits}, args.report)
    return 0


def _map_nearest(args: Namespace) -> int:
    visual = pd.read_csv(args.visual, low_memory=False)
    imu = pd.read_csv(args.imu, low_memory=False)
    for table, column in ((visual, args.visual_time), (imu, args.imu_time)):
        if column not in table:
            raise ValueError(f"Column not found: {column}")
    mapping, report = nearest_time_mapping(
        pd.to_numeric(visual[args.visual_time], errors="coerce").to_numpy(dtype=float),
        pd.to_numeric(imu[args.imu_time], errors="coerce").to_numpy(dtype=float),
        max_abs_error_ms=args.max_error_ms,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(output, index=False, encoding="utf-8-sig")
    report["mapping_csv"] = output.as_posix()
    if args.joint_output:
        joint = merge_visual_imu(visual, imu, mapping)
        joint_path = Path(args.joint_output)
        joint_path.parent.mkdir(parents=True, exist_ok=True)
        joint.to_csv(joint_path, index=False, encoding="utf-8-sig")
        report["joint_csv"] = joint_path.as_posix()
    _emit(report, args.report)
    return 0 if report["status"] == "PASS" else 2


def _qc_inclusion(args: Namespace) -> int:
    data = pd.read_csv(args.input, low_memory=False)
    result = apply_inclusion_rules(
        data,
        optical_column=args.optical_column,
        imu_valid_percent_column=args.imu_percent_column,
        main_threshold_percent=args.main_threshold,
        exclusion_threshold_percent=args.exclusion_threshold,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False, encoding="utf-8-sig")
    counts = result["JointAnalysisStatus"].value_counts().to_dict()
    _emit({"status": "PASS", "output": output.as_posix(), "counts": counts}, args.report)
    return 0


def _pose2sim(args: Namespace) -> int:
    plan = run_pose2sim(args.config, args.stages, execute=args.execute)
    _emit({"status": "COMPLETED" if args.execute else "DRY_RUN", "stages": plan}, args.report)
    return 0


def _audit_paper(args: Namespace) -> int:
    report = audit_paper_workbook(
        args.workbook,
        bootstrap_iterations=args.bootstrap_iterations,
        bootstrap_seed=args.bootstrap_seed,
    )
    _emit(report, args.report)
    return 0 if report["status"] == "PASS_WITH_LIMITATION" else 2


def _demo(args: Namespace) -> int:
    report = build_demo(args.output_dir)
    _emit(report)
    return 0


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="court35", description="BadmintonCourt35 reproducibility CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    command = sub.add_parser("validate-control-points", help="validate the locked formal 35-point layout")
    command.add_argument("--csv")
    command.add_argument("--trc")
    command.add_argument("--report")
    command.set_defaults(handler=_validate_points)

    command = sub.add_parser("export-control-points", help="write the locked formal 35-point CSV")
    command.add_argument("--output", required=True)
    command.set_defaults(handler=_export_points)

    command = sub.add_parser("audit-calibration", help="audit per-camera pixel residuals")
    command.add_argument("--residuals", required=True)
    command.add_argument("--summary")
    command.add_argument("--report")
    command.add_argument("--robust-pixel-review-threshold", type=float, default=2.0)
    command.set_defaults(handler=_audit_calibration)

    command = sub.add_parser("reconstruct-time", help="rebuild a monotonic IMU timebase")
    command.add_argument("--input", required=True)
    command.add_argument("--time-column", required=True)
    command.add_argument("--output", required=True)
    command.add_argument("--output-column", default="ReconstructedTime_s")
    command.add_argument("--report")
    command.set_defaults(handler=_reconstruct_time)

    command = sub.add_parser("filter-imu", help="filter IMU channels without bridging missing gaps")
    command.add_argument("--input", required=True)
    command.add_argument("--output", required=True)
    command.add_argument("--columns", nargs="+")
    command.add_argument("--rate", type=float, default=50.0)
    command.add_argument("--cutoff", type=float, default=10.0)
    command.add_argument("--order", type=int, default=4)
    command.add_argument("--report")
    command.set_defaults(handler=_filter_imu)

    command = sub.add_parser("map-nearest", help="map 60 Hz visual rows to nearest 50 Hz IMU rows")
    command.add_argument("--visual", required=True)
    command.add_argument("--imu", required=True)
    command.add_argument("--visual-time", required=True)
    command.add_argument("--imu-time", required=True)
    command.add_argument("--output", required=True)
    command.add_argument("--joint-output")
    command.add_argument("--max-error-ms", type=float, default=10.000001)
    command.add_argument("--report")
    command.set_defaults(handler=_map_nearest)

    command = sub.add_parser("qc-inclusion", help="apply locked optical/IMU inclusion gates")
    command.add_argument("--input", required=True)
    command.add_argument("--output", required=True)
    command.add_argument("--optical-column", default="OpticalComparisonEligible")
    command.add_argument("--imu-percent-column", default="ValidPercent")
    command.add_argument("--main-threshold", type=float, default=95.0)
    command.add_argument("--exclusion-threshold", type=float, default=90.0)
    command.add_argument("--report")
    command.set_defaults(handler=_qc_inclusion)

    command = sub.add_parser("pose2sim", help="plan or explicitly execute Pose2Sim stages")
    command.add_argument("--config", required=True)
    command.add_argument("--stages", nargs="+", choices=SUPPORTED_STAGES, required=True)
    command.add_argument("--execute", action="store_true", help="run stages; omission is a safe dry run")
    command.add_argument("--report")
    command.set_defaults(handler=_pose2sim)

    command = sub.add_parser(
        "audit-paper-workbook",
        help="audit the formal PCA, FDR and out-of-fold ROC workbook outputs",
    )
    command.add_argument("--workbook", required=True)
    command.add_argument("--bootstrap-iterations", type=int, default=2000)
    command.add_argument("--bootstrap-seed", type=int, default=20260805)
    command.add_argument("--report")
    command.set_defaults(handler=_audit_paper)

    command = sub.add_parser("demo", help="create an anonymous synthetic end-to-end example")
    command.add_argument("--output-dir", required=True)
    command.set_defaults(handler=_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except Exception as exc:  # one controlled CLI error boundary
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
