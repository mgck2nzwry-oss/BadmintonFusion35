"""Study-specific analysis extracted from build_sci_supplement.py.

Source algorithms are preserved, not a recovery of the unarchived historical classifier.
Mixed-model df=9 assumes all ten study actions; use the guarded runner for this design.
Warning strings must be retained. No participant observations are shipped in this module.
"""
import hashlib
import warnings
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import chi2, chi2_contingency, shapiro
from statsmodels.formula.api import mixedlm

SEED = 20260813


BOOTSTRAPS = 2000


FEATURE_NAMES = {
    "visual_duration_s": "动作时长",
    "rwrist_speed_mean_m_s": "右腕平均速度",
    "rwrist_speed_p95_m_s": "右腕P95速度",
    "lwrist_speed_mean_m_s": "左腕平均速度",
    "lwrist_speed_p95_m_s": "左腕P95速度",
    "rknee_angle_rom_deg": "右膝活动范围",
    "lknee_angle_rom_deg": "左膝活动范围",
    "knee_rom_asym_deg": "膝活动范围不对称",
    "relbow_angle_rom_deg": "右肘活动范围",
    "lelbow_angle_rom_deg": "左肘活动范围",
    "elbow_rom_asym_deg": "肘活动范围不对称",
    "wtlhand_gyro_rms_deg_s": "左手角速度RMS",
    "wtrhand_gyro_rms_deg_s": "右手角速度RMS",
    "wtlknee_gyro_rms_deg_s": "左膝角速度RMS",
    "wtrknee_gyro_rms_deg_s": "右膝角速度RMS",
    "hand_gyro_rms_deg_s_asym_index": "手部角速度不对称",
    "knee_gyro_rms_deg_s_asym_index": "膝部角速度不对称",
    "wtlhand_dynamic_acc_rms_g": "左手动态加速度RMS",
    "wtrhand_dynamic_acc_rms_g": "右手动态加速度RMS",
    "wtlknee_dynamic_acc_rms_g": "左膝动态加速度RMS",
    "wtrknee_dynamic_acc_rms_g": "右膝动态加速度RMS",
    "hand_dynamic_acc_rms_g_asym_index": "手部加速度不对称",
    "knee_dynamic_acc_rms_g_asym_index": "膝部加速度不对称",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def bh(values):
    values = np.asarray(values, float)
    order = np.argsort(values, kind="stable")
    ranked = values[order]
    adjusted = np.minimum.accumulate((ranked * len(values) / np.arange(1, len(values) + 1))[::-1])[::-1]
    result = np.empty_like(adjusted)
    result[order] = np.clip(adjusted, 0, 1)
    return result


def design(frame, participant=True, action=True):
    columns = [np.ones(len(frame))]
    if participant:
        columns.append(pd.get_dummies(frame["Participant"].astype(str), drop_first=True, dtype=float).to_numpy())
    if action:
        columns.append(pd.get_dummies(frame["Action"].astype(str), drop_first=True, dtype=float).to_numpy())
    return np.column_stack(columns)


def fixed_model(frame, feature):
    sub = frame[["Participant", "Action", feature]].copy()
    sub[feature] = pd.to_numeric(sub[feature], errors="coerce")
    sub = sub.dropna()
    y = np.log1p(sub[feature].to_numpy(float))
    x_full = design(sub)
    x_reduced = design(sub, participant=True, action=False)
    beta = np.linalg.lstsq(x_full, y, rcond=None)[0]
    fitted = x_full @ beta
    residual = y - fitted
    rank = int(np.linalg.matrix_rank(x_full))
    error_df = int(len(sub) - rank)
    mse = float(residual @ residual / error_df)
    leverage = np.sum((x_full @ np.linalg.pinv(x_full.T @ x_full)) * x_full, axis=1)
    cook = residual**2 / (rank * mse) * leverage / np.maximum((1 - leverage) ** 2, 1e-12)
    standardized = residual / np.sqrt(mse * np.maximum(1 - leverage, 1e-12))
    reduced_resid = y - x_reduced @ np.linalg.lstsq(x_reduced, y, rcond=None)[0]
    full_sse = float(residual @ residual)
    action_ss = max(0.0, float(reduced_resid @ reduced_resid) - full_sse)
    action_df = int(rank - np.linalg.matrix_rank(x_reduced))
    f_value = float((action_ss / action_df) / (full_sse / error_df))
    from scipy.stats import f as f_distribution
    p_value = float(f_distribution.sf(f_value, action_df, error_df))
    eta = float(action_ss / (action_ss + full_sse))
    sw_w, sw_p = shapiro(residual)
    details = sub.copy()
    details["Fitted"] = fitted
    details["Residual"] = residual
    details["StandardizedResidual"] = standardized
    details["Leverage"] = leverage
    details["CooksDistance"] = cook
    return {
        "Feature": feature,
        "特征": FEATURE_NAMES[feature],
        "N": int(len(sub)),
        "动作df": action_df,
        "参与者df": int(sub["Participant"].nunique() - 1),
        "误差df": error_df,
        "F": f_value,
        "P": p_value,
        "偏η²": eta,
        "残差RMSE_log1p": float(np.sqrt(mse)),
        "ShapiroW": float(sw_w),
        "ShapiroP": float(sw_p),
        "最大绝对标准化残差": float(np.max(np.abs(standardized))),
        "最大杠杆值": float(np.max(leverage)),
        "最大Cook距离": float(np.max(cook)),
        "Cook距离大于4/N数": int(np.sum(cook > 4 / len(sub))),
    }, details


def within_parts(frame, feature):
    sub = frame[["Participant", "Action", feature]].dropna().copy()
    actions = sorted(frame["Action"].astype(str).unique())
    mapping = {a: i for i, a in enumerate(actions)}
    parts = []
    for participant, group in sub.groupby("Participant", sort=True):
        y = np.log1p(group[feature].to_numpy(float))
        x = np.zeros((len(group), len(actions) - 1), float)
        for r, action in enumerate(group["Action"].astype(str)):
            idx = mapping[action]
            if idx:
                x[r, idx - 1] = 1.0
        parts.append((str(participant), y - y.mean(), x - x.mean(axis=0)))
    return parts


def eta_from_parts(parts, weights):
    y = np.concatenate([p[1] for p, w in zip(parts, weights) for _ in range(int(w))])
    x = np.vstack([p[2] for p, w in zip(parts, weights) for _ in range(int(w))])
    reduced_sse = float(y @ y)
    residual = y - x @ np.linalg.lstsq(x, y, rcond=None)[0]
    full_sse = float(residual @ residual)
    action_ss = max(0.0, reduced_sse - full_sse)
    return action_ss / (action_ss + full_sse)


def eta_ci(frame, feature, rng):
    parts = within_parts(frame, feature)
    estimates = np.empty(BOOTSTRAPS, float)
    for i in range(BOOTSTRAPS):
        counts = np.bincount(rng.integers(0, len(parts), len(parts)), minlength=len(parts))
        estimates[i] = eta_from_parts(parts, counts)
    return np.quantile(estimates, [0.025, 0.975]).tolist()


def mixed_model(frame, feature):
    sub = frame[["Participant", "Action", feature]].dropna().copy()
    sub["y"] = np.log1p(sub[feature].astype(float))
    fits = {}
    warning_text = []
    for label, formula in (("null", "y ~ 1"), ("full", "y ~ C(Action)")):
        result = None
        last_error = None
        for method in ("lbfgs", "powell"):
            try:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    candidate = mixedlm(formula, sub, groups=sub["Participant"]).fit(
                        reml=False, method=method, maxiter=500, disp=False
                    )
                warning_text.extend(str(w.message) for w in caught)
                if candidate.converged and np.isfinite(candidate.llf):
                    result = candidate
                    break
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
        if result is None:
            raise RuntimeError(last_error or "mixed model did not converge")
        fits[label] = result
    lr = max(0.0, 2 * (fits["full"].llf - fits["null"].llf))
    return {
        "混合模型N": int(len(sub)),
        "参与者组数": int(sub["Participant"].nunique()),
        "混合模型LR": float(lr),
        "混合模型df": 9,
        "混合模型P": float(chi2.sf(lr, 9)),
        "随机截距方差": float(np.asarray(fits["full"].cov_re)[0, 0]),
        "混合模型收敛": True,
        "混合模型警告": " | ".join(sorted(set(warning_text))),
    }


def softmax(scores):
    scores = scores - np.max(scores, axis=1, keepdims=True)
    exp = np.exp(scores)
    return exp / exp.sum(axis=1, keepdims=True)


def fit_multinomial(x, y, n_classes, l2):
    n, p = x.shape
    def unpack(theta):
        return theta[:p * n_classes].reshape(p, n_classes), theta[p * n_classes:]
    def objective(theta):
        w, b = unpack(theta)
        probs = softmax(x @ w + b)
        loss = -np.log(np.maximum(probs[np.arange(n), y], 1e-15)).sum() + 0.5 * l2 * np.sum(w * w)
        diff = probs.copy()
        diff[np.arange(n), y] -= 1
        grad_w = x.T @ diff + l2 * w
        grad_b = diff.sum(axis=0)
        return float(loss), np.concatenate([grad_w.ravel(), grad_b])
    initial = np.zeros(p * n_classes + n_classes, float)
    result = minimize(objective, initial, jac=True, method="L-BFGS-B", options={"maxiter": 1000, "ftol": 1e-12})
    if not result.success:
        raise RuntimeError(result.message)
    return unpack(result.x), int(result.nit)


def predict_probs(model, x):
    w, b = model
    return softmax(x @ w + b)


def standardize_train_test(x_train, x_test):
    mean = x_train.mean(axis=0)
    scale = x_train.std(axis=0, ddof=0)
    scale[scale == 0] = 1.0
    return (x_train - mean) / scale, (x_test - mean) / scale, mean, scale


def metrics(actual, predicted, classes):
    rows = []
    f1s = []
    recalls = []
    for cls in classes:
        tp = int(np.sum((actual == cls) & (predicted == cls)))
        fn = int(np.sum((actual == cls) & (predicted != cls)))
        fp = int(np.sum((actual != cls) & (predicted == cls)))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1s.append(f1); recalls.append(recall)
        rows.append({"Action": cls, "Support": tp + fn, "TP": tp, "Precision": precision, "Recall": recall, "F1": f1})
    return {
        "accuracy": float(np.mean(actual == predicted)),
        "balanced_accuracy": float(np.mean(recalls)),
        "macro_f1": float(np.mean(f1s)),
        "per_class": rows,
    }


def nested_lopo(frame, features):
    data = frame[["Participant", "Action", *features]].dropna().copy()
    classes = sorted(data["Action"].astype(str).unique())
    class_map = {c: i for i, c in enumerate(classes)}
    participants = sorted(data["Participant"].astype(str).unique())
    x_all = np.log1p(data[features].to_numpy(float))
    y_all = np.array([class_map[v] for v in data["Action"].astype(str)])
    p_all = data["Participant"].astype(str).to_numpy()
    a_all = data["Action"].astype(str).to_numpy()
    candidates = [0.01, 0.1, 1.0, 10.0]
    predictions = []
    outer = []
    for held_out in participants:
        train_mask = p_all != held_out
        test_mask = ~train_mask
        train_participants = [p for p in participants if p != held_out]
        candidate_scores = []
        for l2 in candidates:
            fold_scores = []
            for inner_held in train_participants:
                inner_train = train_mask & (p_all != inner_held)
                inner_valid = train_mask & (p_all == inner_held)
                x_tr, x_va, _, _ = standardize_train_test(x_all[inner_train], x_all[inner_valid])
                model, _ = fit_multinomial(x_tr, y_all[inner_train], len(classes), l2)
                pred = np.argmax(predict_probs(model, x_va), axis=1)
                fold_scores.append(float(np.mean(pred == y_all[inner_valid])))
            candidate_scores.append((float(np.mean(fold_scores)), l2))
        best_score, best_l2 = max(candidate_scores, key=lambda item: (item[0], -item[1]))
        x_train, x_test, mean, scale = standardize_train_test(x_all[train_mask], x_all[test_mask])
        model, iterations = fit_multinomial(x_train, y_all[train_mask], len(classes), best_l2)
        probs = predict_probs(model, x_test)
        pred_idx = np.argmax(probs, axis=1)
        for row_idx, global_idx in enumerate(np.flatnonzero(test_mask)):
            record = {
                "Participant": p_all[global_idx],
                "Action": a_all[global_idx],
                "PredictedAction": classes[pred_idx[row_idx]],
                "HeldOutParticipant": held_out,
                "SelectedL2": best_l2,
                "InnerMeanAccuracy": best_score,
            }
            for j, cls in enumerate(classes): record[f"Prob_{cls}"] = float(probs[row_idx, j])
            predictions.append(record)
        outer.append({
            "HeldOutParticipant": held_out,
            "TrainN": int(train_mask.sum()),
            "TestN": int(test_mask.sum()),
            "SelectedL2": best_l2,
            "InnerMeanAccuracy": best_score,
            "OuterAccuracy": float(np.mean(pred_idx == y_all[test_mask])),
            "OptimizerIterations": iterations,
        })
    pred = pd.DataFrame(predictions).sort_values(["Participant", "Action"]).reset_index(drop=True)
    summary = metrics(pred["Action"].to_numpy(), pred["PredictedAction"].to_numpy(), classes)
    per_class = pd.DataFrame(summary.pop("per_class"))
    outer_df = pd.DataFrame(outer)
    return pred, outer_df, per_class, summary


def missingness(frame, features):
    rows = []
    for feature in features:
        missing = frame[feature].isna()
        by_action = pd.crosstab(frame["Action"].astype(str), missing)
        by_participant = pd.crosstab(frame["Participant"].astype(str), missing)
        action_p = np.nan; participant_p = np.nan; min_action = np.nan; min_participant = np.nan
        if missing.any():
            _, action_p, _, exp_a = chi2_contingency(by_action)
            _, participant_p, _, exp_p = chi2_contingency(by_participant)
            min_action = float(exp_a.min()); min_participant = float(exp_p.min())
        rows.append({
            "Feature": feature, "特征": FEATURE_NAMES[feature], "有效N": int((~missing).sum()),
            "缺失N": int(missing.sum()), "缺失率": float(missing.mean()),
            "动作列联P_探索性": action_p, "参与者列联P_探索性": participant_p,
            "动作最小期望频数": min_action, "参与者最小期望频数": min_participant,
            "缺失原因": "现有工作簿未编码逐单元互斥原因；不可推断",
        })
    result = pd.DataFrame(rows)
    mask = result["缺失N"] > 0
    result.loc[mask, "动作列联q_BH"] = bh(result.loc[mask, "动作列联P_探索性"])
    result.loc[mask, "参与者列联q_BH"] = bh(result.loc[mask, "参与者列联P_探索性"])
    return result
