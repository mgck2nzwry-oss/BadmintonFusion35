from __future__ import annotations

import warnings
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .stats import participant_blocked_action_effects


FORMAL_ACTIONS = tuple(f"A{index:02d}" for index in range(1, 11))
FORMAL_PROBABILITY_COLUMNS = tuple(f"Probability_{action}" for action in FORMAL_ACTIONS)


def binary_roc_auc(y_true: Iterable[bool], score: Iterable[float]) -> float:
    """Compute tie-aware binary ROC AUC using the Mann-Whitney rank identity."""
    labels = np.asarray(list(y_true), dtype=bool)
    values = np.asarray(list(score), dtype=float)
    if labels.ndim != 1 or values.ndim != 1 or len(labels) != len(values):
        raise ValueError("y_true and score must be equal-length one-dimensional arrays")
    if not np.isfinite(values).all():
        raise ValueError("ROC scores must be finite")
    positive_n = int(labels.sum())
    negative_n = int(len(labels) - positive_n)
    if positive_n == 0 or negative_n == 0:
        raise ValueError("ROC AUC requires both positive and negative observations")

    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    sorted_ranks = np.empty(len(values), dtype=float)
    start = 0
    while start < len(values):
        stop = start + 1
        while stop < len(values) and sorted_values[stop] == sorted_values[start]:
            stop += 1
        sorted_ranks[start:stop] = (start + 1 + stop) / 2.0
        start = stop
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = sorted_ranks
    rank_sum = float(ranks[labels].sum())
    return (rank_sum - positive_n * (positive_n + 1) / 2.0) / (
        positive_n * negative_n
    )


def multiclass_roc_metrics(
    labels: Iterable[str],
    probabilities: np.ndarray,
    classes: tuple[str, ...] = FORMAL_ACTIONS,
) -> dict[str, float]:
    actual = np.asarray(list(labels), dtype=str)
    scores = np.asarray(probabilities, dtype=float)
    if scores.shape != (len(actual), len(classes)):
        raise ValueError("Probability matrix shape does not match labels/classes")
    one_hot = actual[:, None] == np.asarray(classes, dtype=str)[None, :]
    metrics = {
        action: binary_roc_auc(one_hot[:, index], scores[:, index])
        for index, action in enumerate(classes)
    }
    metrics["Micro"] = binary_roc_auc(one_hot.ravel(), scores.ravel())
    metrics["Macro"] = float(np.mean([metrics[action] for action in classes]))
    return metrics


def cluster_bootstrap_roc(
    labels: Iterable[str],
    probabilities: np.ndarray,
    participants: Iterable[str],
    *,
    classes: tuple[str, ...] = FORMAL_ACTIONS,
    iterations: int = 2000,
    seed: int = 20260805,
) -> dict[str, tuple[float, float]]:
    if iterations < 1:
        raise ValueError("iterations must be positive")
    actual = np.asarray(list(labels), dtype=str)
    groups = np.asarray(list(participants), dtype=str)
    scores = np.asarray(probabilities, dtype=float)
    if len(groups) != len(actual):
        raise ValueError("Participant and label arrays must have equal length")
    unique_groups = np.unique(groups)
    curve_order = ("Micro", "Macro", *classes)
    samples = np.full((iterations, len(curve_order)), np.nan, dtype=float)
    rng = np.random.default_rng(seed)
    for iteration in range(iterations):
        selected_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        selected_rows = np.concatenate(
            [np.flatnonzero(groups == group) for group in selected_groups]
        )
        try:
            metrics = multiclass_roc_metrics(
                actual[selected_rows], scores[selected_rows], classes
            )
        except ValueError:
            continue
        samples[iteration] = [metrics[curve] for curve in curve_order]
    valid_counts = np.isfinite(samples).sum(axis=0)
    if np.any(valid_counts == 0):
        missing = [curve_order[index] for index in np.flatnonzero(valid_counts == 0)]
        raise ValueError(f"No valid bootstrap estimates for curves: {missing}")
    limits = np.nanquantile(samples, [0.025, 0.975], axis=0)
    return {
        curve: (float(limits[0, index]), float(limits[1, index]))
        for index, curve in enumerate(curve_order)
    }


