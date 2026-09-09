"""BadmintonFusion35 local desktop synchronised video and data player."""

from __future__ import annotations

from argparse import ArgumentParser
from bisect import bisect_left
import json
import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from build_a01_demo import build

APP_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


SIGNALS = (
    ("rightHandGyro", "Right-hand gyroscope", "deg/s", "#20b6b2"),
    ("rightKneeGyro", "Right-knee gyroscope", "deg/s", "#8b5cf6"),
    ("combinedImuEnergy", "Combined IMU energy", "a.u.", "#ec4899"),
    ("rightWristSpeed", "Right-wrist speed", "m/s", "#3f8cff"),
    ("rightKneeAngle", "Right-knee angle", "degrees", "#f59e0b"),
)


class SignalPlot(tk.Canvas):
    def __init__(self, parent, on_seek, **kwargs):
        super().__init__(parent, background="#111827", highlightthickness=0, **kwargs)
        self.samples: list[dict] = []
        self.duration = 1.0
        self.current = 0.0
        self.color, self.title, self.unit = "#20b6b2", "Signal", ""
        self.on_seek = on_seek
        self.bind("<Configure>", lambda event: self.render())
        self.bind("<Button-1>", self.seek)

    def set_signal(self, samples, duration, title, unit, color):
        self.samples, self.duration, self.title, self.unit, self.color = samples, max(duration, .01), title, unit, color
        self.render()

    def seek(self, event):
        width = max(self.winfo_width() - 58, 1)
        time = min(self.duration, max(0.0, (event.x - 42) / width * self.duration))
        self.on_seek(time)

    def render(self):
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        if width < 100 or height < 30:
            return
        left, right, top, bottom = 42, 16, 19, 16
        values = [float(p["value"]) for p in self.samples] or [0.0]
        low, high = min(values), max(values)
        pad = max((high-low)*.12, 1.0)
        low, high = low-pad, high+pad
        self.create_text(left, 11, text=f"{self.title} ({self.unit})", fill="#e5e7eb", anchor="w", font=("Segoe UI", 10, "bold"))
        for i in range(3):
            y = top + i*(height-top-bottom)/2
            value = high - i*(high-low)/2
            self.create_line(left, y, width-right, y, fill="#263244")
            self.create_text(left-4, y, text=f"{value:.0f}", fill="#94a3b8", anchor="e", font=("Segoe UI", 8))
        points = []
        for point in self.samples:
            x = left + float(point["time"])/self.duration*(width-left-right)
            y = top + (high-float(point["value"]))/(high-low)*(height-top-bottom)
            points.extend((x, y))
        if len(points) >= 4:
            self.create_line(*points, fill=self.color, width=2, smooth=True)
        cursor = left + self.current/self.duration*(width-left-right)
        self.create_line(cursor, top, cursor, height-bottom, fill="#f8fafc", width=1)
        self.create_text(cursor+4, height-bottom+11, text=f"{self.current:.2f}s", fill="#dbeafe", anchor="w", font=("Segoe UI", 8))


