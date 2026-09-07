"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Point = { device: string; time: number; valid: boolean; dynamicAcceleration: number | null; gyroMagnitude: number | null };
type DeviceMetric = { device: string; location: string; validPercent: number; accRms: number; accPeak: number; gyroRms: number; gyroPeak: number; gyroPeakTime: number; status: string };
type MetricRecord = { action: string; name: string; n: number; median: number; q1: number; q3: number; mean: number };
type PaperMetric = { id: string; label: string; unit: string; records: MetricRecord[] };
type Effect = { feature: string; label: string; family: string; unit: string; n: number; f: number; q: number; eta: number; significant: boolean; effect: string };
type PaperSummary = { actions: Record<string, string>; metrics: PaperMetric[]; effects: Effect[] };
type Audit = { status: string; sections: Record<string, { status: string; [key: string]: unknown }> };
type CalibrationCamera = { camera: string; status: string; visiblePoints: number; robustInliers: number; inlierRatio: number; robustRmsePx: number; pointLossReserve: number; suggestedReview: { pointId: string; residualPx: number }[]; recommendedAction: string };
type CalibrationResilience = { report: { status: string; minimum_robust_inliers: number; minimum_inlier_ratio: number; review_rmse_px: number; automatic_changes_applied: boolean; safe_adaptation: string; accuracy_boundary: string }; cameras: CalibrationCamera[] };
type EvidenceArtifact = { path: string; sha256: string; role: string };
type ResearchEvidence = {
  schemaVersion: string;
  status: string;
  trialId: string;
  calculationAuthority: string;
  architecture: string;
  reproduction: { command: string; entrypoint: string; generatorSha256: string; repository: string };
  environment: Record<string, string>;
  parameters: { visualRateHz: number; imuRateHz: number; mappingMaxErrorMs: number; filter: { type: string; cutoff_hz: number; order: number; bridge_long_gaps: boolean }; qualityControl: Record<string, string | number | boolean>; calibrationGate: { minimumRobustInliers: number; minimumInlierRatio: number; reviewRmsePx: number; automaticChangesApplied: boolean; validationLevel: string } };
  inputs: { path: string; sha256: string; lockedChecksumVerified: boolean | null }[];
  artifacts: EvidenceArtifact[];
  checks: { id: string; status: string }[];
  limitations: string[];
};

const deviceColors: Record<string, string> = {
  WTLhand: "#2364aa",
  WTLknee: "#73a942",
  WTRhand: "#db5a42",
  WTRknee: "#7b5ea7",
};

const locationLabels: Record<string, string> = {
  WTLhand: "左手",
  WTLknee: "左膝",
  WTRhand: "右手",
  WTRknee: "右膝",
};

function useJson<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  useEffect(() => { fetch(url).then((r) => r.json()).then(setData); }, [url]);
  return data;
}

function TimeSeriesChart({ points, devices, signal }: { points: Point[]; devices: string[]; signal: "dynamicAcceleration" | "gyroMagnitude" }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || points.length === 0) return;
    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(ratio, ratio);
    ctx.clearRect(0, 0, width, height);
    const pad = { l: 50, r: 18, t: 16, b: 34 };
    const values = points.filter((p) => devices.includes(p.device) && p.valid && p[signal] !== null).map((p) => p[signal] as number);
    const maxY = Math.max(...values, 1) * 1.08;
    const maxX = Math.max(...points.map((p) => p.time), 1);
    ctx.strokeStyle = "#d9e1e8";
    ctx.lineWidth = 1;
    ctx.fillStyle = "#718096";
    ctx.font = "11px Arial";
    for (let i = 0; i <= 4; i++) {
      const y = pad.t + ((height - pad.t - pad.b) * i) / 4;
      ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(width - pad.r, y); ctx.stroke();
      const value = maxY * (1 - i / 4);
      ctx.fillText(signal === "gyroMagnitude" ? value.toFixed(0) : value.toFixed(1), 8, y + 4);
    }
    for (let i = 0; i <= 4; i++) {
      const x = pad.l + ((width - pad.l - pad.r) * i) / 4;
      ctx.fillText((maxX * i / 4).toFixed(1), x - 8, height - 10);
    }
    for (const device of devices) {
      const series = points.filter((p) => p.device === device && p.valid && p[signal] !== null);
      ctx.strokeStyle = deviceColors[device];
      ctx.lineWidth = device.includes("hand") ? 2.4 : 1.9;
      ctx.beginPath();
      series.forEach((p, index) => {
        const x = pad.l + (p.time / maxX) * (width - pad.l - pad.r);
        const y = pad.t + (1 - (p[signal] as number) / maxY) * (height - pad.t - pad.b);
        if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();
    }
    ctx.fillStyle = "#425466";
    ctx.font = "12px Arial";
    ctx.fillText("相对时间（s）", width / 2 - 32, height - 9);
  }, [points, devices, signal]);
  return <canvas ref={canvasRef} className="signal-canvas" aria-label="A10-R10 IMU时序曲线" />;
}

