# 代码文件与函数索引 / Source index

依据当前源码静态生成。所有Python文件均解析；列出顶层函数/类及其直接方法。
索引存在不等于该文件在所有参与者上执行通过；执行验证范围见[验证记录](RELEASE_VERIFICATION_20261005.md)。
算法、输入输出、公式、参数和限制见[中文说明](ALGORITHMS_ZH.md)。网页模板和工具配置不算实验算法。

源代码文件：80；Python文件：61。

## [desktop_app/build_a01_demo.py](../desktop_app/build_a01_demo.py)

特定P01/A01/R1本地演示裁剪与信号导出

主要入口/定义：[number](../desktop_app/build_a01_demo.py#L15)、[mapping_row](../desktop_app/build_a01_demo.py#L22)、[imu_signals](../desktop_app/build_a01_demo.py#L30)、[triplet](../desktop_app/build_a01_demo.py#L49)、[kinematic_signals](../desktop_app/build_a01_demo.py#L54)、[build](../desktop_app/build_a01_demo.py#L86)

## [desktop_app/build_desktop_exe.ps1](../desktop_app/build_desktop_exe.ps1)

桌面程序打包脚本

## [desktop_app/player.py](../desktop_app/player.py)

原生桌面视频/曲线同步播放器

主要入口/定义：[SignalPlot](../desktop_app/player.py#L31)、[SignalPlot.__init__](../desktop_app/player.py#L32)、[SignalPlot.set_signal](../desktop_app/player.py#L42)、[SignalPlot.seek](../desktop_app/player.py#L46)、[SignalPlot.render](../desktop_app/player.py#L51)、[Player](../desktop_app/player.py#L79)、[Player.__init__](../desktop_app/player.py#L80)、[Player._layout](../desktop_app/player.py#L99)、[Player.load_demo](../desktop_app/player.py#L154)、[Player.pick_manifest](../desktop_app/player.py#L162)、[Player.pick_videos](../desktop_app/player.py#L168)、[Player.load_manifest](../desktop_app/player.py#L175)、[Player.open_evidence](../desktop_app/player.py#L202)、[Player.nearest](../desktop_app/player.py#L214)、[Player.render_videos](../desktop_app/player.py#L221)、[Player.seek](../desktop_app/player.py#L238)、[Player.toggle](../desktop_app/player.py#L253)、[Player.tick](../desktop_app/player.py#L259)、[Player.pause](../desktop_app/player.py#L266)、[Player.release_captures](../desktop_app/player.py#L272)、[Player.close](../desktop_app/player.py#L276)、[self_test](../desktop_app/player.py#L280)、[main](../desktop_app/player.py#L293)

## [desktop_app/run_a01_demo.ps1](../desktop_app/run_a01_demo.ps1)

启动桌面示例程序

## [legacy_reference/p01/align_P01_visual_IMU.py](../legacy_reference/p01/align_P01_visual_IMU.py)

原P01分支算法参考；逐文件用途见[参考脚本说明](../legacy_reference/README.md)

主要入口/定义：[interpolate_finite](../legacy_reference/p01/align_P01_visual_IMU.py#L68)、[robust_normalize](../legacy_reference/p01/align_P01_visual_IMU.py#L150)、[pearson_correlation](../legacy_reference/p01/align_P01_visual_IMU.py#L197)

## [legacy_reference/p01/build_P01_visual_IMU_joint_inclusion.py](../legacy_reference/p01/build_P01_visual_IMU_joint_inclusion.py)

原P01分支算法参考；逐文件用途见[参考脚本说明](../legacy_reference/README.md)

主要入口/定义：[determine_status](../legacy_reference/p01/build_P01_visual_IMU_joint_inclusion.py#L50)、[determine_reason](../legacy_reference/p01/build_P01_visual_IMU_joint_inclusion.py#L72)

## [legacy_reference/p01/extract_P01_IMU_repetition_metrics.py](../legacy_reference/p01/extract_P01_IMU_repetition_metrics.py)

原P01分支算法参考；逐文件用途见[参考脚本说明](../legacy_reference/README.md)

主要入口/定义：[split_invalid_joints](../legacy_reference/p01/extract_P01_IMU_repetition_metrics.py#L87)、[interpolate_with_gap_limit](../legacy_reference/p01/extract_P01_IMU_repetition_metrics.py#L98)、[filter_valid_blocks](../legacy_reference/p01/extract_P01_IMU_repetition_metrics.py#L187)、[rms](../legacy_reference/p01/extract_P01_IMU_repetition_metrics.py#L249)、[safe_percentile](../legacy_reference/p01/extract_P01_IMU_repetition_metrics.py#L269)、[peak_value_and_time](../legacy_reference/p01/extract_P01_IMU_repetition_metrics.py#L290)、[missing_gap_statistics](../legacy_reference/p01/extract_P01_IMU_repetition_metrics.py#L322)

## [legacy_reference/p01/extract_participant01_metrics.py](../legacy_reference/p01/extract_participant01_metrics.py)

原P01分支算法参考；逐文件用途见[参考脚本说明](../legacy_reference/README.md)

主要入口/定义：[split_invalid_joints](../legacy_reference/p01/extract_participant01_metrics.py#L35)、[marker_columns](../legacy_reference/p01/extract_participant01_metrics.py#L46)、[safe_stat](../legacy_reference/p01/extract_participant01_metrics.py#L54)、[calculate_marker_metrics](../legacy_reference/p01/extract_participant01_metrics.py#L64)、[calculate_angle_series](../legacy_reference/p01/extract_participant01_metrics.py#L165)、[calculate_angle_metrics](../legacy_reference/p01/extract_participant01_metrics.py#L220)、[main](../legacy_reference/p01/extract_participant01_metrics.py#L284)

## [legacy_reference/p01/extract_participant01_metrics_v2.py](../legacy_reference/p01/extract_participant01_metrics_v2.py)

原P01分支算法参考；逐文件用途见[参考脚本说明](../legacy_reference/README.md)

主要入口/定义：[read_trc_safe](../legacy_reference/p01/extract_participant01_metrics_v2.py#L13)、[calculate_marker_metrics](../legacy_reference/p01/extract_participant01_metrics_v2.py#L27)、[calculate_angle_metrics](../legacy_reference/p01/extract_participant01_metrics_v2.py#L151)

## [legacy_reference/p01/legacy_config.py](../legacy_reference/p01/legacy_config.py)

旧脚本显式本地根目录、写入确认及显示窗口配置

主要入口/定义：[load_windows](../legacy_reference/p01/legacy_config.py#L16)

## [legacy_reference/p01/map_P01_visual_repetitions_to_IMU.py](../legacy_reference/p01/map_P01_visual_repetitions_to_IMU.py)

原P01分支算法参考；逐文件用途见[参考脚本说明](../legacy_reference/README.md)

主要入口/定义：[nearest_index](../legacy_reference/p01/map_P01_visual_repetitions_to_IMU.py#L47)

## [legacy_reference/p01/merge_reconstruct_P01_IMU.py](../legacy_reference/p01/merge_reconstruct_P01_IMU.py)

原P01分支算法参考；逐文件用途见[参考脚本说明](../legacy_reference/README.md)

主要入口/定义：[source_part](../legacy_reference/p01/merge_reconstruct_P01_IMU.py#L34)、[reconstruct_timestamp](../legacy_reference/p01/merge_reconstruct_P01_IMU.py#L46)

## [legacy_reference/p01/prepare_P01_IMU_alignment_preview.py](../legacy_reference/p01/prepare_P01_IMU_alignment_preview.py)

原P01分支算法参考；逐文件用途见[参考脚本说明](../legacy_reference/README.md)

主要入口/定义：[gap_aware_interpolate](../legacy_reference/p01/prepare_P01_IMU_alignment_preview.py#L38)、[robust_normalize](../legacy_reference/p01/prepare_P01_IMU_alignment_preview.py#L121)

## [legacy_reference/p01/segment_A10_zoom.py](../legacy_reference/p01/segment_A10_zoom.py)

原P01分支算法参考；逐文件用途见[参考脚本说明](../legacy_reference/README.md)

此文件以顶层流程/包声明为主；参考脚本可能在导入时执行，请勿随意导入。

## [legacy_reference/p01/segment_P01_IMU_trials.py](../legacy_reference/p01/segment_P01_IMU_trials.py)

原P01分支算法参考；逐文件用途见[参考脚本说明](../legacy_reference/README.md)

主要入口/定义：[nearest_index](../legacy_reference/p01/segment_P01_IMU_trials.py#L41)

## [legacy_reference/p01/segment_repetitions.py](../legacy_reference/p01/segment_repetitions.py)

原P01分支算法参考；逐文件用途见[参考脚本说明](../legacy_reference/README.md)

主要入口/定义：[read_trc](../legacy_reference/p01/segment_repetitions.py#L18)、[build_motion_energy](../legacy_reference/p01/segment_repetitions.py#L91)、[main](../legacy_reference/p01/segment_repetitions.py#L159)

## [legacy_reference/p01/summarize_participant01_metrics.py](../legacy_reference/p01/summarize_participant01_metrics.py)

原P01分支算法参考；逐文件用途见[参考脚本说明](../legacy_reference/README.md)

主要入口/定义：[summarize_long](../legacy_reference/p01/summarize_participant01_metrics.py#L38)、[summarize_duration](../legacy_reference/p01/summarize_participant01_metrics.py#L152)、[main](../legacy_reference/p01/summarize_participant01_metrics.py#L195)

## [scripts/audit_validation_tables.py](../scripts/audit_validation_tables.py)

验证表核算命令行入口

主要入口/定义：[main](../scripts/audit_validation_tables.py#L8)

## [scripts/build_blender_scene.py](../scripts/build_blender_scene.py)

将轨迹、场地与相机布置构建为Blender动画

主要入口/定义：[parse_args](../scripts/build_blender_scene.py#L57)、[read_trc](../scripts/build_blender_scene.py#L78)、[read_keypoints_csv](../scripts/build_blender_scene.py#L117)、[material](../scripts/build_blender_scene.py#L169)、[add_box](../scripts/build_blender_scene.py#L185)、[add_sphere](../scripts/build_blender_scene.py#L198)、[animate_location](../scripts/build_blender_scene.py#L210)、[animate_property](../scripts/build_blender_scene.py#L214)、[add_animated_bone](../scripts/build_blender_scene.py#L237)、[add_curve](../scripts/build_blender_scene.py#L263)、[add_text](../scripts/build_blender_scene.py#L278)、[load_control_points](../scripts/build_blender_scene.py#L291)、[parse_calibration](../scripts/build_blender_scene.py#L296)、[rodrigues](../scripts/build_blender_scene.py#L303)、[look_at](../scripts/build_blender_scene.py#L311)、[main](../scripts/build_blender_scene.py#L315)

## [scripts/extract_visual_features.py](../scripts/extract_visual_features.py)

明确TRC时间段的视觉特征提取入口

主要入口/定义：[main](../scripts/extract_visual_features.py#L10)

## [scripts/inventory_legacy.py](../scripts/inventory_legacy.py)

只记录旧源码结构/哈希的清单工具

主要入口/定义：[main](../scripts/inventory_legacy.py#L11)

## [scripts/plot_a10_r10.py](../scripts/plot_a10_r10.py)

公开A10-R10演示绘图

主要入口/定义：[build_figure](../scripts/plot_a10_r10.py#L19)、[main](../scripts/plot_a10_r10.py#L75)

## [scripts/real_data_regression.py](../scripts/real_data_regression.py)

现有本地实验文件的回归审计入口

主要入口/定义：[main](../scripts/real_data_regression.py#L21)

## [scripts/reproduce_study_pca.py](../scripts/reproduce_study_pca.py)

PCA重算与可选二维图输出

主要入口/定义：[main](../scripts/reproduce_study_pca.py#L11)

## [scripts/run_complete_evidence_chain.ps1](../scripts/run_complete_evidence_chain.ps1)

本地阶段计划/可选执行与证据链审计启动器

## [scripts/run_study_analysis.py](../scripts/run_study_analysis.py)

可移植完整统计/嵌套分类入口及输入防护

主要入口/定义：[synthetic_frame](../scripts/run_study_analysis.py#L19)、[validate_frame](../scripts/run_study_analysis.py#L32)、[main](../scripts/run_study_analysis.py#L58)

## [src/badminton_court35/__init__.py](../src/badminton_court35/__init__.py)

Python包初始化/导出约定

此文件以顶层流程/包声明为主；参考脚本可能在导入时执行，请勿随意导入。

## [src/badminton_court35/__main__.py](../src/badminton_court35/__main__.py)

python -m badminton_court35入口

此文件以顶层流程/包声明为主；参考脚本可能在导入时执行，请勿随意导入。

## [src/badminton_court35/alignment/__init__.py](../src/badminton_court35/alignment/__init__.py)

Python包初始化/导出约定

此文件以顶层流程/包声明为主；参考脚本可能在导入时执行，请勿随意导入。

## [src/badminton_court35/alignment/nearest.py](../src/badminton_court35/alignment/nearest.py)

同时间基准上的最近样本映射及表连接

主要入口/定义：[nearest_time_mapping](../src/badminton_court35/alignment/nearest.py#L7)、[merge_visual_imu](../src/badminton_court35/alignment/nearest.py#L56)

## [src/badminton_court35/analysis/__init__.py](../src/badminton_court35/analysis/__init__.py)

Python包初始化/导出约定

此文件以顶层流程/包声明为主；参考脚本可能在导入时执行，请勿随意导入。

## [src/badminton_court35/analysis/aggregation.py](../src/badminton_court35/analysis/aggregation.py)

仅汇总有效重复的分组描述统计

主要入口/定义：[summarize_long](../src/badminton_court35/analysis/aggregation.py#L9)

## [src/badminton_court35/analysis/kinematics.py](../src/badminton_court35/analysis/kinematics.py)

v2相邻有效帧视觉速度、几何角与ROM

主要入口/定义：[split_invalid_joints](../src/badminton_court35/analysis/kinematics.py#L10)、[marker_columns](../src/badminton_court35/analysis/kinematics.py#L21)、[safe_stat](../src/badminton_court35/analysis/kinematics.py#L29)、[calculate_angle_series](../src/badminton_court35/analysis/kinematics.py#L39)、[calculate_marker_metrics](../src/badminton_court35/analysis/kinematics.py#L94)、[calculate_angle_metrics](../src/badminton_court35/analysis/kinematics.py#L218)

## [src/badminton_court35/analysis/paper.py](../src/badminton_court35/analysis/paper.py)

原工作簿与已有预测结果审计，不恢复历史训练模型

主要入口/定义：[binary_roc_auc](../src/badminton_court35/analysis/paper.py#L17)、[multiclass_roc_metrics](../src/badminton_court35/analysis/paper.py#L48)、[cluster_bootstrap_roc](../src/badminton_court35/analysis/paper.py#L67)、[audit_paper_tables](../src/badminton_court35/analysis/paper.py#L110)、[audit_paper_workbook](../src/badminton_court35/analysis/paper.py#L331)

## [src/badminton_court35/analysis/pca_study.py](../src/badminton_court35/analysis/pca_study.py)

论文PCA数值流程：log1p、总体SD、SVD及符号固定

主要入口/定义：[study_pca](../src/badminton_court35/analysis/pca_study.py#L10)

## [src/badminton_court35/analysis/stats.py](../src/badminton_court35/analysis/stats.py)

通用BH、PCA及固定参与者区组模型

主要入口/定义：[benjamini_hochberg](../src/badminton_court35/analysis/stats.py#L8)、[pca_standardized](../src/badminton_court35/analysis/stats.py#L33)、[participant_blocked_action_effects](../src/badminton_court35/analysis/stats.py#L64)

## [src/badminton_court35/analysis/study.py](../src/badminton_court35/analysis/study.py)

23特征固定/混合模型、参与者bootstrap、缺失审计、嵌套LOPO分类

主要入口/定义：[sha256](../src/badminton_court35/analysis/study.py#L48)、[bh](../src/badminton_court35/analysis/study.py#L56)、[design](../src/badminton_court35/analysis/study.py#L66)、[fixed_model](../src/badminton_court35/analysis/study.py#L75)、[within_parts](../src/badminton_court35/analysis/study.py#L126)、[eta_from_parts](../src/badminton_court35/analysis/study.py#L142)、[eta_ci](../src/badminton_court35/analysis/study.py#L152)、[mixed_model](../src/badminton_court35/analysis/study.py#L161)、[softmax](../src/badminton_court35/analysis/study.py#L198)、[fit_multinomial](../src/badminton_court35/analysis/study.py#L204)、[predict_probs](../src/badminton_court35/analysis/study.py#L224)、[standardize_train_test](../src/badminton_court35/analysis/study.py#L229)、[metrics](../src/badminton_court35/analysis/study.py#L236)、[nested_lopo](../src/badminton_court35/analysis/study.py#L257)、[missingness](../src/badminton_court35/analysis/study.py#L316)

## [src/badminton_court35/analysis/validation.py](../src/badminton_court35/analysis/validation.py)

提供的场景坐标/事件时间验证表核算

主要入口/定义：[scene_point_errors](../src/badminton_court35/analysis/validation.py#L6)、[event_timing_errors](../src/badminton_court35/analysis/validation.py#L19)

## [src/badminton_court35/calibration/__init__.py](../src/badminton_court35/calibration/__init__.py)

Python包初始化/导出约定

此文件以顶层流程/包声明为主；参考脚本可能在导入时执行，请勿随意导入。

## [src/badminton_court35/calibration/audit.py](../src/badminton_court35/calibration/audit.py)

相机重投影残差审计

主要入口/定义：[audit_residual_table](../src/badminton_court35/calibration/audit.py#L19)

## [src/badminton_court35/calibration/control_points.py](../src/badminton_court35/calibration/control_points.py)

35点场地几何的生成、读取、哈希与验证

主要入口/定义：[ControlPoint](../src/badminton_court35/calibration/control_points.py#L20)、[ControlPoint.canonical_row](../src/badminton_court35/calibration/control_points.py#L28)、[expected_control_points](../src/badminton_court35/calibration/control_points.py#L35)、[read_control_points](../src/badminton_court35/calibration/control_points.py#L54)、[write_control_points](../src/badminton_court35/calibration/control_points.py#L75)、[control_point_digest](../src/badminton_court35/calibration/control_points.py#L95)、[validate_control_points](../src/badminton_court35/calibration/control_points.py#L100)、[trc_declared_marker_count](../src/badminton_court35/calibration/control_points.py#L162)、[report_json](../src/badminton_court35/calibration/control_points.py#L175)

## [src/badminton_court35/calibration/deployment.py](../src/badminton_court35/calibration/deployment.py)

新场地配置模板与部署记录核对

主要入口/定义：[_write_csv](../src/badminton_court35/calibration/deployment.py#L61)、[_as_bool](../src/badminton_court35/calibration/deployment.py#L69)、[_load_toml](../src/badminton_court35/calibration/deployment.py#L73)、[_site_toml](../src/badminton_court35/calibration/deployment.py#L78)、[_site_readme](../src/badminton_court35/calibration/deployment.py#L107)、[create_site_package](../src/badminton_court35/calibration/deployment.py#L121)、[_read_csv](../src/badminton_court35/calibration/deployment.py#L182)、[_missing_columns](../src/badminton_court35/calibration/deployment.py#L187)、[validate_site_package](../src/badminton_court35/calibration/deployment.py#L191)

## [src/badminton_court35/calibration/resilience.py](../src/badminton_court35/calibration/resilience.py)

控制点缺失和相机覆盖诊断

主要入口/定义：[assess_calibration_resilience](../src/badminton_court35/calibration/resilience.py#L18)

## [src/badminton_court35/cli.py](../src/badminton_court35/cli.py)

court35命令行参数及各模块入口

主要入口/定义：[_json_default](../src/badminton_court35/cli.py#L32)、[_emit](../src/badminton_court35/cli.py#L42)、[_validate_points](../src/badminton_court35/cli.py#L51)、[_export_points](../src/badminton_court35/cli.py#L64)、[_audit_calibration](../src/badminton_court35/cli.py#L70)、[_reconstruct_time](../src/badminton_court35/cli.py#L84)、[_filter_imu](../src/badminton_court35/cli.py#L99)、[_map_nearest](../src/badminton_court35/cli.py#L125)、[_qc_inclusion](../src/badminton_court35/cli.py#L150)、[_pose2sim](../src/badminton_court35/cli.py#L167)、[_audit_paper](../src/badminton_court35/cli.py#L173)、[_demo](../src/badminton_court35/cli.py#L183)、[_export_real_demo](../src/badminton_court35/cli.py#L189)、[_build_dashboard_evidence](../src/badminton_court35/cli.py#L195)、[_build_evidence_chain](../src/badminton_court35/cli.py#L201)、[_scaffold_site](../src/badminton_court35/cli.py#L209)、[_validate_site](../src/badminton_court35/cli.py#L215)、[build_parser](../src/badminton_court35/cli.py#L221)、[main](../src/badminton_court35/cli.py#L348)

## [src/badminton_court35/demo.py](../src/badminton_court35/demo.py)

人工合成非真实记录的软件演示

主要入口/定义：[build_demo](../src/badminton_court35/demo.py#L15)

## [src/badminton_court35/imu/__init__.py](../src/badminton_court35/imu/__init__.py)

Python包初始化/导出约定

此文件以顶层流程/包声明为主；参考脚本可能在导入时执行，请勿随意导入。

## [src/badminton_court35/imu/features.py](../src/badminton_court35/imu/features.py)

原IMU重复算法的插值、滤波、RMS、分位数、峰时、缺口原语

主要入口/定义：[interpolate_with_gap_limit](../src/badminton_court35/imu/features.py#L17)、[filter_valid_blocks](../src/badminton_court35/imu/features.py#L106)、[rms](../src/badminton_court35/imu/features.py#L168)、[safe_percentile](../src/badminton_court35/imu/features.py#L188)、[peak_value_and_time](../src/badminton_court35/imu/features.py#L209)、[missing_gap_statistics](../src/badminton_court35/imu/features.py#L241)

## [src/badminton_court35/imu/filtering.py](../src/badminton_court35/imu/filtering.py)

有限连续区段的IMU低通滤波

主要入口/定义：[_finite_runs](../src/badminton_court35/imu/filtering.py#L7)、[filter_contiguous_segments](../src/badminton_court35/imu/filtering.py#L13)

## [src/badminton_court35/imu/timebase.py](../src/badminton_court35/imu/timebase.py)

批量主机时间戳重建及时间轴审计

主要入口/定义：[reconstruct_timestamp](../src/badminton_court35/imu/timebase.py#L6)、[timebase_audit](../src/badminton_court35/imu/timebase.py#L58)

## [src/badminton_court35/io/__init__.py](../src/badminton_court35/io/__init__.py)

Python包初始化/导出约定

此文件以顶层流程/包声明为主；参考脚本可能在导入时执行，请勿随意导入。

## [src/badminton_court35/io/trc.py](../src/badminton_court35/io/trc.py)

TRC读取和动作分段参考曲线

主要入口/定义：[read_trc](../src/badminton_court35/io/trc.py#L11)、[build_motion_energy](../src/badminton_court35/io/trc.py#L61)

## [src/badminton_court35/pipeline/__init__.py](../src/badminton_court35/pipeline/__init__.py)

Python包初始化/导出约定

此文件以顶层流程/包声明为主；参考脚本可能在导入时执行，请勿随意导入。

## [src/badminton_court35/pipeline/evidence_chain.py](../src/badminton_court35/pipeline/evidence_chain.py)

现有原始到展示链条的文件/日志核对

主要入口/定义：[_hash](../src/badminton_court35/pipeline/evidence_chain.py#L31)、[_identity](../src/badminton_court35/pipeline/evidence_chain.py#L39)、[_stage](../src/badminton_court35/pipeline/evidence_chain.py#L49)、[_mapping](../src/badminton_court35/pipeline/evidence_chain.py#L53)、[_final_sync_offsets](../src/badminton_court35/pipeline/evidence_chain.py#L62)、[_pose_2d](../src/badminton_court35/pipeline/evidence_chain.py#L78)、[_trc_3d](../src/badminton_court35/pipeline/evidence_chain.py#L115)、[_imu_alignment](../src/badminton_court35/pipeline/evidence_chain.py#L137)、[build_evidence_chain](../src/badminton_court35/pipeline/evidence_chain.py#L157)

## [src/badminton_court35/pipeline/pose2sim.py](../src/badminton_court35/pipeline/pose2sim.py)

明确阶段的Pose2Sim外部调用适配器

主要入口/定义：[run_pose2sim](../src/badminton_court35/pipeline/pose2sim.py#L17)

## [src/badminton_court35/qc/__init__.py](../src/badminton_court35/qc/__init__.py)

Python包初始化/导出约定

此文件以顶层流程/包声明为主；参考脚本可能在导入时执行，请勿随意导入。

## [src/badminton_court35/qc/inclusion.py](../src/badminton_court35/qc/inclusion.py)

变量级光学/IMU联合质量门控

主要入口/定义：[_as_bool](../src/badminton_court35/qc/inclusion.py#L7)、[apply_inclusion_rules](../src/badminton_court35/qc/inclusion.py#L18)

## [src/badminton_court35/real_demo.py](../src/badminton_court35/real_demo.py)

指定A10-R10授权演示导出

主要入口/定义：[TrialSelection](../src/badminton_court35/real_demo.py#L32)、[TrialSelection.trial_id](../src/badminton_court35/real_demo.py#L40)、[_hash](../src/badminton_court35/real_demo.py#L44)、[_write_json](../src/badminton_court35/real_demo.py#L52)、[_export_2d](../src/badminton_court35/real_demo.py#L57)、[_export_3d](../src/badminton_court35/real_demo.py#L104)、[_interpolate_gap_limited](../src/badminton_court35/real_demo.py#L134)、[_export_imu](../src/badminton_court35/real_demo.py#L150)、[export_a10_r10](../src/badminton_court35/real_demo.py#L191)

## [src/badminton_court35/visualization/__init__.py](../src/badminton_court35/visualization/__init__.py)

Python包初始化/导出约定

此文件以顶层流程/包声明为主；参考脚本可能在导入时执行，请勿随意导入。

## [src/badminton_court35/visualization/evidence.py](../src/badminton_court35/visualization/evidence.py)

公开演示哈希核验和可视化证据JSON生成

主要入口/定义：[_sha256](../src/badminton_court35/visualization/evidence.py#L25)、[_write_json](../src/badminton_court35/visualization/evidence.py#L33)、[_installed_version](../src/badminton_court35/visualization/evidence.py#L40)、[_verify_locked_checksums](../src/badminton_court35/visualization/evidence.py#L47)、[_locked_result](../src/badminton_court35/visualization/evidence.py#L61)、[build_dashboard_evidence](../src/badminton_court35/visualization/evidence.py#L69)

## [src/badminton_court35/visualization/export.py](../src/badminton_court35/visualization/export.py)

可视化公开字段白名单导出

主要入口/定义：[export_public_dashboard_data](../src/badminton_court35/visualization/export.py#L18)

## [tests/__init__.py](../tests/__init__.py)

Python包初始化/导出约定

此文件以顶层流程/包声明为主；参考脚本可能在导入时执行，请勿随意导入。

## [tests/test_core.py](../tests/test_core.py)

核心库的人工合成与公开示例测试

主要入口/定义：[ControlPointTests](../tests/test_core.py#L38)、[ControlPointTests.test_formal_layout](../tests/test_core.py#L39)、[ControlPointTests.test_round_trip_csv](../tests/test_core.py#L47)、[DeploymentTests](../tests/test_core.py#L53)、[DeploymentTests.test_site_template_requires_local_confirmation](../tests/test_core.py#L54)、[DeploymentTests.test_site_reports_ready_only_after_all_deployment_records](../tests/test_core.py#L64)、[DeploymentTests.test_site_blocks_nonstandard_geometry](../tests/test_core.py#L92)、[TimeAndFilterTests](../tests/test_core.py#L106)、[TimeAndFilterTests.test_batched_time_and_midnight](../tests/test_core.py#L107)、[TimeAndFilterTests.test_filter_preserves_gap](../tests/test_core.py#L114)、[MappingAndQCTests](../tests/test_core.py#L124)、[MappingAndQCTests.test_60_to_50_mapping](../tests/test_core.py#L125)、[MappingAndQCTests.test_variable_specific_qc](../tests/test_core.py#L137)、[AnalysisTests](../tests/test_core.py#L151)、[AnalysisTests.test_participant_blocked_action_effect](../tests/test_core.py#L152)、[AnalysisTests.test_tie_aware_auc_and_multiclass_metrics](../tests/test_core.py#L165)、[AnalysisTests.test_bh_is_monotone_in_rank](../tests/test_core.py#L173)、[AnalysisTests.test_standardized_pca](../tests/test_core.py#L181)、[AuditAndDemoTests](../tests/test_core.py#L190)、[AuditAndDemoTests.test_calibration_resilience_tolerates_small_losses_but_blocks_weak_camera](../tests/test_core.py#L191)、[AuditAndDemoTests.test_public_dashboard_export_excludes_raw_axes](../tests/test_core.py#L212)、[AuditAndDemoTests.test_python_builds_signed_dashboard_evidence](../tests/test_core.py#L244)、[AuditAndDemoTests.test_calibration_audit_and_demo](../tests/test_core.py#L262)

## [tests/test_published_demo.py](../tests/test_published_demo.py)

既有公开A10-R10文件哈希和指标一致性测试

主要入口/定义：[file_hash](../tests/test_published_demo.py#L15)、[PublishedA10R10Tests](../tests/test_published_demo.py#L23)、[PublishedA10R10Tests.test_checksums_and_locked_scope](../tests/test_published_demo.py#L24)、[PublishedA10R10Tests.test_public_imu_metrics_match_published_samples](../tests/test_published_demo.py#L41)

## [tests/test_study_algorithms.py](../tests/test_study_algorithms.py)

新增视觉/IMU/统计/PCA/验证算法的合成测试

主要入口/定义：[synthetic_study](../tests/test_study_algorithms.py#L16)、[KinematicsTests](../tests/test_study_algorithms.py#L23)、[KinematicsTests.test_speed_never_bridges_nan_gap](../tests/test_study_algorithms.py#L24)、[KinematicsTests.test_geometric_angle_and_missing_marker](../tests/test_study_algorithms.py#L32)、[KinematicsTests.test_angle_velocity_never_bridges_gap](../tests/test_study_algorithms.py#L41)、[KinematicsTests.test_repetition_aggregation_excludes_invalid](../tests/test_study_algorithms.py#L45)、[KinematicsTests.test_v2_extraction_is_identical_except_local_safe_stat](../tests/test_study_algorithms.py#L53)、[IMUFeatureTests](../tests/test_study_algorithms.py#L64)、[IMUFeatureTests.test_interpolation_keeps_long_gaps_and_no_extrapolation](../tests/test_study_algorithms.py#L65)、[IMUFeatureTests.test_filter_keeps_gaps_and_returns_too_short_block](../tests/test_study_algorithms.py#L69)、[StatisticalTests](../tests/test_study_algorithms.py#L77)、[StatisticalTests.test_training_only_scaler](../tests/test_study_algorithms.py#L78)、[StatisticalTests.test_fixed_model_agrees_with_independent_existing_implementation](../tests/test_study_algorithms.py#L83)、[StatisticalTests.test_cluster_bootstrap_reproducible](../tests/test_study_algorithms.py#L92)、[StatisticalTests.test_nested_lopo_holds_each_participant_out_once](../tests/test_study_algorithms.py#L103)、[StatisticalTests.test_pca_population_scaling_and_sign](../tests/test_study_algorithms.py#L114)、[ValidationAuditTests](../tests/test_study_algorithms.py#L128)、[ValidationAuditTests.test_scene_units_and_reported_mismatch](../tests/test_study_algorithms.py#L129)、[ValidationAuditTests.test_same_event_offset_not_independent_validation](../tests/test_study_algorithms.py#L138)

## [visualizer/app/chatgpt-auth.ts](../visualizer/app/chatgpt-auth.ts)

既有网站模板身份验证辅助；不是实验算法

## [visualizer/app/Dashboard.tsx](../visualizer/app/Dashboard.tsx)

网页研究仪表板、交互与数据展示

## [visualizer/app/layout.tsx](../visualizer/app/layout.tsx)

网页布局

## [visualizer/app/page.tsx](../visualizer/app/page.tsx)

仪表板页面入口

## [visualizer/db/index.ts](../visualizer/db/index.ts)

既有网站数据库配置/模式，不属于实验算法

## [visualizer/db/schema.ts](../visualizer/db/schema.ts)

既有网站数据库配置/模式，不属于实验算法

## [visualizer/drizzle.config.ts](../visualizer/drizzle.config.ts)

构建/类型/样式/开发工具配置，不属于实验算法

## [visualizer/eslint.config.mjs](../visualizer/eslint.config.mjs)

构建/类型/样式/开发工具配置，不属于实验算法

## [visualizer/examples/d1/app/api/notes/route.ts](../visualizer/examples/d1/app/api/notes/route.ts)

网站模板D1数据库示例，不属于实验算法

## [visualizer/examples/d1/db/schema.ts](../visualizer/examples/d1/db/schema.ts)

网站模板D1数据库示例，不属于实验算法

## [visualizer/next-env.d.ts](../visualizer/next-env.d.ts)

构建/类型/样式/开发工具配置，不属于实验算法

## [visualizer/next.config.ts](../visualizer/next.config.ts)

构建/类型/样式/开发工具配置，不属于实验算法

## [visualizer/postcss.config.mjs](../visualizer/postcss.config.mjs)

构建/类型/样式/开发工具配置，不属于实验算法

## [visualizer/tests/rendered-html.test.mjs](../visualizer/tests/rendered-html.test.mjs)

网页渲染输出测试；本次未重跑

## [visualizer/vite.config.ts](../visualizer/vite.config.ts)

构建/类型/样式/开发工具配置，不属于实验算法

## [visualizer/worker/index.ts](../visualizer/worker/index.ts)

网站Worker路由与图片优化服务入口，不属于实验算法

