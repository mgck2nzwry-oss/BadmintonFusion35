"""Run the study's statistical algorithms on an authorized workbook or wide CSV.

No private data are bundled. --synthetic-demo is a software smoke test, not evidence.
See docs/ALGORITHMS_ZH.md for the retained study-specific assumptions and limitations.
"""
from pathlib import Path
import argparse
import importlib.metadata
import json
import sys
import numpy as np
import pandas as pd
from badminton_court35.analysis import study

FEATURES = list(study.FEATURE_NAMES)
IMU_FEATURES = [f for f in FEATURES if 'gyro' in f or 'dynamic_acc' in f]


def synthetic_frame():
    """Deterministic artificial data: no sampled, fitted or copied human records."""
    rng = np.random.default_rng(20261005)
    rows = []
    for person in range(4):
        for action in range(10):
            row = {'Participant': f'SYN{person + 1:02d}', 'Action': f'A{action + 1:02d}'}
            for j, feature in enumerate(FEATURES):
                row[feature] = float(np.exp(0.5 + 0.03 * person + 0.04 * action + 0.02 * j + rng.normal(0, 0.25)))
            rows.append(row)
    return pd.DataFrame(rows)


def validate_frame(frame):
    missing = sorted(set(['Participant', 'Action', *FEATURES]) - set(frame.columns))
    if missing:
        raise ValueError(f'Missing columns: {missing}')
    if frame[['Participant', 'Action']].isna().any().any():
        raise ValueError('Participant and Action cannot be missing')
    if frame.duplicated(['Participant', 'Action']).any():
        raise ValueError('Expected one aggregate row per participant-action; do not treat frames/repeats as independent participants')
    if set(frame.Action.astype(str)) != {f'A{i:02d}' for i in range(1, 11)}:
        raise ValueError('This retained study implementation requires all ten A01-A10 actions (mixed-model df=9)')
    if frame.Participant.nunique() < 3:
        raise ValueError('Nested participant CV requires at least three participants')
    for feature in FEATURES:
        values = pd.to_numeric(frame[feature], errors='raise').to_numpy(float)
        if np.isinf(values).any() or np.any(values[np.isfinite(values)] < 0):
            raise ValueError(f'{feature}: expected nonnegative finite observations or explicit NaN')
        frame[feature] = values
        sub = frame[['Participant', 'Action', feature]].dropna()
        if set(sub.Action.astype(str)) != {f'A{i:02d}' for i in range(1, 11)}:
            raise ValueError(f'{feature}: complete-case subset lacks one of the ten actions; requires a separately reviewed design')
        design = study.design(sub)
        if len(sub) <= np.linalg.matrix_rank(design) or sub.Participant.nunique() < 2:
            raise ValueError(f'{feature}: insufficient residual degrees of freedom or participant clusters')
    return frame


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--input', type=Path, help='Wide .csv or original-schema .xlsx (quality-control retained rows)')
    source.add_argument('--synthetic-demo', action='store_true')
    parser.add_argument('--sheet', default='质量门控数据')
    parser.add_argument('--output', type=Path, required=True, help='New/empty output directory; inputs never modified')
    parser.add_argument('--bootstrap-iterations', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=20260813)
    parser.add_argument('--exclude-participant', action='append', default=[])
    parser.add_argument('--skip-mixed', action='store_true', help='Smoke/partial run only; clearly recorded in manifest')
    parser.add_argument('--skip-classification', action='store_true', help='Partial run only')
    args = parser.parse_args(argv)
    if args.bootstrap_iterations < 1:
        parser.error('bootstrap-iterations must be positive')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Output directory must be new or empty; no implicit overwrite')
    if args.synthetic_demo:
        frame = synthetic_frame(); input_identity = {'kind': 'SYNTHETIC_SOFTWARE_TEST_NOT_PAPER_DATA'}
    else:
        if args.input.suffix.lower() == '.csv':
            frame = pd.read_csv(args.input)
        elif args.input.suffix.lower() == '.xlsx':
            frame = pd.read_excel(args.input, sheet_name=args.sheet)
        else:
            parser.error('Input must be CSV or XLSX')
        input_identity = {'filename': args.input.name, 'sha256': study.sha256(args.input), 'sheet': args.sheet if args.input.suffix.lower() == '.xlsx' else None}
    if args.exclude_participant:
        absent = set(args.exclude_participant) - set(frame.Participant.astype(str))
        if absent:
            raise ValueError(f'Excluded participant(s) not found: {sorted(absent)}')
        frame = frame.loc[~frame.Participant.astype(str).isin(args.exclude_participant)].copy()
    frame = validate_frame(frame)
    if not args.skip_classification:
        classification = frame[['Participant', 'Action', *IMU_FEATURES]].dropna()
        if classification.Participant.nunique() < 3:
            raise ValueError('Classification complete-case subset needs at least three participants')
        for outer in classification.Participant.unique():
            outer_train = classification.loc[classification.Participant != outer]
            for inner in outer_train.Participant.unique():
                inner_train = outer_train.loc[outer_train.Participant != inner]
                if set(inner_train.Action.astype(str)) != {f'A{i:02d}' for i in range(1, 11)}:
                    raise ValueError('An inner training fold lacks a study action; this input requires a separately reviewed classification design')
    args.output.mkdir(parents=True, exist_ok=True)
    def save(table, name):
        table.to_csv(args.output / name, index=False, encoding='utf-8-sig')
    rng = np.random.default_rng(args.seed)
    study.BOOTSTRAPS = args.bootstrap_iterations
    rows, details = [], []
    for feature in FEATURES:
        row, detail = study.fixed_model(frame, feature)
        row['偏η²_CI下限'], row['偏η²_CI上限'] = study.eta_ci(frame, feature, rng)
        if not args.skip_mixed:
            row.update(study.mixed_model(frame, feature))
        rows.append(row); details.append(detail.assign(Feature=feature, 特征=study.FEATURE_NAMES[feature]))
    fixed = pd.DataFrame(rows)
    fixed['FDR_q'] = study.bh(fixed.P.to_numpy())
    fixed['FDR显著'] = fixed.FDR_q <= 0.05
    if not args.skip_mixed:
        fixed['混合模型FDR_q'] = study.bh(fixed['混合模型P'].to_numpy())
        fixed['混合模型FDR显著'] = fixed['混合模型FDR_q'] <= 0.05
    save(fixed, 'S1_complete_model_results.csv')
    save(pd.concat(details, ignore_index=True), 'S2_observation_level_diagnostics.csv')
    save(study.missingness(frame, FEATURES), 'S3_missingness_audit.csv')
    for group_column, filename in [('Action', 'S4_missing_by_action.csv'), ('Participant', 'S5_missing_by_participant.csv')]:
        grouped=[]
        for feature in FEATURES:
            for value, group in frame.assign(_missing=frame[feature].isna()).groupby(group_column):
                grouped.append({'Feature': feature, '特征': study.FEATURE_NAMES[feature], group_column: value, 'MissingN': int(group._missing.sum()), 'TotalN': len(group)})
        save(pd.DataFrame(grouped), filename)
    summary = {'status': 'SKIPPED'}
    if not args.skip_classification:
        pred, outer, per_class, summary = study.nested_lopo(frame, IMU_FEATURES)
        save(pred, 'S6_nested_lopo_predictions.csv')
        save(outer, 'S7_nested_lopo_participant_results.csv')
        save(per_class, 'S8_nested_lopo_per_class.csv')
    manifest = {
        'input': input_identity, 'participants': int(frame.Participant.nunique()), 'participant_action_rows': len(frame),
        'features': FEATURES, 'classification_features': IMU_FEATURES, 'seed': args.seed,
        'bootstrap_iterations': args.bootstrap_iterations, 'excluded_participants': args.exclude_participant,
        'mixed_models_run': not args.skip_mixed, 'nested_lopo': summary,
        'model': 'multinomial logistic regression; L2 grid [0.01,0.1,1,10]; inner mean accuracy; smallest L2 on ties',
        'historical_classifier_recovered': False, 'fixed_model_fdr_significant': int(fixed['FDR显著'].sum()),
        'python': sys.version.split()[0], 'versions': {n: importlib.metadata.version(n) for n in ['numpy','pandas','scipy','statsmodels','openpyxl']},
        'limits': ['Ten-action study-specific implementation, not a general-purpose trained recognizer.',
                   'Mixed-model warnings are retained; convergence is not proof of model validity.',
                   'Missingness association tests are exploratory; reason codes cannot be inferred.',
                   'No hardware validation, new measurements or training-outcome evaluation are performed.'],
        'outputs': {p.name: study.sha256(p) for p in sorted(args.output.glob('*.csv'))},
    }
    (args.output/'run_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'participants':manifest['participants'],'rows':len(frame),'fdr_significant':manifest['fixed_model_fdr_significant'],'nested_lopo':summary},ensure_ascii=False))

if __name__ == '__main__':
    main()
