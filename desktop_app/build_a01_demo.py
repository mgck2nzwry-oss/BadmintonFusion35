"""Derive a local-only, no-audio A01-R1 package for the desktop player."""

from __future__ import annotations

import csv
import json
import math
import shutil
import subprocess
from pathlib import Path

OFFSETS = {"cam01": 0, "cam02": 15, "cam03": 72, "cam04": 117}


def number(value: str | None) -> float:
    try:
        return float(value or "nan")
    except ValueError:
        return float("nan")


def mapping_row(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if (row.get("Participant"), row.get("Trial"), row.get("Repeat")) == ("P01", "A01", "1"):
                return row
    raise ValueError("P01 / A01 / repeat 1 was not found in the mapping table")


def imu_signals(path: Path, start: float, end: float) -> dict[str, list[dict[str, float]]]:
    result = {"rightHandGyro": [], "rightKneeGyro": [], "combinedImuEnergy": []}
    fields = {
        "rightHandGyro": "WTRhand_GyroMagnitudeSmooth_deg_s",
        "rightKneeGyro": "WTRknee_GyroMagnitudeSmooth_deg_s",
        "combinedImuEnergy": "CombinedIMUEnergy",
    }
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            time = number(row.get("SessionTime_s"))
            if not start <= time <= end:
                continue
            for name, field in fields.items():
                value = number(row.get(field))
                if math.isfinite(value):
                    result[name].append({"time": round(time - start, 6), "value": round(value, 6)})
    return result


def triplet(row: list[str], index: int) -> tuple[float, float, float]:
    start = 2 + index * 3
    return number(row[start]), number(row[start + 1]), number(row[start + 2])


def kinematic_signals(path: Path, start_frame: int, end_frame: int, start_time: float) -> dict[str, list[dict[str, float]]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.reader(source, delimiter="\t"))
    indices = {name: i for i, name in enumerate(rows[3][2::3]) if name}
    if {"RHip", "RKnee", "RAnkle", "RWrist"} - set(indices):
        raise ValueError("The A01 TRC file lacks one or more required right-side markers")
    wrist_speed: list[dict[str, float]] = []
    knee_angle: list[dict[str, float]] = []
    prior_wrist: tuple[float, float, float] | None = None
    prior_time: float | None = None
    for row in rows[5:]:
        if len(row) < 6 or not row[0]:
            continue
        frame, time = int(float(row[0])), number(row[1])
        if frame < start_frame or frame > end_frame:
            continue
        hip, knee, ankle, wrist = (triplet(row, indices[name]) for name in ("RHip", "RKnee", "RAnkle", "RWrist"))
        valid = lambda point: all(math.isfinite(v) for v in point)
        local_time = round(time - start_time, 6)
        if valid(hip) and valid(knee) and valid(ankle):
            ba, bc = tuple(a-b for a, b in zip(hip, knee)), tuple(a-b for a, b in zip(ankle, knee))
            norm = math.sqrt(sum(v*v for v in ba)) * math.sqrt(sum(v*v for v in bc))
            if norm:
                angle = math.degrees(math.acos(max(-1.0, min(1.0, sum(a*b for a, b in zip(ba, bc)) / norm))))
                knee_angle.append({"time": local_time, "value": round(angle, 6)})
        if prior_wrist and prior_time is not None and valid(wrist) and time > prior_time:
            speed = math.sqrt(sum((a-b)**2 for a, b in zip(wrist, prior_wrist))) / (time-prior_time)
            wrist_speed.append({"time": local_time, "value": round(speed, 6)})
        prior_wrist, prior_time = (wrist, time) if valid(wrist) else (None, None)
    return {"rightWristSpeed": wrist_speed, "rightKneeAngle": knee_angle}


def build(project_root: Path, output_root: Path, make_videos: bool = True) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    existing_manifest = output_root / "a01-r1-sync.json"
    existing_mode = None
    if existing_manifest.exists():
        try:
            existing_mode = json.loads(existing_manifest.read_text(encoding="utf-8")).get("videoRenderMode")
        except json.JSONDecodeError:
            pass
    row = mapping_row(project_root / "P01_IMU_Alignment" / "P01_visual_IMU_repetition_mapping.csv")
    visual_start, visual_end = number(row["StartTime_s"]), number(row["EndTime_s"])
    imu_start, imu_end = number(row["MappedIMUStart_s"]), number(row["MappedIMUEnd_s"])
    duration = visual_end - visual_start
    evidence_path = project_root / "reports" / "A01_R01_evidence_chain" / "evidence_chain.json"
    evidence: dict[str, object] | None = None
    if evidence_path.is_file():
        report = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence = {
            "status": report.get("status"),
            "reviewRequiredStages": report.get("review_required_stages", []),
            "failedStages": report.get("failed_stages", []),
            "report": str(evidence_path),
        }
    signals = imu_signals(project_root / "P01_IMU_Alignment" / "P01_IMU_50Hz_alignment_preview.csv", imu_start, imu_end)
    signals.update(kinematic_signals(project_root / "A01" / "pose-3d" / "A01_1-3814_filt_butterworth.trc", int(row["StartFrame"]), int(row["EndFrame"]), visual_start))
    videos = []
    ffmpeg = shutil.which("ffmpeg")
    for camera, offset in OFFSETS.items():
        target = output_root / "videos" / f"{camera}.mp4"
        # Pose2Sim's rendered 2D result preserves the original camera view while
        # adding its detected keypoints, limbs, person ID and bounding box.
        source = project_root / "A01" / "pose" / f"{camera}_pose.mp4"
        if make_videos and (existing_mode != "pose2d_overlay" or not target.exists() or target.stat().st_size == 0):
            if not ffmpeg:
                raise RuntimeError("ffmpeg is required to make synchronized local clips but was not found on PATH")
            target.parent.mkdir(parents=True, exist_ok=True)
            command = [ffmpeg, "-y", "-ss", f"{visual_start + offset/60:.6f}", "-i", str(source), "-t", f"{duration:.6f}", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", str(target)]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        videos.append({"id": camera, "file": str(Path("videos") / f"{camera}.mp4"), "syncFrameOffset": offset, "view": "Pose2Sim 2D skeleton overlay"})
    payload = {
        "schemaVersion": "badmintonfusion35-desktop-v1",
        "videoRenderMode": "pose2d_overlay",
        "trial": {"participant": "P01", "action": "A01", "repeat": 1, "visualRateHz": 60, "imuRateHz": 50, "duration_s": round(duration, 6), "alignmentStatus": row["AlignmentStatus"], "maxCorrelation": number(row["MaxCorrelation"])},
        "videos": videos,
        "evidence": evidence,
        "signals": signals,
        "provenance": "Local A01-R1 evidence package. Each video is the Pose2Sim 2D rendered result, preserving the camera view with detected skeleton overlay. It uses final camera synchronization and the recorded visual-IMU alignment; no audio is included.",
    }
    manifest = output_root / "a01-r1-sync.json"
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
