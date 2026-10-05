# 实验算法代码说明

本说明对应2026-10-05算法代码整理。研究对象是四相机与四个肢体IMU记录的羽毛球训练动作。
本次新增内容为**代码、说明、来源记录和人工合成测试**，不包含新上传的参与者原始视频、传感器记录、完整工作簿或逐人分析结果。仓库此前已经公开的有限演示文件保持原样。

## 1. 先区分三类代码

1. `src/badminton_court35/`：可复用函数库；`scripts/`：明确输入输出的运行入口。
2. `legacy_reference/p01/`：原始P01分支的参考脚本。保留算法逻辑，替换本机绝对路径，外置记录特定的显示窗口。它们用于追溯，不代表P01–P10均执行过完全相同的版本。
3. `desktop_app/`、`visualizer/`、Blender脚本：结果查看和演示工具，不是额外的测量验证，也不改变统计分析的独立样本数。

文件及函数定位见[代码索引](CODE_INDEX.md)；历史脚本的依赖、风险与使用顺序见[参考脚本说明](../legacy_reference/README.md)。

## 2. 数据处理链及各部分用途

以下库文件路径均相对于 `src/badminton_court35/`。

| 部分 | 代码 | 输入 → 输出 | 作用及边界 |
|---|---|---|---|
| 场地控制点 | `calibration/control_points.py` | 控制点CSV/TRC → 坐标与顺序核对报告 | 生成/检查35点布局，25地面点和10高程点；不是人体关节精度标定 |
| 相机残差审计 | `calibration/audit.py` | 已有重投影残差表 → 各相机摘要 | 区分全部点与稳健内点的像素残差，不能直接换算成厘米精度 |
| 标定点缺失诊断 | `calibration/resilience.py` | 残差/可见点表 → 审查提示 | 检查点丢失、较大残差与可见性，不自动修复相机或宣称达到精度 |
| 新场地部署 | `calibration/deployment.py` | 场地配置和检查记录 → 模板/核对报告 | 要求新场地的实际标定、覆盖与同步记录；不是复制原场地参数即完成迁移 |
| 上游视觉流程 | `pipeline/pose2sim.py` | Pose2Sim配置及阶段列表 → 执行计划或结果状态 | 调用上游标定、姿态估计、同步、人物关联、三角化、滤波；默认只预演，执行须明确启用 |
| TRC读取 | `io/trc.py` | TRC → Frame、Time与各关键点XYZ | 保留缺失，重复列名加后缀；运动强度曲线用于分段参考，不写回轨迹 |
| 人工动作分段 | `legacy_reference/p01/segment_repetitions.py`等 | 运动强度曲线与人工点击 → 重复起止时刻 | 不是自动识别模型；原流程需人工边界与质量判断 |
| IMU时间重建 | `imu/timebase.py` | 批量/重复主机时间戳 → 逐样本时间轴与审计 | 重建采样时序；不能等同于硬件同步证据 |
| 跨模态对齐 | 参考脚本`align_P01_visual_IMU.py` | 视觉强度、IMU预览、人工动作窗口 → 时间缩放/偏移 | 搜索时间尺度与偏移，比较相关性；依赖已选动作窗口 |
| 最近样本映射 | `alignment/nearest.py` | 已在同一时间基准的两组时间 → 索引及时间差 | 把视觉时刻映射到最近IMU样本；它本身不估计跨设备时钟偏移 |
| IMU滤波 | `imu/filtering.py`、`imu/features.py` | 各轴序列 → 分段低通结果 | 默认50 Hz、四阶10 Hz零相位Butterworth，不跨长缺口滤波；过短区段可能原样返回 |
| 视觉特征 | `analysis/kinematics.py` | 一段Time+关键点XYZ → 轨迹、速度、几何角、ROM | 采用v2相邻有效帧计算，不跨NaN缺口求速度或角速度 |
| IMU重复特征 | `imu/features.py`及参考脚本`extract_P01_IMU_repetition_metrics.py` | 四设备各轴序列、重复时间映射 → RMS、峰值、P95、积分等 | 参照原采样和滤波参数；视觉遮挡不删除IMU本身，只影响对应联合比较资格 |
| 质量门控 | `qc/inclusion.py` | 光学资格、IMU有效率 → 主分析/敏感性/排除标记 | 默认≥95%主分析、90%至不足95%仅敏感性、<90%排除；光学不合格排除对应联合比较 |
| 重复汇总 | `analysis/aggregation.py` | 标有Status的重复级表 → 分组描述统计 | 只汇总`Valid`记录；不把重复或帧当作独立参与者 |
| 通用统计组件 | `analysis/stats.py` | 特征表/p值 → PCA、FDR、固定区组效应 | 通用PCA用样本SD，`ddof=1`；论文图专用版本另见下文 |
| 完整统计实现 | `analysis/study.py` | 已经完成质量门控的参与者–动作宽表 → 模型/诊断/嵌套预测 | 23特征固定区组模型、参与者bootstrap、混合模型敏感性、缺失审计、12特征分类 |
| 论文PCA | `analysis/pca_study.py` | 12个IMU特征 → 得分、系数、解释率 | `ln(1+x)`、总体SD标准化、SVD，确定性符号方向；只作描述性分析 |
| 旧结果审计 | `analysis/paper.py` | 工作簿及已有预测概率 → PCA/FDR/ROC及CI审计 | 计算已有预测的性能，不代表找回原来的训练程序 |
| 验证表核算 | `analysis/validation.py` | 场景点坐标/配对事件时间 → 误差摘要 | 核算已有表；不生成新验证事件、不证明关节精度或留出独立性 |
| 演示导出 | `real_demo.py`、`visualization/export.py` | 经授权的指定示例/派生摘要 → 演示文件 | 有字段白名单，但白名单不替代研究伦理和公开授权 |
| 证据与溯源 | `visualization/evidence.py`、`pipeline/evidence_chain.py` | 现有输入、日志及哈希 → 分阶段报告 | 核对链条，不等于从头重跑所有姿态模型或验证所有论文结论 |

