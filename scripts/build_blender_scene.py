"""Build a Blender scene from BadmintonFusion35 3-D trajectories.

Run with Blender, for example:

    blender --background --python scripts/build_blender_scene.py -- \
        --keypoints-csv examples/a10_r10/visual/keypoints_3d_filtered.csv \
        --data-rate 60 \
        --control-points examples/a10_r10/calibration/scene_points_click_order.csv \
        --calibration examples/a10_r10/calibration/Calib_scene.toml \
        --action-label A10-R10 --preview-frame 4080 \
        --output outputs/A10_R10_BadmintonFusion35.blend \
        --preview outputs/A10_R10_BadmintonFusion35_preview.png

The script intentionally visualizes measured/derived marker trajectories. It does not
invent an OpenSim surface model when .osim/.mot outputs are unavailable.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


CONNECTIONS = (
    ("Hip", "RHip"),
    ("RHip", "RKnee"),
    ("RKnee", "RAnkle"),
    ("RAnkle", "RHeel"),
    ("RHeel", "RBigToe"),
    ("RAnkle", "RBigToe"),
    ("RAnkle", "RSmallToe"),
    ("Hip", "LHip"),
    ("LHip", "LKnee"),
    ("LKnee", "LAnkle"),
    ("LAnkle", "LHeel"),
    ("LHeel", "LBigToe"),
    ("LAnkle", "LBigToe"),
    ("LAnkle", "LSmallToe"),
    ("Hip", "Neck"),
    ("Neck", "Head"),
    ("Head", "Nose"),
    ("Neck", "RShoulder"),
    ("RShoulder", "RElbow"),
    ("RElbow", "RWrist"),
    ("Neck", "LShoulder"),
    ("LShoulder", "LElbow"),
    ("LElbow", "LWrist"),
)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--trc", help="Pose2Sim TRC trajectory file")
    source.add_argument(
        "--keypoints-csv",
        help="BadmintonFusion35 long-form 3-D keypoint CSV",
    )
    parser.add_argument("--data-rate", type=float, default=60.0)
    parser.add_argument("--control-points", required=True)
    parser.add_argument("--calibration", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--preview", required=True)
    parser.add_argument("--action-label", default="A01")
    parser.add_argument("--preview-frame", type=int)
    parser.add_argument("--start-frame", type=int)
    parser.add_argument("--end-frame", type=int)
    return parser.parse_args(argv)


def read_trc(path: Path, start_frame: int | None = None, end_frame: int | None = None):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    metadata = lines[2].split("\t")
    rate = float(metadata[0])
    n_frames = int(metadata[2])
    n_markers = int(metadata[3])
    marker_tokens = lines[3].split("\t")
    names = [marker_tokens[2 + 3 * i].strip() for i in range(n_markers)]
    tracks = {name: [] for name in names}
    frame_numbers = []
    source_rows = 0
    for line in lines[5:]:
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < 2 + 3 * n_markers:
            continue
        source_rows += 1
        frame = int(float(fields[0]))
        if start_frame is not None and frame < start_frame:
            continue
        if end_frame is not None and frame > end_frame:
            continue
        frame_numbers.append(frame)
        for i, name in enumerate(names):
            x, y, z = (float(fields[2 + 3 * i + j]) for j in range(3))
            # Pose2Sim TRC: X=net-to-back, Y=vertical, Z=lateral.
            # Blender court: X=lateral, Y=net-to-back, Z=vertical.
            tracks[name].append((z, x, y))
    if not frame_numbers:
        raise RuntimeError("TRC contains no readable trajectory rows")
    if source_rows != n_frames:
        print(
            f"WARNING_TRC_FRAME_COUNT=header:{n_frames},rows:{source_rows}; "
            "using available source rows"
        )
    return rate, frame_numbers, tracks, n_frames, source_rows


def read_keypoints_csv(
    path: Path,
    rate: float,
    start_frame: int | None = None,
    end_frame: int | None = None,
):
    """Read the public long-form 3-D table without filling missing observations."""
    by_frame: dict[int, dict[str, tuple[float, float, float]]] = {}
    marker_order: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"source_frame", "keypoint", "x_m", "y_m", "z_m"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise RuntimeError(f"Keypoint CSV is missing columns: {sorted(missing)}")
        for row in reader:
            frame = int(float(row["source_frame"]))
            if start_frame is not None and frame < start_frame:
                continue
            if end_frame is not None and frame > end_frame:
                continue
            name = row["keypoint"].strip()
            if name not in marker_order:
                marker_order.append(name)
            # Public CSV: x=net-to-back, y=vertical, z=lateral.
            # Blender court: X=lateral, Y=net-to-back, Z=vertical.
            by_frame.setdefault(frame, {})[name] = (
                float(row["z_m"]),
                float(row["x_m"]),
                float(row["y_m"]),
            )
    frames = sorted(by_frame)
    if not frames:
        raise RuntimeError("Keypoint CSV contains no readable trajectory rows")
    incomplete = {
        frame: sorted(set(marker_order).difference(by_frame[frame]))
        for frame in frames
        if set(marker_order).difference(by_frame[frame])
    }
    if incomplete:
        first_frame = next(iter(incomplete))
        raise RuntimeError(
            "Keypoint CSV contains missing marker observations; "
            f"first incomplete frame {first_frame}: {incomplete[first_frame]}"
        )
    tracks = {
        name: [by_frame[frame][name] for frame in frames]
        for name in marker_order
    }
    return rate, frames, tracks, len(frames), len(frames)


def material(name: str, rgba: tuple[float, float, float, float], metallic=0.0, roughness=0.45):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    bsdf = next(
        (node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED"),
        None,
    )
    if bsdf is None:
        raise RuntimeError(f"Material {name!r} has no Principled BSDF node")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def add_box(name, location, scale, mat, collection=None):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    if collection is not None:
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)
    return obj


def add_sphere(name, location, radius, mat, collection=None):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    if collection is not None:
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)
    return obj


def animate_location(obj, frame_numbers, values):
    animate_property(obj, "location", frame_numbers, values)


def animate_property(obj, data_path, frame_numbers, components):
    # Blender 4.4+ requires an Action Slot for animation evaluation.  A first
    # keyframe_insert creates the correct slot; the remaining points are then
    # populated in bulk for performance.
    setattr(obj, data_path, components[0])
    obj.keyframe_insert(data_path=data_path, frame=float(frame_numbers[0]), group="A01 Motion")
    action = obj.animation_data.action
    for axis, values in enumerate(zip(*components)):
        curve = action.fcurves.find(data_path, index=axis)
        if curve is None:
            raise RuntimeError(f"Blender did not create {data_path}[{axis}] for {obj.name}")
        while curve.keyframe_points:
            curve.keyframe_points.remove(curve.keyframe_points[0], fast=True)
        curve.keyframe_points.add(len(values))
        flattened = []
        for frame, value in zip(frame_numbers, values):
            flattened.extend((float(frame), float(value)))
        curve.keyframe_points.foreach_set("co", flattened)
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"
        curve.update()


def add_animated_bone(name, frame_numbers, start_values, end_values, radius, mat, collection):
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=radius, depth=1.0)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)
    obj.rotation_mode = "QUATERNION"
    locations = []
    rotations = []
    scales = []
    local_z = Vector((0.0, 0.0, 1.0))
    for start, end in zip(start_values, end_values):
        a, b = Vector(start), Vector(end)
        delta = b - a
        length = max(delta.length, 1e-6)
        locations.append(tuple((a + b) * 0.5))
        rotations.append(tuple(local_z.rotation_difference(delta.normalized())))
        scales.append((1.0, 1.0, length))
    animate_property(obj, "location", frame_numbers, locations)
    animate_property(obj, "rotation_quaternion", frame_numbers, rotations)
    animate_property(obj, "scale", frame_numbers, scales)
    return obj


def add_curve(name, points, bevel_depth, mat, collection=None):
    curve = bpy.data.curves.new(name=name, type="CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = (*co, 1.0)
    obj = bpy.data.objects.new(name, curve)
    (collection or bpy.context.scene.collection).objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def add_text(text, location, size, mat, collection=None, align="CENTER"):
    curve = bpy.data.curves.new(name=f"Text_{text}", type="FONT")
    curve.body = text
    curve.align_x = align
    curve.size = size
    curve.extrude = 0.006
    obj = bpy.data.objects.new(f"Label_{text}", curve)
    (collection or bpy.context.scene.collection).objects.link(obj)
    obj.location = location
    obj.data.materials.append(mat)
    return obj


def load_control_points(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def parse_calibration(path: Path):
    import tomllib

    with path.open("rb") as stream:
        return tomllib.load(stream)


def rodrigues(rotation_vector):
    vector = Vector(rotation_vector)
    angle = vector.length
    if angle < 1e-12:
        return Matrix.Identity(3)
    return Matrix.Rotation(angle, 3, vector.normalized())


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def main():
    args = parse_args()
    # Resolve before Blender changes the active file directory while saving.
    output_path = Path(args.output).resolve()
    preview_path = Path(args.preview).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.parent.mkdir(parents=True, exist_ok=True)

    if args.trc:
        rate, frames, tracks, declared_frames, source_rows = read_trc(
            Path(args.trc), start_frame=args.start_frame, end_frame=args.end_frame
        )
    else:
        rate, frames, tracks, declared_frames, source_rows = read_keypoints_csv(
            Path(args.keypoints_csv),
            args.data_rate,
            start_frame=args.start_frame,
            end_frame=args.end_frame,
        )
    controls = load_control_points(Path(args.control_points))
    calibration = parse_calibration(Path(args.calibration))

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.collections:
        if block.name != "Collection":
            bpy.data.collections.remove(block)

    scene = bpy.context.scene
    scene.name = f"{args.action_label}_BadmintonFusion35"
    scene.frame_start = frames[0]
    scene.frame_end = frames[-1]
    scene.frame_set(frames[0])
    scene.render.fps = round(rate)
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(preview_path)
    scene.world.color = (0.025, 0.035, 0.05)

    court_collection = bpy.data.collections.new("Court_and_35_Control_Points")
    skeleton_collection = bpy.data.collections.new(f"{args.action_label}_3D_Skeleton")
    camera_collection = bpy.data.collections.new("Four_Calibrated_Cameras")
    scene.collection.children.link(court_collection)
    scene.collection.children.link(skeleton_collection)
    scene.collection.children.link(camera_collection)

    green = material("Court green", (0.035, 0.24, 0.11, 1.0), roughness=0.8)
    white = material("Court lines", (0.93, 0.96, 1.0, 1.0), roughness=0.55)
    blue = material("Left body", (0.08, 0.38, 0.95, 1.0), metallic=0.05)
    red = material("Right body", (0.94, 0.12, 0.10, 1.0), metallic=0.05)
    gold = material("Central body", (1.0, 0.66, 0.08, 1.0), metallic=0.08)
    cyan = material("Ground control points", (0.04, 0.85, 1.0, 1.0), metallic=0.15)
    magenta = material("Elevated control points", (0.96, 0.12, 0.72, 1.0), metallic=0.15)
    orange = material("Right wrist trajectory", (1.0, 0.27, 0.02, 1.0), metallic=0.1)
    dark = material("Camera body", (0.025, 0.03, 0.045, 1.0), metallic=0.4)

    add_box("Court floor", (0.0, 3.35, -0.035), (3.45, 3.70, 0.035), green, court_collection)
    line_w = 0.025
    for x in (-3.05, -2.59, 0.0, 2.59, 3.05):
        add_box(f"Court longitudinal {x:+.2f}", (x, 3.35, 0.012), (line_w, 3.35, 0.012), white, court_collection)
    for y in (0.0, 1.98, 5.94, 6.70):
        add_box(f"Court transverse {y:.2f}", (0.0, y, 0.014), (3.05, line_w, 0.014), white, court_collection)

    for row in controls:
        point_id = row["Point_ID"]
        location = (float(row["X_m"]), float(row["Y_m"]), float(row["Z_m"]))
        point_mat = cyan if row["Type"] == "Ground" else magenta
        add_sphere(point_id, location, 0.055, point_mat, court_collection)
        add_text(point_id, (location[0], location[1], location[2] + 0.09), 0.085, white, court_collection)

    for x, y, label in ((-3.45, 1.6, "Pole A"), (3.45, 5.1, "Pole B")):
        add_box(label, (x, y, 1.15), (0.025, 0.025, 1.15), white, court_collection)

    marker_objects = {}
    for name, values in tracks.items():
        mat = red if name.startswith("R") else blue if name.startswith("L") else gold
        radius = 0.055 if name not in {"Hip", "Neck", "Head"} else 0.075
        obj = add_sphere(name, values[0], radius, mat, skeleton_collection)
        marker_objects[name] = obj
        animate_location(obj, frames, values)

    for start, end in CONNECTIONS:
        if start not in marker_objects or end not in marker_objects:
            continue
        mat = red if end.startswith("R") else blue if end.startswith("L") else gold
        add_animated_bone(
            f"Bone_{start}_{end}", frames, tracks[start], tracks[end], 0.022, mat, skeleton_collection
        )

    if "RWrist" in tracks:
        requested_preview = args.preview_frame or min(frames[-1], frames[0] + int(rate * 25))
        preview_index = min(range(len(frames)), key=lambda i: abs(frames[i] - requested_preview))
        trail_start = max(0, preview_index - int(rate * 3))
        trail_end = min(len(frames), preview_index + int(rate * 3))
        trail_points = tracks["RWrist"][trail_start:trail_end:3]
        add_curve(f"{args.action_label}_RWrist_local_6s_trajectory", trail_points, 0.010, orange, skeleton_collection)

    target = Vector((0.0, 3.35, 1.15))
    for camera_name in ("cam01", "cam02", "cam03", "cam04"):
        if camera_name not in calibration:
            continue
        data = calibration[camera_name]
        rotation = rodrigues(data["rotation"])
        translation = Vector(data["translation"])
        center = -(rotation.transposed() @ translation)
        cam_data = bpy.data.cameras.new(camera_name)
        cam = bpy.data.objects.new(camera_name, cam_data)
        camera_collection.objects.link(cam)
        cam.location = center
        look_at(cam, target)
        cam.data.display_size = 0.35
        label = add_text(camera_name.upper(), (center.x, center.y, center.z + 0.35), 0.20, white, camera_collection)
        label.rotation_euler = (Vector((0.0, 3.35, 2.0)) - label.location).to_track_quat("Z", "Y").to_euler()
        body = add_box(f"{camera_name}_body", center, (0.12, 0.18, 0.10), dark, camera_collection)
        look_at(body, target)

    view_data = bpy.data.cameras.new("Presentation_Camera")
    view_camera = bpy.data.objects.new("Presentation_Camera", view_data)
    scene.collection.objects.link(view_camera)
    view_camera.location = (9.4, -8.2, 8.1)
    view_data.lens = 48
    look_at(view_camera, (0.0, 3.35, 1.0))
    scene.camera = view_camera

    bpy.ops.object.light_add(type="AREA", location=(0.0, 3.2, 9.0))
    key = bpy.context.object
    key.name = "Overhead_Key_Light"
    key.data.energy = 1700
    key.data.shape = "DISK"
    key.data.size = 8.0
    bpy.ops.object.light_add(type="AREA", location=(6.0, -1.0, 4.5))
    fill = bpy.context.object
    fill.name = "Fill_Light"
    fill.data.energy = 1100
    fill.data.size = 5.0
    look_at(fill, (0.0, 3.0, 1.0))

    title = add_text(
        f"{args.action_label} | 4 cameras | 35 control points | 3D Pose2Sim trajectory",
        (-3.0, -0.55, 0.15),
        0.30,
        white,
        align="LEFT",
    )
    if declared_frames != source_rows:
        audit = add_text(
            f"TRC audit: header {declared_frames} frames; {source_rows} source trajectory rows",
            (-3.0, -0.95, 0.13),
            0.18,
            white,
            align="LEFT",
        )
    if args.start_frame is not None or args.end_frame is not None:
        add_text(
            f"Selected source frames: {frames[0]}-{frames[-1]} ({len(frames)} frames)",
            (-3.0, -1.25, 0.13),
            0.18,
            white,
            align="LEFT",
        )

    # Render a motion-rich preview rather than the initial standing frame.
    render_frame = args.preview_frame or min(frames[-1], frames[0] + int(rate * 25))
    scene.frame_set(min(frames[-1], max(frames[0], render_frame)))
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))
    bpy.ops.render.render(write_still=True)
    scene.frame_set(frames[0])
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))
    print(f"ACTION_LABEL={args.action_label}")
    print(f"BLEND={output_path}")
    print(f"PREVIEW={preview_path}")
    print(f"FRAMES={len(frames)}")
    print(f"MARKERS={len(tracks)}")


if __name__ == "__main__":
    main()
