"""Synthetic numerical tests only: no private participants or measured records."""
import ast
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from badminton_court35.analysis import study
from badminton_court35.analysis import kinematics
from badminton_court35.analysis.aggregation import summarize_long
from badminton_court35.analysis.pca_study import study_pca
from badminton_court35.analysis.stats import participant_blocked_action_effects
from badminton_court35.analysis.validation import event_timing_errors, scene_point_errors
from badminton_court35.imu.features import interpolate_with_gap_limit, filter_valid_blocks, rms, missing_gap_statistics


def synthetic_study():
    rng=np.random.default_rng(123)
    return pd.DataFrame([{'Participant':f'SYN{p}', 'Action':f'A{a+1:02d}',
                         **{f:float(np.exp(0.1*p+0.04*a+rng.normal(0,.2))) for f in study.FEATURE_NAMES}}
                         for p in range(4) for a in range(10)])


class KinematicsTests(unittest.TestCase):
    def test_speed_never_bridges_nan_gap(self):
        frame=pd.DataFrame({'Time':[0,1,2,3,4], 'RWrist_X':[0,1,np.nan,20,22],
                            'RWrist_Y':[0,0,np.nan,0,0], 'RWrist_Z':[0,0,np.nan,0,0]})
        got=kinematics.calculate_marker_metrics(frame,'RWrist')
        self.assertEqual(got['PathLength_m'],3)
        self.assertEqual(got['MeanSpeed_m_s'],1.5)
        self.assertEqual(got['ValidFraction'],.8)

    def test_geometric_angle_and_missing_marker(self):
        frame=pd.DataFrame({'Time':[0,1,2]})
        for marker,point in {'RHip':(1,0,0),'RKnee':(0,0,0),'RAnkle':(0,1,0)}.items():
            for axis,value in zip('XYZ',point): frame[f'{marker}_{axis}']=value
        t,a=kinematics.calculate_angle_series(frame,'RHip','RKnee','RAnkle')
        np.testing.assert_allclose(a,90)
        self.assertEqual(kinematics.calculate_angle_metrics(t,a)['AngleROM_deg'],0)
        self.assertEqual(kinematics.calculate_marker_metrics(frame,'RWrist')['Status'],'MarkerMissing')

    def test_angle_velocity_never_bridges_gap(self):
        got=kinematics.calculate_angle_metrics(np.arange(5),[0,10,np.nan,100,105])
        self.assertEqual(got['PeakAngularVelocity_deg_s'],10)

    def test_repetition_aggregation_excludes_invalid(self):
        frame=pd.DataFrame({'Action':['A01']*3,'Status':['Valid','Valid','Excluded_Occlusion'],
                            'Repeat':[1,2,3],'x':[1,3,999]})
        row=summarize_long(frame,['Action'],['x']).iloc[0]
        self.assertEqual(row['Mean'],2)
        self.assertEqual(row.ValidRepeats,2)
        self.assertAlmostEqual(row.SD,np.sqrt(2))

    def test_v2_extraction_is_identical_except_local_safe_stat(self):
        root=Path(__file__).resolve().parents[1]
        source=ast.parse((root/'legacy_reference/p01/extract_participant01_metrics_v2.py').read_text(encoding='utf-8'))
        extracted=ast.parse((root/'src/badminton_court35/analysis/kinematics.py').read_text(encoding='utf-8'))
        a={n.name:n for n in source.body if isinstance(n,ast.FunctionDef)}
        b={n.name:n for n in extracted.body if isinstance(n,ast.FunctionDef)}
        for name in ['calculate_marker_metrics','calculate_angle_metrics']:
            rewritten=ast.parse(ast.unparse(a[name]).replace('base.safe_stat(', 'safe_stat(')).body[0]
            self.assertEqual(ast.dump(rewritten),ast.dump(b[name]))


class IMUFeatureTests(unittest.TestCase):
    def test_interpolation_keeps_long_gaps_and_no_extrapolation(self):
        got=interpolate_with_gap_limit([0,.1,.5,.6],[0,1,5,6],[-.1,.05,.3,.55,.7])
        np.testing.assert_allclose(got,[np.nan,.5,np.nan,5.5,np.nan],equal_nan=True)

    def test_filter_keeps_gaps_and_returns_too_short_block(self):
        got=filter_valid_blocks([1,2,3,np.nan,4,5,6])
        np.testing.assert_allclose(got,[1,2,3,np.nan,4,5,6],equal_nan=True)
        self.assertAlmostEqual(rms([3,4,np.nan]),np.sqrt(12.5))
        count,maximum=missing_gap_statistics([True,False,False,True,False])
        self.assertEqual(count,2); self.assertAlmostEqual(maximum,.04)