## 3. 特征的具体计算含义

### 视觉

- XYZ单位要求为米，Time为秒。速度为相邻有效点欧氏距离除以时间差，报告均值、峰值和P95。路径长度只累加相邻有效段；起终点位移是首末有效点的直线距离，两者不要混淆。
- 关节几何角使用近端–中心与远端–中心向量的夹角，余弦截断到[-1,1]后转为度。ROM为有效角度最大值减最小值，不是经肌骨模型校准的关节坐标角。
- 角速度取相邻有效帧角度差除以时间差的绝对值。NaN两侧不连接求导。
- `extract_visual_features.py`不自动读入遮挡注释，输出数值不代表已经通过论文的全部质量门控。

### IMU

- 原参考流程先按50 Hz重采样，各轴分别处理；相同时间点取均值，超过0.12 s的缺口不插值，区间外不外推。
- 有效连续段使用四阶10 Hz零相位Butterworth。短于15样本或滤波器长度条件不满足的区段保留原值；因此不能写成“所有样本都完成低通滤波”。
- 角速度合量为三轴欧氏范数，RMS为有效样本平方均值的平方根。
- 动态加速度代理量为 `abs(norm(a_g) - 1)`。它不是经过姿态解算和重力补偿的世界坐标线性加速度。
- 积分是有效值求和乘采样间隔；角速度合量积分表示活动量，不是某个解剖关节的净旋转角。动态加速度代理量相邻差分形成jerk代理量。
- 原重复脚本还输出有效率、缺口数、最大缺口、峰时、映射状态和联合比较资格。

### 23列工作簿

特征名称与顺序由`analysis/study.py::FEATURE_NAMES`规定：11项视觉特征、12项IMU特征，包括原宽表中的左右侧差异指标。**本次没有凭名称推测不对称指数的公式，也没有把重复表到完整23列宽表的组装过程伪装成已经恢复。**该组装程序的完整执行来源尚未确认；统计入口读取已经核对的宽表，不悄悄重建或修改这些列。

## 4. 统计算法与防止数据泄漏

- 分析单位是参与者–动作汇总记录；先做`ln(1+x)`，以动作和参与者作为固定效应。动作效应来自完整模型与仅含参与者的约简模型比较。
- 23项动作效应p值用Benjamini–Hochberg校正；输出F、p、偏η²、残差、杠杆和Cook距离等。
- 偏η²置信区间在参与者层级有放回抽样，不在帧层级抽样；默认2000次，随机种子20260813。
- 参与者随机截距模型是敏感性分析，使用最大似然拟合；原实现先尝试`lbfgs`，再尝试`powell`，保留奇异/边界等警告。动作检验自由度固定为9，所以运行入口要求A01–A10完整设计。
- 缺失审计报告每个特征及动作/参与者分组的缺失情况。列联检验是探索性的，保留最小期望频数；没有逐单元原因记录时不得推断排除原因。
- 分类只使用12项IMU特征。外层留一参与者评估，内层仅在外层训练参与者中再次留一参与者，选择L2参数`[0.01, 0.1, 1, 10]`。以平均内层准确率选择，并列取较小L2。
- 多项逻辑回归使用softmax交叉熵总和，加`0.5 × L2 × 权重平方和`，不惩罚截距。它不直接等于某个软件库的`C`参数。
- 标准化均值和总体SD只在当前训练折估计；验证/测试折不参与。没有全数据特征选择。最终返回逐记录外层预测、各外层折结果及各类精确率/召回率/F1。
- 这套已明确实现的嵌套分类是后续可复算分析，**不是未归档历史分类器的源码恢复**，不得混用两套性能结果。