class Player(tk.Tk):
    def __init__(self, manifest: Path):
        super().__init__()
        self.title("BadmintonFusion35 Desktop Player")
        self.geometry("1540x980")
        self.minsize(1100, 720)
        self.configure(background="#0b1220")
        self.manifest_path: Path | None = None
        self.video_folder_override: Path | None = None
        self.payload: dict = {}
        self.captures: dict[str, cv2.VideoCapture] = {}
        self.photos: dict[str, ImageTk.PhotoImage] = {}
        self.current, self.playing, self.after_id = 0.0, False, None
        self.duration, self.fps = 1.0, 60.0
        self.setting_scale = False
        self.metric_vars = {name: tk.StringVar(value="--") for name, _, _, _ in SIGNALS}
        self._layout()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.load_manifest(manifest)

    def _layout(self):
        toolbar = tk.Frame(self, background="#101a2d", padx=12, pady=9)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Load A01 demo", command=self.load_demo).pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="Open data JSON", command=self.pick_manifest).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Open video folder", command=self.pick_videos).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Evidence report", command=self.open_evidence).pack(side="left", padx=4)
        self.status = tk.StringVar(value="Preparing local trial…")
        tk.Label(toolbar, textvariable=self.status, background="#101a2d", foreground="#cbd5e1", font=("Segoe UI", 10)).pack(side="right")
        body = tk.PanedWindow(self, orient="vertical", sashwidth=5, background="#0b1220", bd=0)
        body.pack(fill="both", expand=True, padx=10, pady=(8, 5))
        video_area = tk.Frame(body, background="#0b1220")
        body.add(video_area, stretch="always")
        self.video_labels = {}
        for index, camera in enumerate(("cam01", "cam02", "cam03", "cam04")):
            panel = tk.Frame(video_area, background="#111827", highlightbackground="#263244", highlightthickness=1)
            panel.grid(row=index//2, column=index%2, sticky="nsew", padx=4, pady=4)
            video_area.grid_rowconfigure(index//2, weight=1)
            video_area.grid_columnconfigure(index%2, weight=1)
            tk.Label(panel, text=f"{camera.upper()} · 2D Skeleton", background="#111827", foreground="#cbd5e1", anchor="w", padx=8, pady=4, font=("Segoe UI", 10, "bold")).pack(fill="x")
            label = tk.Label(panel, background="#000000", foreground="#cbd5e1", text="Waiting for video")
            label.pack(fill="both", expand=True)
            self.video_labels[camera] = label
        lower = tk.Frame(body, background="#0b1220")
        body.add(lower, minsize=300)
        controls = tk.Frame(lower, background="#101a2d", padx=8, pady=7)
        controls.pack(fill="x")
        ttk.Button(controls, text="▶ Play / Pause", command=self.toggle).pack(side="left")
        ttk.Button(controls, text="↺ Restart", command=lambda: self.seek(0)).pack(side="left", padx=6)
        self.time_label = tk.StringVar(value="0.00 / 0.00 s")
        tk.Label(controls, textvariable=self.time_label, background="#101a2d", foreground="#e2e8f0", width=16).pack(side="left")
        self.scale = ttk.Scale(controls, from_=0, to=1, command=lambda value: self.seek(float(value), refresh=True))
        self.scale.pack(side="left", fill="x", expand=True, padx=10)
        metrics = tk.Frame(lower, background="#0b1220")
        metrics.pack(fill="x", pady=(6, 2))
        for index, (name, title, unit, color) in enumerate(SIGNALS):
            card = tk.Frame(metrics, background="#111827", padx=10, pady=7, highlightbackground="#263244", highlightthickness=1)
            card.grid(row=index//3, column=index % 3, sticky="ew", padx=3, pady=2)
            metrics.grid_columnconfigure(index % 3, weight=1)
            tk.Label(card, text=title, background="#111827", foreground="#94a3b8", anchor="w").pack(fill="x")
            tk.Label(card, textvariable=self.metric_vars[name], background="#111827", foreground=color, anchor="w", font=("Segoe UI", 15, "bold")).pack(fill="x")
            tk.Label(card, text=unit, background="#111827", foreground="#64748b", anchor="w").pack(fill="x")
        plots_area = tk.Frame(lower, background="#0b1220")
        plots_area.pack(fill="both", expand=True, pady=(2, 0))
        self.plots = []
        for name, title, unit, color in SIGNALS:
            index = len(self.plots)
            plot = SignalPlot(plots_area, self.seek, height=92)
            plot.grid(row=index//2, column=index % 2, sticky="nsew", padx=3, pady=3)
            plots_area.grid_columnconfigure(index % 2, weight=1)
            plots_area.grid_rowconfigure(index//2, weight=1)
            plot.key = name
            plot.config_title, plot.config_unit, plot.config_color = title, unit, color
            self.plots.append(plot)

    def load_demo(self):
        project = Path(r"E:\Pose2SimProjects\Badminton_Final")
        try:
            manifest = build(project, APP_ROOT / "local_assets" / "a01_r1")
            self.load_manifest(manifest)
        except Exception as error:
            messagebox.showerror("A01 demo could not be prepared", str(error))

    def pick_manifest(self):
        name = filedialog.askopenfilename(title="Select synchronised data JSON", filetypes=[("JSON files", "*.json")])
        if name:
            self.video_folder_override = None
            self.load_manifest(Path(name))

    def pick_videos(self):
        folder = filedialog.askdirectory(title="Select folder containing cam01.mp4 … cam04.mp4")
        if not folder or not self.manifest_path:
            return
        self.video_folder_override = Path(folder)
        self.load_manifest(self.manifest_path)

    def load_manifest(self, path: Path):
        self.pause()
        payload = json.loads(path.read_text(encoding="utf-8"))
        required = {"rightHandGyro", "rightWristSpeed", "rightKneeAngle"}
        if not required <= set(payload.get("signals", {})):
            raise ValueError(f"Data JSON must contain {sorted(required)}")
        self.release_captures()
        self.manifest_path, self.payload = path, payload
        self.duration = float(payload["trial"]["duration_s"])
        self.fps = float(payload["trial"].get("visualRateHz", 60))
        for video in payload.get("videos", []):
            file = self.video_folder_override / f"{video['id']}.mp4" if self.video_folder_override else Path(video["file"])
            if not file.is_absolute():
                file = path.parent / file
            capture = cv2.VideoCapture(str(file))
            if not capture.isOpened():
                raise ValueError(f"Cannot open video: {file}")
            self.captures[video["id"]] = capture
        self.scale.configure(to=self.duration)
        trial = payload["trial"]
        evidence = payload.get("evidence") or {}
        evidence_status = evidence.get("status", "evidence report not loaded")
        self.status.set(f"{trial.get('participant','?')} · {trial.get('action','?')} · R{trial.get('repeat','?')}  |  {trial.get('alignmentStatus','alignment not stated')}  |  Evidence: {evidence_status}")
        for plot in self.plots:
            plot.set_signal(payload["signals"][plot.key], self.duration, plot.config_title, plot.config_unit, plot.config_color)
        self.seek(0)

    def open_evidence(self):
        evidence = self.payload.get("evidence") or {}
        report = evidence.get("report")
        if not report or not Path(report).is_file():
            messagebox.showinfo("Evidence chain", "No local evidence-chain report is linked to the loaded data package.")
            return
        messagebox.showinfo(
            "Evidence-chain status",
            f"Status: {evidence.get('status')}\nReview required: {', '.join(evidence.get('reviewRequiredStages', [])) or 'none'}\n\nReport:\n{report}",
        )
        os.startfile(report)  # opens local JSON in the user's registered editor

    def nearest(self, samples):
        points = [float(point["time"]) for point in samples]
        index = bisect_left(points, self.current)
        if index == len(points): index -= 1
        if index and abs(points[index-1]-self.current) < abs(points[index]-self.current): index -= 1
        return float(samples[index]["value"])

    def render_videos(self):
        frame_index = int(round(self.current * self.fps))
        for camera, label in self.video_labels.items():
            cap = self.captures.get(camera)
            if not cap:
                continue
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = cap.read()
            if not ok:
                continue
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            max_width, max_height = max(label.winfo_width(), 320), max(label.winfo_height(), 180)
            scale = min(max_width/frame.shape[1], max_height/frame.shape[0])
            image = Image.fromarray(frame).resize((max(2, int(frame.shape[1]*scale)), max(2, int(frame.shape[0]*scale))), Image.Resampling.LANCZOS)
            self.photos[camera] = ImageTk.PhotoImage(image)
            label.configure(image=self.photos[camera], text="")

    def seek(self, time: float, refresh: bool = False):
        if self.setting_scale:
            return
        self.current = min(self.duration, max(0.0, time))
        self.setting_scale = True
        self.scale.set(self.current)
        self.setting_scale = False
        self.time_label.set(f"{self.current:.2f} / {self.duration:.2f} s")
        for name, _, unit, _ in SIGNALS:
            self.metric_vars[name].set(f"{self.nearest(self.payload['signals'][name]):.2f}")
        for plot in self.plots:
            plot.current = self.current
            plot.render()
        self.render_videos()

    def toggle(self):
        if self.playing: self.pause()
        else:
            self.playing = True
            self.tick()

    def tick(self):
        if not self.playing: return
        if self.current >= self.duration:
            self.pause(); return
        self.seek(self.current + 1/self.fps)
        self.after_id = self.after(max(1, int(1000/self.fps)), self.tick)

    def pause(self):
        self.playing = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None

    def release_captures(self):
        for capture in self.captures.values(): capture.release()
        self.captures = {}

    def close(self):
        self.pause(); self.release_captures(); self.destroy()


def self_test(manifest: Path):
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    required = {"rightHandGyro", "rightKneeGyro", "combinedImuEnergy", "rightWristSpeed", "rightKneeAngle"}
    missing = required - set(payload.get("signals", {}))
    if missing: raise RuntimeError(f"Missing signal channels: {sorted(missing)}")
    for video in payload["videos"]:
        source = manifest.parent / video["file"]
        cap = cv2.VideoCapture(str(source))
        ok, frame = cap.read(); cap.release()
        if not ok or frame is None: raise RuntimeError(f"Cannot decode: {source}")
    print(f"PASS: {manifest.name}; {len(payload['videos'])} video streams; {len(payload['signals'])} signal channels")


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(r"E:\Pose2SimProjects\Badminton_Final"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    manifest = build(args.project_root, APP_ROOT / "local_assets" / "a01_r1")
    if args.self_test:
        self_test(manifest)
    else:
        Player(manifest).mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
