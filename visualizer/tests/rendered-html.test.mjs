import assert from "node:assert/strict";
import test from "node:test";

test("dashboard source exposes the three evidence layers", async () => {
  const source = await import("node:fs/promises").then((fs) => fs.readFile(new URL("../app/Dashboard.tsx", import.meta.url), "utf8"));
  assert.match(source, /单试次信号/);
  assert.match(source, /动作比较/);
  assert.match(source, /统计证据/);
  assert.match(source, /场地与相机容错/);
  assert.match(source, /证据边界/);
});

test("public dashboard data excludes forbidden private fields", async () => {
  const fs = await import("node:fs/promises");
  const data = await fs.readFile(new URL("../public/data/a10-r10-timeseries.json", import.meta.url), "utf8");
  assert.doesNotMatch(data, /Participant|private_path|source_sha256|acc_x_g|gyro_x_deg_s/);
});

test("calibration diagnostics expose review guidance without automatic mutation", async () => {
  const fs = await import("node:fs/promises");
  const raw = await fs.readFile(new URL("../public/data/calibration-resilience.json", import.meta.url), "utf8");
  const calibration = JSON.parse(raw);
  assert.equal(calibration.report.automatic_changes_applied, false);
  assert.equal(calibration.cameras.length, 4);
  assert.ok(calibration.cameras.every((camera) => camera.pointLossReserve >= 0));
});