def audit_paper_tables(
    tables: dict[str, pd.DataFrame],
    *,
    bootstrap_iterations: int = 2000,
    bootstrap_seed: int = 20260805,
    tolerance: float = 1e-12,
) -> dict[str, object]:
    feature_dictionary = tables["feature_dictionary"]
    quality = tables["quality_gates"]
    pca_scores = tables["pca_scores"]
    pca_loadings = tables["pca_loadings"]
    fdr = tables["fdr_sets"]
    predictions = tables["roc_predictions"]
    roc_results = tables["roc_results"]
    readme = tables["readme"]

    feature_count = int(len(feature_dictionary))
    gate_counts = {
        "formal_action_units": int(len(quality)),
        "visual_general_units": int(quality["VisualGeneralEligible"].astype(bool).sum()),
        "right_wrist_units": int(quality["RWristEligible"].astype(bool).sum()),
        "left_wrist_units": int(quality["LWristEligible"].astype(bool).sum()),
        "strict_imu_units": int(quality["IMUStrictEligible"].astype(bool).sum()),
    }
    expected_gate_counts = {
        "formal_action_units": 87,
        "visual_general_units": 84,
        "right_wrist_units": 70,
        "left_wrist_units": 72,
        "strict_imu_units": 87,
    }

    pc_columns = [f"PC{index}" for index in range(1, 13)]
    pc_matrix = pca_scores[pc_columns].to_numpy(dtype=float)
    pc_variances = np.var(pc_matrix, axis=0, ddof=1)
    first_two_ratio = float(pc_variances[:2].sum() / pc_variances.sum())
    stated_first_two_ratio = float(readme.iloc[4, 4])
    pca_report = {
        "status": "PASS"
        if len(pca_scores) == 87
        and len(pca_loadings) == 12
        and abs(first_two_ratio - stated_first_two_ratio) <= tolerance
        else "FAIL",
        "score_rows": int(len(pca_scores)),
        "loading_features": int(len(pca_loadings)),
        "first_two_explained_variance_ratio": first_two_ratio,
        "stated_first_two_explained_variance_ratio": stated_first_two_ratio,
    }

    fdr_full = fdr["FDR_Significant_Full"].astype(bool)
    fdr_without_p10 = fdr["FDR_Significant_ExcludeP10"].astype(bool)
    large_effect = fdr["LargeEffect_Eta2_GE_0_14"].astype(bool)
    feature_order = feature_dictionary["Feature"].astype(str).tolist()
    recomputed_full = participant_blocked_action_effects(quality, feature_order).set_index(
        "Feature"
    )
    recomputed_without_p10 = participant_blocked_action_effects(
        quality.loc[quality["Participant"].astype(str) != "P10"], feature_order
    ).set_index("Feature")
    expected_fdr = fdr.set_index("Feature").loc[feature_order]
    max_q_difference = float(
        np.max(
            np.abs(
                recomputed_full.loc[feature_order, "P_FDR_BH"].to_numpy(float)
                - expected_fdr["P_FDR_BH"].to_numpy(float)
            )
        )
    )
    max_eta_difference = float(
        np.max(
            np.abs(
                recomputed_full.loc[feature_order, "PartialEtaSquared"].to_numpy(float)
                - expected_fdr["PartialEtaSquared"].to_numpy(float)
            )
        )
    )
    full_membership_match = bool(
        np.array_equal(
            recomputed_full.loc[feature_order, "FDR_Significant"].to_numpy(bool),
            expected_fdr["FDR_Significant_Full"].to_numpy(bool),
        )
    )
    sensitivity_membership_match = bool(
        np.array_equal(
            recomputed_without_p10.loc[feature_order, "FDR_Significant"].to_numpy(bool),
            expected_fdr["FDR_Significant_ExcludeP10"].to_numpy(bool),
        )
    )
    fdr_report = {
        "status": "PASS"
        if len(fdr) == 23
        and int(fdr_full.sum()) == 19
        and np.array_equal(fdr_full.to_numpy(), fdr_without_p10.to_numpy())
        and int(large_effect.sum()) == 22
        and max_q_difference <= tolerance
        and max_eta_difference <= tolerance
        and full_membership_match
        and sensitivity_membership_match
        else "FAIL",
        "features": int(len(fdr)),
        "fdr_significant_full": int(fdr_full.sum()),
        "fdr_significant_exclude_p10": int(fdr_without_p10.sum()),
        "significant_membership_identical": bool(
            np.array_equal(fdr_full.to_numpy(), fdr_without_p10.to_numpy())
        ),
        "large_effect_features": int(large_effect.sum()),
        "recomputed_max_abs_fdr_q_difference": max_q_difference,
        "recomputed_max_abs_partial_eta_squared_difference": max_eta_difference,
        "recomputed_full_membership_matches": full_membership_match,
        "recomputed_exclude_p10_membership_matches": sensitivity_membership_match,
    }

    probability_matrix = predictions[list(FORMAL_PROBABILITY_COLUMNS)].to_numpy(float)
    actual = predictions["Action"].astype(str).to_numpy()
    participants = predictions["Participant"].astype(str).to_numpy()
    predicted_from_probability = np.asarray(FORMAL_ACTIONS)[np.argmax(probability_matrix, axis=1)]
    probability_sum_error = float(np.max(np.abs(probability_matrix.sum(axis=1) - 1.0)))
    point_metrics = multiclass_roc_metrics(actual, probability_matrix)
    intervals = cluster_bootstrap_roc(
        actual,
        probability_matrix,
        participants,
        iterations=bootstrap_iterations,
        seed=bootstrap_seed,
    )
    expected_curves = roc_results.set_index("Curve")
    curve_order = ("Micro", "Macro", *FORMAL_ACTIONS)
    auc_matches = {
        curve: abs(point_metrics[curve] - float(expected_curves.loc[curve, "AUC"])) <= tolerance
        for curve in curve_order
    }
    ci_matches = {
        curve: (
            abs(intervals[curve][0] - float(expected_curves.loc[curve, "CI95_Lower"]))
            <= tolerance
            and abs(intervals[curve][1] - float(expected_curves.loc[curve, "CI95_Upper"]))
            <= tolerance
        )
        for curve in curve_order
    }
    accuracy = float(np.mean(predicted_from_probability == actual))
    recalls = [
        float(np.mean(predicted_from_probability[actual == action] == action))
        for action in FORMAL_ACTIONS
    ]
    balanced_accuracy = float(np.mean(recalls))
    roc_report = {
        "status": "PASS"
        if len(predictions) == 87
        and probability_sum_error <= tolerance
        and np.array_equal(
            predicted_from_probability,
            predictions["PredictedAction"].astype(str).to_numpy(),
        )
        and np.array_equal(
            participants,
            predictions["CVFold_HeldOutParticipant"].astype(str).to_numpy(),
        )
        and all(auc_matches.values())
        and all(ci_matches.values())
        else "FAIL",
        "out_of_fold_rows": int(len(predictions)),
        "probability_sum_max_abs_error": probability_sum_error,
        "predicted_action_matches_argmax": bool(
            np.array_equal(
                predicted_from_probability,
                predictions["PredictedAction"].astype(str).to_numpy(),
            )
        ),
        "held_out_participant_matches_row_participant": bool(
            np.array_equal(
                participants,
                predictions["CVFold_HeldOutParticipant"].astype(str).to_numpy(),
            )
        ),
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "micro_auc": point_metrics["Micro"],
        "macro_auc": point_metrics["Macro"],
        "micro_auc_ci95": intervals["Micro"],
        "macro_auc_ci95": intervals["Macro"],
        "bootstrap_iterations": bootstrap_iterations,
        "bootstrap_seed": bootstrap_seed,
        "auc_curve_matches": int(sum(auc_matches.values())),
        "ci_curve_matches": int(sum(ci_matches.values())),
        "curve_count": int(len(curve_order)),
    }

    sections = {
        "data_contract": {
            "status": "PASS"
            if feature_count == 23 and gate_counts == expected_gate_counts
            else "FAIL",
            "feature_count": feature_count,
            **gate_counts,
        },
        "pca": pca_report,
        "fdr_sensitivity": fdr_report,
        "out_of_fold_roc": roc_report,
        "classifier_training": {
            "status": "UNVERIFIED",
            "reason": (
                "The workbook contains out-of-fold probabilities but does not identify "
                "the classifier, hyperparameters or training implementation."
            ),
        },
    }
    auditable_sections = [
        sections["data_contract"],
        sections["pca"],
        sections["fdr_sensitivity"],
        sections["out_of_fold_roc"],
    ]
    return {
        "status": "PASS_WITH_LIMITATION"
        if all(section["status"] == "PASS" for section in auditable_sections)
        else "FAIL",
        "sections": sections,
    }


