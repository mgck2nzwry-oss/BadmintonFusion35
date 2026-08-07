from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from badminton_court35.alignment.nearest import merge_visual_imu, nearest_time_mapping
from badminton_court35.analysis.stats import (
    benjamini_hochberg,
    participant_blocked_action_effects,
    pca_standardized,
)
from badminton_court35.analysis.paper import binary_roc_auc, multiclass_roc_metrics
from badminton_court35.calibration.audit import audit_residual_table
from badminton_court35.calibration.control_points import (
    expected_control_points,
    read_control_points,
    validate_control_points,
    write_control_points,
)
from badminton_court35.demo import build_demo
from badminton_court35.imu.filtering import filter_contiguous_segments
from badminton_court35.imu.timebase import reconstruct_timestamp, timebase_audit
from badminton_court35.qc.inclusion import apply_inclusion_rules


class ControlPointTests(unittest.TestCase):
    def test_formal_layout(self) -> None:
        points = expected_control_points()
        report = validate_control_points(points)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["ground_count"], 25)
        self.assertEqual(report["elevated_count"], 10)
        self.assertEqual(report["coordinate_rank"], 3)

    def test_round_trip_csv(self) -> None:
        with TemporaryDirectory() as directory:
            path = write_control_points(expected_control_points(), Path(directory) / "points.csv")
            self.assertEqual(read_control_points(path), expected_control_points())


class TimeAndFilterTests(unittest.TestCase):
    def test_batched_time_and_midnight(self) -> None:
        raw = np.array([86399.90, 86399.90, 86399.94, 0.02, 0.02, 0.06])
        rebuilt = reconstruct_timestamp(raw)
        self.assertTrue(np.all(np.diff(rebuilt) > 0))
        self.assertEqual(timebase_audit(rebuilt)["status"], "PASS")
        self.assertGreater(rebuilt[-1], 86400.0)

    def test_filter_preserves_gap(self) -> None:
        time = np.arange(300) / 50.0
        values = np.sin(2 * np.pi * time) + 0.1 * np.sin(2 * np.pi * 15 * time)
        values[100:110] = np.nan
        filtered, audit = filter_contiguous_segments(values)
        self.assertTrue(np.isnan(filtered[100:110]).all())
        self.assertEqual(audit["missing_samples_preserved"], 10)
        self.assertGreaterEqual(audit["filtered_runs"], 2)


class MappingAndQCTests(unittest.TestCase):
    def test_60_to_50_mapping(self) -> None:
        visual_time = np.arange(0, 2, 1 / 60)
        imu_time = np.arange(0, 2, 1 / 50)
        mapping, audit = nearest_time_mapping(visual_time, imu_time)
        self.assertEqual(audit["status"], "PASS")
        self.assertLessEqual(audit["max_abs_timing_error_ms"], 10.000001)
        self.assertLessEqual(audit["max_imu_reuse_count"], 2)
        visual = pd.DataFrame({"time": visual_time})
        imu = pd.DataFrame({"time": imu_time, "value": np.arange(len(imu_time))})
        merged = merge_visual_imu(visual, imu, mapping)
        self.assertEqual(len(merged), len(visual))

    def test_variable_specific_qc(self) -> None:
        data = pd.DataFrame(
            {
                "OpticalComparisonEligible": [True, True, True, False],
                "ValidPercent": [96, 92, 80, 100],
            }
        )
        result = apply_inclusion_rules(data)
        self.assertEqual(
            result["JointAnalysisStatus"].tolist(),
            ["Main_Analysis", "Sensitivity_Only", "Excluded_IMU", "Excluded_Optical"],
        )


class AnalysisTests(unittest.TestCase):
    def test_participant_blocked_action_effect(self) -> None:
        frame = pd.DataFrame(
            {
                "Participant": np.repeat(["P01", "P02", "P03", "P04"], 2),
                "Action": ["A01", "A02"] * 4,
                "signal": [1.0, 10.0, 1.2, 11.0, 0.9, 9.0, 1.1, 12.0],
            }
        )
        result = participant_blocked_action_effects(frame, ["signal"])
        self.assertEqual(result.loc[0, "ActionDF"], 1)
        self.assertTrue(result.loc[0, "FDR_Significant"])
        self.assertGreater(result.loc[0, "PartialEtaSquared"], 0.90)

    def test_tie_aware_auc_and_multiclass_metrics(self) -> None:
        self.assertAlmostEqual(binary_roc_auc([False, True, False, True], [0, 1, 0, 1]), 1.0)
        labels = ["A01", "A02", "A01", "A02"]
        probabilities = np.array([[0.9, 0.1], [0.2, 0.8], [0.8, 0.2], [0.1, 0.9]])
        metrics = multiclass_roc_metrics(labels, probabilities, ("A01", "A02"))
        self.assertAlmostEqual(metrics["Micro"], 1.0)
        self.assertAlmostEqual(metrics["Macro"], 1.0)

    def test_bh_is_monotone_in_rank(self) -> None:
        p = np.array([0.001, 0.02, 0.04, 0.2, np.nan])
        adjusted, rejected = benjamini_hochberg(p)
        self.assertTrue(rejected[0])
        self.assertTrue(np.isnan(adjusted[-1]))
        order = np.argsort(p[:-1])
        self.assertTrue(np.all(np.diff(adjusted[:-1][order]) >= -1e-12))

    def test_standardized_pca(self) -> None:
        rng = np.random.default_rng(7)
        base = rng.normal(size=40)
        matrix = np.column_stack((base, 2 * base + rng.normal(scale=0.05, size=40), rng.normal(size=40)))
        result = pca_standardized(matrix, n_components=2)
        self.assertEqual(result["scores"].shape, (40, 2))
        self.assertGreater(result["explained_variance_ratio"][0], 0.60)


class AuditAndDemoTests(unittest.TestCase):
    def test_calibration_audit_and_demo(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            residuals = pd.DataFrame(
                {
                    "Camera": ["cam01"] * 6 + ["cam02"] * 6,
                    "Point_ID": [f"P{i:02d}" for i in range(1, 7)] * 2,
                    "Residual_px": [1, 2, 3, 2, 1, 2] * 2,
                    "Camera_true_RMSE_px": [2.0] * 12,
                    "Robust_inlier_count": [6] * 12,
                    "Robust_inlier_RMSE_px": [1.8] * 12,
                }
            )
            residual_path = root / "residuals.csv"
            residuals.to_csv(residual_path, index=False)
            summary, report = audit_residual_table(residual_path)
            self.assertEqual(len(summary), 2)
            self.assertEqual(report["status"], "REVIEW_REQUIRED")

            demo_report = build_demo(root / "demo")
            self.assertEqual(demo_report["status"], "PASS")
            self.assertTrue((root / "demo" / "demo_audit.json").exists())


if __name__ == "__main__":
    unittest.main()