function ComparisonChart({ metric }: { metric: PaperMetric }) {
  const max = Math.max(...metric.records.map((r) => r.q3), 1) * 1.12;
  return (
    <div className="comparison-chart" role="img" aria-label={`${metric.label}十类动作中位数和四分位距比较`}>
      {metric.records.map((record) => (
        <div className="bar-column" key={record.action}>
          <div className="bar-zone">
            <span className="whisker" style={{ bottom: `${record.q1 / max * 100}%`, height: `${(record.q3 - record.q1) / max * 100}%` }} />
            <span className="bar" style={{ height: `${record.median / max * 100}%` }} />
            <span className="bar-value">{record.median.toFixed(record.median >= 10 ? 1 : 2)}</span>
          </div>
          <b>{record.action}</b>
          <span>{record.name}</span>
          <small>n={record.n}</small>
        </div>
      ))}
    </div>
  );
}

function downloadCsv(rows: Record<string, string | number | boolean>[], filename: string) {
  if (!rows.length) return;
  const headers = Object.keys(rows[0]);
  const csv = [headers.join(","), ...rows.map((row) => headers.map((h) => JSON.stringify(row[h] ?? "")).join(","))].join("\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" }));
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

async function sha256Response(path: string) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  const digest = await crypto.subtle.digest("SHA-256", await response.arrayBuffer());
  return Array.from(new Uint8Array(digest)).map((value) => value.toString(16).padStart(2, "0")).join("");
}