def audit_paper_workbook(
    workbook: str | Path,
    *,
    bootstrap_iterations: int = 2000,
    bootstrap_seed: int = 20260805,
) -> dict[str, object]:
    """Read the formal audit workbook without modifying it and verify paper outputs."""
    path = Path(workbook)
    try:
        # Some chart/conditional-formatting extensions are irrelevant to a values-only
        # read and cause openpyxl warnings. The source workbook is never saved here.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message="Unknown extension is not supported and will be removed"
            )
            warnings.filterwarnings(
                "ignore",
                message="Conditional Formatting extension is not supported and will be removed",
            )
            tables = {
                "readme": pd.read_excel(
                    path, sheet_name="README", header=None, engine="openpyxl"
                ),
                "feature_dictionary": pd.read_excel(
                    path, sheet_name="特征字典", engine="openpyxl"
                ),
                "quality_gates": pd.read_excel(
                    path, sheet_name="质量门控数据", engine="openpyxl"
                ),
                "pca_scores": pd.read_excel(path, sheet_name="PCA得分", engine="openpyxl"),
                "pca_loadings": pd.read_excel(
                    path, sheet_name="PCA载荷", engine="openpyxl"
                ),
                "fdr_sets": pd.read_excel(path, sheet_name="韦恩集合", engine="openpyxl"),
                "roc_predictions": pd.read_excel(
                    path, sheet_name="ROC折外预测", engine="openpyxl"
                ),
                "roc_results": pd.read_excel(
                    path, sheet_name="ROC结果", engine="openpyxl"
                ),
            }
    except ImportError as exc:
        raise RuntimeError(
            "Paper-workbook audit requires the optional dependency: "
            "pip install 'badminton-court35[paper]'"
        ) from exc
    return audit_paper_tables(
        tables,
        bootstrap_iterations=bootstrap_iterations,
        bootstrap_seed=bootstrap_seed,
    )
