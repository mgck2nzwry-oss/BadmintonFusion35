from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import f as f_distribution


def benjamini_hochberg(p_values: np.ndarray, *, alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(p_values, dtype=float)
    if values.ndim != 1:
        raise ValueError("p_values must be one-dimensional")
    finite = np.isfinite(values)
    adjusted = np.full(values.shape, np.nan, dtype=float)
    rejected = np.zeros(values.shape, dtype=bool)
    finite_values = values[finite]
    if not len(finite_values):
        return adjusted, rejected
    if np.any((finite_values < 0) | (finite_values > 1)):
        raise ValueError("Finite p-values must be in [0, 1]")
    order = np.argsort(finite_values, kind="stable")
    ranked = finite_values[order]
    count = len(ranked)
    raw_adjusted = ranked * count / np.arange(1, count + 1)
    monotone = np.minimum.accumulate(raw_adjusted[::-1])[::-1]
    monotone = np.clip(monotone, 0, 1)
    restored = np.empty_like(monotone)
    restored[order] = monotone
    adjusted[finite] = restored
    rejected[finite] = restored <= alpha
    return adjusted, rejected


def pca_standardized(
    data: pd.DataFrame | np.ndarray,
    *,
    n_components: int | None = None,
) -> dict[str, np.ndarray]:
    values = np.asarray(data, dtype=float)
    if values.ndim != 2 or min(values.shape) < 2:
        raise ValueError("PCA input must be a two-dimensional matrix")
    if not np.isfinite(values).all():
        raise ValueError("PCA input contains missing or infinite values; imputation must be explicit")
    mean = values.mean(axis=0)
    scale = values.std(axis=0, ddof=1)
    if np.any(scale <= 0):
        raise ValueError("PCA input contains a zero-variance feature")
    standardized = (values - mean) / scale
    _, singular, vt = np.linalg.svd(standardized, full_matrices=False)
    eigenvalues = singular**2 / (values.shape[0] - 1)
    explained = eigenvalues / eigenvalues.sum()
    count = min(n_components or len(explained), len(explained))
    components = vt[:count]
    scores = standardized @ components.T
    return {
        "mean": mean,
        "scale": scale,
        "components": components,
        "scores": scores,
        "explained_variance": eigenvalues[:count],
        "explained_variance_ratio": explained[:count],
    }


def participant_blocked_action_effects(
    data: pd.DataFrame,
    features: list[str] | tuple[str, ...],
    *,
    participant_column: str = "Participant",
    action_column: str = "Action",
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Fit ln(1+x) ~ Action + Participant and FDR-correct action effects.

    Participant is treated as a fixed blocking factor. The action sum of squares is
    obtained by comparing the full model with a participant-only reduced model.
    """
    missing_columns = [
        column
        for column in (participant_column, action_column, *features)
        if column not in data
    ]
    if missing_columns:
        raise ValueError(f"Missing analysis columns: {missing_columns}")
    rows: list[dict[str, object]] = []
    for feature in features:
        frame = data[[participant_column, action_column, feature]].copy()
        frame[feature] = pd.to_numeric(frame[feature], errors="coerce")
        frame = frame.dropna()
        values = frame[feature].to_numpy(dtype=float)
        if np.any(values <= -1):
            raise ValueError(f"Feature {feature} contains values outside the ln(1+x) domain")
        response = np.log1p(values)
        participant_terms = pd.get_dummies(
            frame[participant_column].astype(str), drop_first=True, dtype=float
        ).to_numpy()
        action_terms = pd.get_dummies(
            frame[action_column].astype(str), drop_first=True, dtype=float
        ).to_numpy()
        reduced = np.column_stack((np.ones(len(frame)), participant_terms))
        full = np.column_stack((reduced, action_terms))
        reduced_rank = int(np.linalg.matrix_rank(reduced))
        full_rank = int(np.linalg.matrix_rank(full))
        action_df = full_rank - reduced_rank
        error_df = len(frame) - full_rank
        if action_df <= 0 or error_df <= 0:
            raise ValueError(f"Insufficient design rank for feature {feature}")
        reduced_fit = reduced @ np.linalg.lstsq(reduced, response, rcond=None)[0]
        full_fit = full @ np.linalg.lstsq(full, response, rcond=None)[0]
        reduced_sse = float(np.sum((response - reduced_fit) ** 2))
        full_sse = float(np.sum((response - full_fit) ** 2))
        action_ss = max(0.0, reduced_sse - full_sse)
        if full_sse <= 0:
            raise ValueError(f"Zero residual variance for feature {feature}")
        f_value = (action_ss / action_df) / (full_sse / error_df)
        p_value = float(f_distribution.sf(f_value, action_df, error_df))
        partial_eta_squared = action_ss / (action_ss + full_sse)
        rows.append(
            {
                "Feature": feature,
                "N": int(len(frame)),
                "ActionDF": action_df,
                "ErrorDF": error_df,
                "F": float(f_value),
                "PValue": p_value,
                "PartialEtaSquared": float(partial_eta_squared),
            }
        )
    result = pd.DataFrame(rows)
    adjusted, rejected = benjamini_hochberg(
        result["PValue"].to_numpy(dtype=float), alpha=alpha
    )
    result["P_FDR_BH"] = adjusted
    result["FDR_Significant"] = rejected
    return result