function ReproducibilityPanel({ evidence }: { evidence: ResearchEvidence }) {
  const [verification, setVerification] = useState<Record<string, "checking" | "match" | "mismatch">>({});
  useEffect(() => {
    let active = true;
    setVerification(Object.fromEntries(evidence.artifacts.map((item) => [item.path, "checking"])));
    Promise.all(evidence.artifacts.map(async (artifact) => {
      try {
        const actual = await sha256Response(artifact.path);
        return [artifact.path, actual === artifact.sha256 ? "match" : "mismatch"] as const;
      } catch {
        return [artifact.path, "mismatch"] as const;
      }
    })).then((items) => { if (active) setVerification(Object.fromEntries(items)); });
    return () => { active = false; };
  }, [evidence]);
  const verifiedCount = Object.values(verification).filter((status) => status === "match").length;
  const allVerified = verifiedCount === evidence.artifacts.length;
  const checkLabels: Record<string, string> = {
    "locked-input-checksums": "锁定输入校验和",
    "python-output-recomputed": "Python 结果重算",
    "public-field-allowlist": "公开字段白名单",
    "missing-values-preserved": "缺失值保留",
    "calibration-never-auto-mutates": "标定不自动篡改",
    "classifier-training": "分类器训练复现",
    "centimetre-spatial-accuracy": "厘米级空间验证",
  };
  return (
    <section className="repro-section">
      <div className="section-heading"><div><p>PYTHON-BACKED REPRODUCIBILITY</p><h2>科研计算与可追溯证据</h2></div><div className={`audit-badge ${allVerified ? "" : "checking"}`}>{allVerified ? `在线校验通过 ${verifiedCount}/${evidence.artifacts.length}` : `正在校验 ${verifiedCount}/${evidence.artifacts.length}`}</div></div>
      <div className="compute-contract">
        <article><span>01</span><b>锁定输入</b><p>真实样例、标定残差和参数文件先通过 SHA-256 完整性检查。</p></article>
        <i>→</i><article><span>02</span><b>Python 重算</b><p>BadmintonFusion35 生成派生信号、指标与相机质量诊断。</p></article>
        <i>→</i><article><span>03</span><b>证据清单</b><p>记录环境、参数、入口函数、输入和每个输出的摘要。</p></article>
        <i>→</i><article><span>04</span><b>网页复核</b><p>浏览器重新计算输出摘要；不匹配时显示验证失败。</p></article>
      </div>
      <div className="repro-grid">
        <article className="provenance-card">
          <div className="card-kicker">可执行复现入口</div>
          <h3>{evidence.calculationAuthority}</h3>
          <code>{evidence.reproduction.command}</code>
          <dl><div><dt>Schema</dt><dd>{evidence.schemaVersion}</dd></div><div><dt>入口函数</dt><dd>{evidence.reproduction.entrypoint}</dd></div><div><dt>生成器 SHA-256</dt><dd>{evidence.reproduction.generatorSha256}</dd></div></dl>
          <a href={evidence.reproduction.repository} target="_blank" rel="noreferrer">查看完整 Python 实现与测试 ↗</a>
        </article>
        <article className="environment-card">
          <div className="card-kicker">记录的计算环境</div>
          <div className="environment-list">{Object.entries(evidence.environment).map(([name, value]) => <div key={name}><span>{name}</span><b>{value}</b></div>)}</div>
          <div className="parameter-note"><b>锁定方法</b><span>{evidence.parameters.filter.type}，{evidence.parameters.filter.cutoff_hz} Hz，{evidence.parameters.filter.order} 阶；视觉 {evidence.parameters.visualRateHz} Hz → IMU {evidence.parameters.imuRateHz} Hz；最大映射误差 {evidence.parameters.mappingMaxErrorMs.toFixed(3)} ms。</span></div>
        </article>
      </div>
      <div className="artifact-card">
        <div className="card-kicker">浏览器端实时完整性验证</div>
        <div className="artifact-list">{evidence.artifacts.map((artifact) => <div key={artifact.path}><span className={`verify-dot ${verification[artifact.path] ?? "checking"}`} /><div><b>{artifact.path.replace("/data/", "")}</b><small>{artifact.role === "python_recomputed" ? "由 Python 重算" : "经统计审计的论文导出"}</small></div><code>{artifact.sha256}</code><em>{verification[artifact.path] === "match" ? "一致" : verification[artifact.path] === "mismatch" ? "不一致" : "校验中"}</em></div>)}</div>
      </div>
      <div className="scientific-checks">
        {evidence.checks.map((check) => <article className={check.status === "PASS" ? "pass" : "unverified"} key={check.id}><span>{check.status === "PASS" ? "✓" : "!"}</span><div><b>{checkLabels[check.id] ?? check.id}</b><small>{check.status === "PASS" ? "机器检查通过" : "尚未完成科学验证"}</small></div></article>)}
      </div>
      <div className="repro-boundary"><b>可信性边界</b><div>{evidence.limitations.map((item) => <p key={item}>• {item}</p>)}</div></div>
    </section>
  );
}