## 5. 安装与运行

在仓库根目录，使用Python 3.11或更高版本。不会自动下载或上传参与者数据。

```powershell
python -m pip install -e ".[study]"
python -m unittest discover -s tests -v

# 不含真实记录的快速软件自测；跳过混合模型，因此不是论文完整分析
python scripts/run_study_analysis.py --synthetic-demo --bootstrap-iterations 5 --skip-mixed --output outputs/synthetic-study

# 完整统计；路径替换为自己有权使用的本地文件
python scripts/run_study_analysis.py --input "<local-authorized-workbook.xlsx>" --output outputs/study

# 同样支持宽表CSV；排除参与者需明确记录，不能静默删除
python scripts/run_study_analysis.py --input "<local-wide-table.csv>" --exclude-participant P10 --output outputs/sensitivity

# PCA可读取同一宽表，也可读取统计入口输出的S2诊断长表
python scripts/reproduce_study_pca.py --input outputs/study/S2_observation_level_diagnostics.csv --output outputs/pca --plot

# 单段视觉特征；时间和单位必须与本地TRC一致
python scripts/extract_visual_features.py --trc "<local-trial.trc>" --start 1.0 --end 2.0 --output outputs/segment.json

# 核算已有验证表；没有这些表时不要填造数据
python scripts/audit_validation_tables.py --scene "<local-scene.csv>" --events "<local-event-pairs.csv>" --output outputs/validation.json
```

新统计入口要求输出目录为空或不存在，避免覆盖旧分析。`--skip-mixed`或`--skip-classification`只用于部分运行，清单中会记录。混合模型拟合失败会报错，不自动伪造缺失结果。

### 输入/输出约定

- 宽表：`Participant`、`Action`及`FEATURE_NAMES`中23列；每个参与者–动作只能一行。XLSX默认工作表名为`质量门控数据`。此入口不读取原视频，也不替代前置质量门控。
- 统计输出：S1模型结果；S2逐记录诊断；S3特征缺失；S4按动作缺失；S5按参与者缺失；S6嵌套预测；S7参与者折结果；S8各类指标；`run_manifest.json`记录输入哈希、参数、版本、输出哈希及运行范围。
- PCA输出：`scores.csv`、`coefficients.csv`、`manifest.json`，可选PNG/PDF。使用`ddof=0`；与通用`stats.py`的`ddof=1`相比，解释率不受这一整体缩放影响，但得分尺度不同，不能把得分混用。可移植绘图布局不声称逐像素复刻原图。
- 场景表：`True_X_m/Y_m/Z_m`和`Estimated_X_m/Y_m/Z_m`；如存在`Euclidean_error_cm`则核对一致性。
- 事件表：`cam3_audio_event_s`和`imu_time_s`，可选原始差值与校正残差列。默认在同一批事件上估计平均常量偏移，再算残差；这不是独立留出验证。`--fixed-offset-ms`允许使用外部给定偏移，但仍需另行提供其来源。

**S2、S6、PCA得分等输出可能包含逐人派生信息，只应留在授权本地目录；不要因它们由公开代码生成就直接上传。**`outputs/`已被忽略，但忽略规则不能替代人工检查。

## 6. 显示、历史与可复现边界

桌面播放器使用Python界面、OpenCV和Pillow；视频裁剪/编码流程还依赖可用的ffmpeg。其现有示例构建器锁定P01/A01/R1和特定相机偏移，不是任意参与者的自动播放器构建器。Blender脚本需要Blender的Python环境，把轨迹映射为动画场景，不进行肌骨仿真。网页目录是另一个展示前端；本次未重新部署网站。

本次没有重跑全量视频姿态估计、所有相机标定、GUI人工点击、所有参与者的个别修复或Blender渲染。已验证范围见[验证记录](RELEASE_VERIFICATION_20261005.md)。

尚未恢复/不能据此证明的部分：历史分类器及其训练参数；完整23列宽表组装脚本的执行链；每位参与者最终采用的修复脚本，特别是存在多个候选的个别动作；人体关节/速度的独立测量效度；训练效果及广泛泛化能力。公开代码不消除这些科学证据上的限制。

Pose2Sim等上游库通过依赖调用，不冒充本项目原创算法，也不随本次发布打包第三方模型权重。代码沿用仓库既有许可证；代码许可不自动授权任何参与者数据的公开或再利用。