class StatisticalTests(unittest.TestCase):
    def test_training_only_scaler(self):
        train,test,mean,scale=study.standardize_train_test(np.array([[0.,2.],[2.,2.]]),np.array([[100.,2.]]))
        np.testing.assert_allclose(mean,[1,2]); np.testing.assert_allclose(scale,[1,1])
        self.assertEqual(test[0,0],99)

    def test_fixed_model_agrees_with_independent_existing_implementation(self):
        frame=synthetic_study(); feature=next(iter(study.FEATURE_NAMES))
        got,details=study.fixed_model(frame,feature)
        other=participant_blocked_action_effects(frame,[feature]).iloc[0]
        self.assertAlmostEqual(got['F'],other.F)
        self.assertAlmostEqual(got['P'],other.PValue)
        self.assertAlmostEqual(got['偏η²'],other.PartialEtaSquared)
        self.assertEqual(len(details),40)

    def test_cluster_bootstrap_reproducible(self):
        frame=synthetic_study(); feature=next(iter(study.FEATURE_NAMES))
        original=study.BOOTSTRAPS
        try:
            study.BOOTSTRAPS=10
            a=study.eta_ci(frame,feature,np.random.default_rng(1))
            b=study.eta_ci(frame,feature,np.random.default_rng(1))
            np.testing.assert_array_equal(a,b)
            self.assertTrue(0<=a[0]<=a[1]<=1)
        finally: study.BOOTSTRAPS=original

    def test_nested_lopo_holds_each_participant_out_once(self):
        frame=synthetic_study(); features=[f for f in study.FEATURE_NAMES if 'gyro' in f or 'dynamic_acc' in f]
        predictions,folds,classes,summary=study.nested_lopo(frame,features)
        self.assertEqual(len(predictions),40); self.assertEqual(len(folds),4)
        self.assertTrue((predictions.Participant==predictions.HeldOutParticipant).all())
        self.assertFalse(predictions.duplicated(['Participant','Action']).any())
        self.assertTrue((folds.TrainN==30).all())
        np.testing.assert_allclose(predictions.filter(like='Prob_').sum(axis=1),1,atol=1e-12)
        self.assertEqual(len(classes),10)
        self.assertTrue(0<=summary['macro_f1']<=1)

    def test_pca_population_scaling_and_sign(self):
        frame=synthetic_study(); features=list(study.FEATURE_NAMES)[-12:]
        scores,coeff,info=study_pca(frame,features)
        self.assertEqual(len(scores),40)
        self.assertAlmostEqual(sum(info['explained_percent']),100)
        for col in ['PC1_loading','PC2_loading']:
            values=coeff[col].to_numpy()
            self.assertGreater(values[np.argmax(abs(values))],0)
        x=np.log1p(frame[features].to_numpy()); z=(x-x.mean(0))/x.std(0,ddof=0)
        np.testing.assert_allclose(scores.PC1,z@coeff.PC1_loading,atol=1e-12)
        frame.loc[0,features[0]]=np.nan
        with self.assertRaises(ValueError): study_pca(frame,features)


class ValidationAuditTests(unittest.TestCase):
    def test_scene_units_and_reported_mismatch(self):
        frame=pd.DataFrame({f'True_{a}_m':[0.,0.] for a in 'XYZ'})
        for a,values in {'X':[.03,0.],'Y':[.04,0.],'Z':[0.,.1]}.items(): frame[f'Estimated_{a}_m']=values
        got=scene_point_errors(frame)
        self.assertAlmostEqual(got['mean_cm'],7.5)
        self.assertAlmostEqual(got['max_cm'],10)
        frame['Euclidean_error_cm']=[0,0]
        with self.assertRaises(ValueError): scene_point_errors(frame)

    def test_same_event_offset_not_independent_validation(self):
        frame=pd.DataFrame({'imu_time_s':[1.,2.,3.],'cam3_audio_event_s':[1.1,2.2,3.3]})
        got=event_timing_errors(frame)
        self.assertAlmostEqual(got['offset_ms'],200)
        self.assertAlmostEqual(got['mean_absolute_ms'],200/3)
        self.assertEqual(got['offset_estimation'],'same supplied events')
        fixed=event_timing_errors(frame,fixed_offset_ms=100)
        self.assertAlmostEqual(fixed['mean_absolute_ms'],100)


if __name__=='__main__': unittest.main()