export function Dashboard() {
  const points = useJson<Point[]>("/data/a10-r10-timeseries.json") ?? [];
  const deviceMetrics = useJson<DeviceMetric[]>("/data/a10-r10-metrics.json") ?? [];
  const paper = useJson<PaperSummary>("/data/paper-summary.json");
  const audit = useJson<Audit>("/data/audit-summary.json");
  const resilience = useJson<CalibrationResilience>("/data/calibration-resilience.json");
  const researchEvidence = useJson<ResearchEvidence>("/data/research-evidence.json");
  const [tab, setTab] = useState<"trial" | "compare" | "calibration" | "evidence" | "reproducibility">("trial");
  const [devices, setDevices] = useState(["WTLhand", "WTLknee", "WTRhand", "WTRknee"]);
  const [signal, setSignal] = useState<"dynamicAcceleration" | "gyroMagnitude">("gyroMagnitude");
  const [metricId, setMetricId] = useState("rwrist_speed_p95_m_s");
  const [effectFamily, setEffectFamily] = useState("全部");
  const metric = paper?.metrics.find((item) => item.id === metricId) ?? paper?.metrics[0];
  const filteredEffects = useMemo(() => (paper?.effects ?? []).filter((e) => effectFamily === "全部" || e.family === effectFamily).sort((a, b) => b.eta - a.eta), [paper, effectFamily]);

  const toggleDevice = (device: string) => setDevices((current) => current.includes(device) ? current.filter((d) => d !== device) : [...current, device]);

  return (
    <main>
      <header className="topbar">
        <a href="#main-content" className="brand"><span className="brand-mark">35</span><span><b>CourtScope</b><small>羽毛球视觉–IMU研究工具</small></span></a>
        <div className="status-pill"><span /> Python 计算证据 · v0.2</div>
        <a className="github-link" href="https://github.com/mgck2nzwry-oss/BadmintonFusion35" target="_blank" rel="noreferrer">查看源代码 ↗</a>
      </header>

      <section className="hero" id="main-content">
        <div>
          <p className="eyebrow">BADMINTON · FOUR-CAMERA · WEARABLE SENSING</p>
          <h1>从实验数据到<br /><em>可解释的运动证据</em></h1>
          <p className="hero-copy">在同一工作台探索四个肢体传感器、比较十类击球动作，并追溯每个统计结论的质量边界。</p>
        </div>
        <div className="hero-stats">
          <div><strong>4</strong><span>固定机位</span></div>
          <div><strong>35</strong><span>三维控制点</span></div>
          <div><strong>4</strong><span>肢体 IMU</span></div>
          <div><strong>10</strong><span>动作类别</span></div>
        </div>
      </section>

      <nav className="tabs" aria-label="分析模块">
        <button className={tab === "trial" ? "active" : ""} onClick={() => setTab("trial")}><span>01</span> 单试次信号</button>
        <button className={tab === "compare" ? "active" : ""} onClick={() => setTab("compare")}><span>02</span> 动作比较</button>
        <button className={tab === "calibration" ? "active" : ""} onClick={() => setTab("calibration")}><span>03</span> 场地与相机容错</button>
        <button className={tab === "evidence" ? "active" : ""} onClick={() => setTab("evidence")}><span>04</span> 统计证据</button>
        <button className={tab === "reproducibility" ? "active" : ""} onClick={() => setTab("reproducibility")}><span>05</span> Python 可复现性</button>
      </nav>

      {tab === "trial" && (
        <section className="workspace">
          <aside className="control-panel">
            <div className="panel-label">试次选择</div>
            <label>参与者<select disabled><option>公开示例（作者参与者）</option></select></label>
            <label>动作<select disabled><option>A10 · 三方向组合动作</option></select></label>
            <label>重复<select disabled><option>R10</option></select></label>
            <div className="divider" />
            <div className="panel-label">传感器</div>
            <div className="device-list">
              {Object.keys(locationLabels).map((device) => <button key={device} className={devices.includes(device) ? "selected" : ""} onClick={() => toggleDevice(device)}><i style={{ background: deviceColors[device] }} />{locationLabels[device]}<small>{device}</small></button>)}
            </div>
            <button className="export-button" onClick={() => downloadCsv(points.filter((p) => devices.includes(p.device)) as unknown as Record<string, string | number | boolean>[], "Court35_A10-R10_IMU.csv")}>导出当前数据 CSV</button>
          </aside>
          <div className="analysis-panel">
            <div className="section-heading"><div><p>DE-IDENTIFIED REAL TRIAL</p><h2>A10–R10 多传感器时序</h2></div><div className="segmented"><button className={signal === "gyroMagnitude" ? "active" : ""} onClick={() => setSignal("gyroMagnitude")}>角速度模长</button><button className={signal === "dynamicAcceleration" ? "active" : ""} onClick={() => setSignal("dynamicAcceleration")}>动态加速度</button></div></div>
            <div className="chart-card">
              <div className="chart-meta"><span>{signal === "gyroMagnitude" ? "角速度模长（deg/s）" : "动态加速度代理（g）"}</span><small>50 Hz · 四阶零相位 Butterworth · 缺口不跨越</small></div>
              <TimeSeriesChart points={points} devices={devices} signal={signal} />
              <div className="legend">{devices.map((d) => <span key={d}><i style={{ background: deviceColors[d] }} />{locationLabels[d]}</span>)}</div>
            </div>
            <div className="metric-grid">
              {deviceMetrics.map((m) => <article key={m.device}><div className="metric-title"><i style={{ background: deviceColors[m.device] }} /><b>{locationLabels[m.device]}</b><span>{m.validPercent}% 有效</span></div><strong>{signal === "gyroMagnitude" ? m.gyroPeak.toFixed(0) : m.accPeak.toFixed(2)}</strong><small>{signal === "gyroMagnitude" ? "峰值角速度 deg/s" : "峰值动态加速度 g"}</small><div className="mini-row"><span>RMS</span><b>{signal === "gyroMagnitude" ? m.gyroRms.toFixed(1) : m.accRms.toFixed(3)}</b></div></article>)}
            </div>
            <div className="boundary-note"><b>证据边界</b><p>本页展示经参与者同意公开的单一试次派生数据。它用于验证完整处理链，不代表全部 P01–P10 个体分布。</p><span>时序映射最大误差 10 ms · 203 个视觉帧 · 169 个 IMU 样本/设备</span></div>
          </div>
        </section>
      )}

      {tab === "compare" && paper && metric && (
        <section className="compare-section">
          <div className="section-heading"><div><p>P01–P10 AGGREGATED RESULTS</p><h2>十类动作的组水平比较</h2></div><label className="metric-select">指标<select value={metricId} onChange={(e) => setMetricId(e.target.value)}>{paper.metrics.map((m) => <option value={m.id} key={m.id}>{m.label}（{m.unit}）</option>)}</select></label></div>
          <div className="chart-card comparison-card">
            <div className="chart-meta"><span>{metric.label} · 中位数与四分位距</span><small>样本量随视觉/IMU质量门控而变化</small></div>
            <ComparisonChart metric={metric} />
          </div>
          <div className="action-key">{Object.entries(paper.actions).map(([id, name]) => <span key={id}><b>{id}</b>{name}</span>)}</div>
          <div className="interpretation-card"><p>如何读图</p><h3>柱高表示中位数，细线表示 Q1–Q3。</h3><span>这是去标识化的动作级汇总，不展示或推断任何单个参与者的身份、轨迹或原始传感器记录。</span></div>
        </section>
      )}

      {tab === "calibration" && resilience && (
        <section className="calibration-section">
          <div className="section-heading"><div><p>ADAPTIVE CALIBRATION DIAGNOSTICS</p><h2>场地标点与相机微扰容错</h2></div><div className="audit-badge">真实 A10–R10 校准证据 · 需人工复核</div></div>
          <div className="tolerance-summary">
            <div><span>当前总体状态</span><strong>可容错，需复核</strong><small>4/4 相机保留最低稳健点集</small></div>
            <div><span>安全底线</span><strong>≥ {resilience.report.minimum_robust_inliers} 点</strong><small>每台相机稳健内点</small></div>
            <div><span>内点比例</span><strong>≥ {(resilience.report.minimum_inlier_ratio * 100).toFixed(0)}%</strong><small>低于即阻断重建</small></div>
            <div><span>自动改点</span><strong>禁止</strong><small>只诊断，不静默移动标点</small></div>
          </div>
          <div className="camera-grid">
            {resilience.cameras.map((camera) => (
              <article key={camera.camera}>
                <div className="camera-head"><div><span>{camera.camera.toUpperCase()}</span><b>稳健校准</b></div><em>{camera.status === "TOLERANT_WITH_REVIEW" ? "可容错" : camera.status}</em></div>
                <div className="camera-score"><strong>{camera.robustInliers}</strong><span>/ {camera.visiblePoints} 个可见点为稳健内点</span></div>
                <div className="reserve-meter"><span style={{ width: `${Math.min(100, camera.inlierRatio * 100)}%` }} /></div>
                <div className="camera-facts"><span>稳健 RMSE <b>{camera.robustRmsePx.toFixed(2)} px</b></span><span>点损失余量 <b>{camera.pointLossReserve}</b></span></div>
                <div className="review-points"><small>优先复核高残差标点</small><div>{camera.suggestedReview.map((point) => <span key={point.pointId}>{point.pointId}<i>{point.residualPx.toFixed(1)}px</i></span>)}</div></div>
              </article>
            ))}
          </div>
          <div className="adaptation-flow">
            <div><span>1</span><b>测量新场地标点</b><p>每次场地变化建立独立坐标版本，不套用旧坐标。</p></div>
            <i>→</i><div><span>2</span><b>稳健筛选异常点击</b><p>允许少量遮挡或误点，优先检查高残差点。</p></div>
            <i>→</i><div><span>3</span><b>相机逐台质量门控</b><p>内点不足、比例过低或误差过大则阻断。</p></div>
            <i>→</i><div><span>4</span><b>重新标定并留痕</b><p>保留诊断、参数和版本，绝不静默修正。</p></div>
          </div>
          <div className="calibration-boundary"><b>它能应对什么？</b><p>少量标点被遮挡、个别点击偏差、相机轻微位移后的重新标定，以及不同场地的实测坐标版本。</p><b>它不能承诺什么？</b><p>相机明显移动后沿用旧参数、用算法猜测缺失的三维坐标，或仅凭像素残差声称厘米级空间精度。</p></div>
        </section>
      )}

      {tab === "evidence" && paper && audit && (
        <section className="evidence-section">
          <div className="section-heading"><div><p>MACHINE-AUDITED PAPER EVIDENCE</p><h2>统计效应与可复现性边界</h2></div><div className="audit-badge">{audit.status === "PASS_WITH_LIMITATION" ? "通过，含一项限制" : audit.status}</div></div>
          <div className="audit-strip">
            <article><span>动作单元</span><strong>87</strong><small>质量门控后</small></article>
            <article><span>显著指标</span><strong>19/23</strong><small>FDR q&lt;0.05</small></article>
            <article><span>PC1 + PC2</span><strong>63.6%</strong><small>解释方差</small></article>
            <article><span>宏平均 AUC</span><strong>0.816</strong><small>LOPO, 95% CI 0.760–0.877</small></article>
          </div>
          <div className="evidence-toolbar"><div>{["全部", "视觉", "IMU"].map((f) => <button className={effectFamily === f ? "active" : ""} key={f} onClick={() => setEffectFamily(f)}>{f}</button>)}</div><button onClick={() => downloadCsv(filteredEffects as unknown as Record<string, string | number | boolean>[], "Court35_effects.csv")}>下载效应表</button></div>
          <div className="effect-list">
            {filteredEffects.map((e, index) => <article key={e.feature}><span className="rank">{String(index + 1).padStart(2, "0")}</span><div className="effect-name"><b>{e.label}</b><small>{e.family} · n={e.n} · {e.unit}</small></div><div className="effect-bar"><span style={{ width: `${Math.min(100, e.eta * 100)}%` }} /></div><strong>η²p {e.eta.toFixed(3)}</strong><span className={e.significant ? "sig" : "not-sig"}>{e.significant ? "FDR 显著" : "未显著"}</span></article>)}
          </div>
          <div className="limitations">
            <article><span>✓</span><div><b>已验证</b><p>PCA、FDR、敏感性分析、OOF 概率、ROC 曲线与参与者聚类 bootstrap 置信区间均可机器复算。</p></div></article>
            <article className="warning"><span>!</span><div><b>仍有限制</b><p>工作簿未记录分类器类型、超参数和训练实现，因此只能审计预测结果，不能声称模型训练端完全可复现。</p></div></article>
          </div>
        </section>
      )}

      {tab === "reproducibility" && researchEvidence && <ReproducibilityPanel evidence={researchEvidence} />}

      <footer><div><b>CourtScope</b><span>由 BadmintonFusion35 可复现计算包驱动</span></div><p>研究工具，不用于临床诊断或未经验证的运动表现判定。</p></footer>
    </main>
  );
}
