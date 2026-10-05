# 原始算法参考脚本 / Legacy algorithm references

这些是原P01脚本分支的代码参考，不是实验数据，也不是声称所有参与者都使用同一分支。
来源SHA-256和编辑范围见[feature_algorithm_provenance.json](../docs/feature_algorithm_provenance.json)。

仅改动：本机固定根目录改为显式配置；会写入本地项目的脚本要求明确启用；两份脚本中的特定实验显示窗口外置。函数计算逻辑保留。没有附带人工点击结果、原始传感器数据、完整TRC或视频。

## 脚本顺序及输入输出

路径相对于`p01/`；运行目录结构仍是原P01约定。

| 文件 | 做什么 | 输入 → 输出 |
|---|---|---|
| `segment_repetitions.py` | TRC运动强度参考曲线，人工点击10次动作起终点 | 各Axx滤波TRC → 重复分段CSV |
| `segment_A10_zoom.py` | A10逐段放大选点辅助 | TRC+本地显示窗口 → 更新A10分段 |
| `extract_participant01_metrics.py` | 原视觉轨迹/角度提取基础版 | 分段+TRC+无效关节注释 → 标记点/关节特征表 |
| `extract_participant01_metrics_v2.py` | 替换基础版读取与求导后运行其main | 同上；去重复列，不跨NaN缺口计算速度/角速度 |
| `summarize_participant01_metrics.py` | 有效重复的分组描述统计 | 重复特征表 → 均值、SD、中位数、IQR、范围、CV |
| `merge_reconstruct_P01_IMU.py` | 合并已清洗的设备文件并重建批量时间戳 | P01_IMU_Cleaned → P01_IMU_Merged及摘要 |
| `prepare_P01_IMU_alignment_preview.py` | 50Hz预览、短缺口插值、运动强度构建 | 合并IMU → 对齐预览CSV/图 |
| `segment_P01_IMU_trials.py` | 人工选取A01–A10的IMU窗口 | 预览+本地显示窗口 → 动作窗口CSV |
| `align_P01_visual_IMU.py` | 搜索视觉–IMU时间缩放/偏移和相关性 | TRC、预览、两类分段 → 对齐摘要/审查图 |
| `map_P01_visual_repetitions_to_IMU.py` | 根据对齐关系映射每次动作到50Hz网格 | 分段+对齐摘要 → 重复映射及审计表 |
| `extract_P01_IMU_repetition_metrics.py` | 重采样、分段滤波、RMS/峰值/P95/积分/jerk和质量输出 | 四个设备合并表+100次重复映射 → 各设备重复指标与审计 |
| `build_P01_visual_IMU_joint_inclusion.py` | 原分支的光学/IMU联合纳入标记 | IMU重复指标 → 主分析、敏感性或排除表 |
| `legacy_config.py` | 安全配置入口，不包含科学算法 | 环境变量+可选窗口JSON → 明确的本地目录配置 |

## 重要限制

- **不要直接运行在唯一一份原始项目上。**部分脚本在导入时就读取/写入文件，可能覆盖派生CSV及图片。请使用项目副本；本次发布没有运行这些遗留脚本。
- 基础版视觉求导会先筛除缺失值，可能跨缺口；保留它是因为v2依赖其中其他函数。实际复用优先选`analysis/kinematics.py`的v2实现，不单独把旧基础版当作推荐版本。
- 旧联合纳入脚本对缺失或非法有效率的处理不足；生产使用优先采用`qc/inclusion.py`并核对输入。参考脚本保留历史，不静默修写历史算法。
- 原始对齐不是单纯最近样本映射：包含50Hz网格、时间尺度0.985至1.015（步长0.0025）及0.02秒步长的窗口搜索，比较运动曲线相关性。自动评分仍需审查，不能证明时间精度。
- P01文件名、4设备标识、10动作及100次重复等断言仍保留。脚本不是跨参与者通用批处理器；不是读取任意CSV就能重建论文。
- 特定实验的人工选点、显示窗口、个别动作修补记录未随代码发布。参考脚本存在并不证明其是某位参与者最后一次执行的版本。

## 手工复核后运行（可选）

```powershell
# 使用自己有权处理的项目副本；先确认不会覆盖唯一结果
$env:BADMINTON_LEGACY_ROOT = "<authorized-project-copy>"
$env:BADMINTON_LEGACY_ALLOW_WRITE = "YES"
python legacy_reference/p01/segment_repetitions.py A01

# 两个窗口辅助脚本还需要本人记录对应的显示窗口
$env:BADMINTON_LEGACY_WINDOWS = "<local-window-config.json>"
```

窗口JSON键为`a10_zoom_windows`与`imu_trial_windows`，各自含10个`[start_seconds,end_seconds]`区间；它们只是显示范围，最终边界仍由人工点击。不要用虚构窗口代替实验记录。

English summary: these are P01-lineage reference programs, not a universal or fully verified participant pipeline. Local paths and recorded display windows are externalized. An explicit write opt-in is mandatory. Do not import/run them on your only project copy. Prefer the tested library functions for new use. No private observations are distributed.
