"""Build an educational cutaway + hot-staging film from the existing display.

Run with Blender --background --python build_animation.py -- --render previews
Geometry helpers take millimetres; the saved scene uses metres. No addons,
external textures, simulation caches or Python drivers are needed for playback.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import bmesh
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Starship_Interior_Animation.blend"
RENDERS = ROOT / "renders"
REPORT = ROOT / "animation_validation.json"
FRAMES = {"interior": 72, "ignition": 192, "liftoff": 250,
          "hot_staging": 305, "separated": 450}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--render", choices=("none", "previews", "video", "all"), default="previews")
parser.add_argument("--verify-only", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])


def original_hashes():
    return {str(p.relative_to(ROOT.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(ROOT.parent.rglob("*"))
            if p.suffix in {".blend", ".stl", ".3mf"} and p != OUTPUT}


def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


def link(obj, col, parent=None):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    obj.parent = parent
    return obj


def material(name, color, metal=0, emission=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = .32
    p.inputs["Emission Color"].default_value = (*color, 1)
    p.inputs["Emission Strength"].default_value = emission
    return m


def mesh(name, verts, faces, mat, col, parent=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata([tuple(v / 1000 for v in p) for p in verts], [], faces)
    data.materials.append(mat)
    data.update()
    o = bpy.data.objects.new(name, data)
    col.objects.link(o)
    o.parent = parent
    for p in data.polygons:
        p.use_smooth = True
    return o


def lathe(name, profile, mat, col, parent=None, segments=64):
    # Nonzero end radii with planar caps avoid degenerate triangles at poles.
    verts = [(r * math.cos(2 * math.pi * j / segments),
              r * math.sin(2 * math.pi * j / segments), z)
             for z, r in profile for j in range(segments)]
    faces = [(k * segments + j, k * segments + (j + 1) % segments,
              (k + 1) * segments + (j + 1) % segments, (k + 1) * segments + j)
             for k in range(len(profile) - 1) for j in range(segments)]
    faces += [tuple(reversed(range(segments))),
              tuple((len(profile) - 1) * segments + j for j in range(segments))]
    return mesh(name, verts, faces, mat, col, parent)


def rod(name, a, b, radius, mat, col, parent=None):
    a, b = Vector(a) / 1000, Vector(b) / 1000
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius / 1000,
                                      depth=(b - a).length, location=(a + b) / 2)
    o = link(bpy.context.object, col, parent)
    o.name = name
    o.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    o.data.materials.append(mat)
    return o


def ring(name, radius, minor, z, mat, col, parent):
    bpy.ops.mesh.primitive_torus_add(major_segments=64, minor_segments=8,
                                   major_radius=radius / 1000, minor_radius=minor / 1000,
                                   location=(0, 0, z / 1000))
    o = link(bpy.context.object, col, parent)
    o.name = name
    o.data.materials.append(mat)
    return o


def visible_between(obj, start, end):
    for frame, hidden in ((1, start > 1), (start, False), (end + 1, True)):
        for prop in ("hide_render", "hide_viewport"):
            setattr(obj, prop, hidden)
            obj.keyframe_insert(prop, frame=frame)


def text(name, body, size, location, col, parent=None, mat=None):
    data = bpy.data.curves.new(name, "FONT")
    data.body, data.size = body, size / 1000
    data.space_line = 1.2
    data.materials.append(mat or white)
    obj = bpy.data.objects.new(name, data)
    col.objects.link(obj)
    obj.location = Vector(location) / 1000
    obj.parent = parent
    return obj


def key_location(obj, keys):
    for f, loc in keys:
        obj.location = Vector(loc) / 1000
        obj.keyframe_insert("location", frame=f)


def camera(name, width, target):
    data = bpy.data.cameras.new(name)
    data.type, data.ortho_scale = "ORTHO", width / 1000
    data.clip_start, data.clip_end = .0001, 10
    o = bpy.data.objects.new(name, data)
    studio.objects.link(o)
    o.location = (target[0] / 1000, -.5, target[1] / 1000)
    o.rotation_euler = (math.pi / 2, 0, 0)
    return o


def hud(cam, title, subtitle, start, end):
    # Camera-local text keeps the explanation legible while the camera follows.
    w = cam.data.ortho_scale * 1000
    for name, body, size, loc, mat in (
        ("Title", title, w * .023, (-w * .455, w * .228, -100), white),
        ("Subtitle", subtitle, w * .011, (-w * .455, w * .196, -100), muted),
        ("Footer", "STARSHIP   /   STRUCTURE & FLIGHT STUDY     •     SCHEMATIC / TIME COMPRESSED",
         w * .009, (-w * .455, -w * .252, -100), muted)):
        obj = text(name + " " + str(start), body, size, loc, captions, cam, mat)
        visible_between(obj, start, end)


def validate(expected):
    assert original_hashes() == expected, "An original model or print export changed"
    ship, booster, base = [bpy.data.objects[n] for n in
                           ("MOVE_Starship", "MOVE_SuperHeavy", "MOVE_Base")]
    tanks = [o for o in bpy.data.objects if o.name.startswith("TANK |")]
    assert len(tanks) == 4
    tank_reports = []
    for o in tanks:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        record = {"name": o.name, "parent": o.parent.name,
                  "nonmanifold_edges": sum(not e.is_manifold for e in bm.edges),
                  "volume_m3": bm.calc_volume(signed=True)}
        bm.free()
        assert record["nonmanifold_edges"] == 0 and record["volume_m3"] > 0, record
        tank_reports.append(record)
    for colname, parent in (("INTERIOR | Starship", ship), ("INTERIOR | SuperHeavy", booster)):
        assert all(o.parent == parent for o in bpy.data.collections[colname].objects)
    flames = list(bpy.data.collections["FX | engine flames"].objects)
    assert len(flames) == 78  # One outer plume and one core per engine.
    assert sum(o.name.startswith("SHIP RVac") or o.name.startswith("SHIP SeaLevel")
               for o in scene.objects if o.type == "MESH" and not o.name.startswith("CUT")) == 6
    assert sum(o.name.startswith("BOOSTER Raptor") for o in scene.objects) == 33
    anchors = {}
    for o in flames:
        bell_name = o.name.removeprefix("FLAME | ").rsplit(" ", 1)[0]
        bell = bpy.data.objects[bell_name]
        anchors[o.name] = Vector((bell.location.x, bell.location.y,
                                 min(v.co.z for v in bell.data.vertices)))
        assert (o.location - anchors[o.name]).length < 1e-8
    for f in range(1, 481):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        assert base.location.length < 1e-8
        if 145 <= f <= 312:
            assert (ship.location - booster.location).length < 1e-7
        for o in flames:
            assert o.parent in (ship, booster)
            assert (o.matrix_world.translation - o.parent.matrix_world @ anchors[o.name]).length < 1e-7
        if 289 <= f <= 312:
            assert all(o.scale.z > .0001 for o in flames if o.parent == ship)
        if 205 <= f <= 288 or f >= 337:
            # Ignition and hot-stage closeups intentionally crop the stack.
            for name in ("Super Heavy | booster", "Starship | upper stage"):
                obj = bpy.data.objects[name]
                for corner in obj.bound_box:
                    p = world_to_camera_view(scene, scene.camera, obj.matrix_world @ Vector(corner))
                    assert .01 < p.x < .99 and .01 < p.y < .99, (f, name, tuple(p))
        if f in (72, 192, 305, 450):
            for obj in bpy.data.collections["CUTAWAY | front shell removed"].objects:
                assert obj.hide_render == (f >= 145)
    scene.frame_set(480)
    assert ship.location.z - booster.location.z > .1
    assert ship.location.x - booster.location.x > .08
    scene.frame_set(1)
    return {"blender": bpy.app.version_string, "frames": 480, "fps": 24,
            "resolution": [1920, 1080], "tanks": tank_reports,
            "all_480_frames_checked": True, "engine_plume_count": 39,
            "flame_anchors_follow_bells": True, "wide_shots_keep_both_stages_in_frame": True,
            "hot_staging_ignition_frame": 289, "separation_begins_after_frame": 312,
            "original_files_unchanged": expected,
            "no_external_textures": all(i.source != "FILE" or i.packed_file for i in bpy.data.images),
            "engineering_replica": False, "b2_uploaded": False}


if args.verify_only:
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
    scene = bpy.context.scene
    expected = json.loads(REPORT.read_text())["original_files_unchanged"]
    print("REOPEN_VALIDATION", json.dumps(validate(expected)), flush=True)
    sys.exit(0)

baseline = original_hashes()
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "Starship_Separable.blend"))
scene = bpy.context.scene
scene.name = "Starship | Cutaway + Launch"
bpy.context.preferences.filepaths.save_version = 0
scene.animation_data_clear()
scene.timeline_markers.clear()
# Print meshes and model-specific friction-fit sleeves have no role in flight.
for c in list(bpy.data.collections):
    if c.hide_render or c.name == "STUDIO":
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(c)
for name in ("SHIP keyed male sleeve", "BOOSTER hot-stage receiver", "Hot-stage solid core",
             "BASE removable launch cradle"):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
ship, booster, base = [bpy.data.objects[n] for n in ("MOVE_Starship", "MOVE_SuperHeavy", "MOVE_Base")]
studio = collection("STUDIO | animation")
captions = collection("CAPTIONS | explanatory labels")
cutaway = collection("CUTAWAY | front shell removed")
ship_inside = collection("INTERIOR | Starship")
booster_inside = collection("INTERIOR | SuperHeavy")
effects = collection("FX | engine flames")
smoke_col = collection("FX | ground exhaust")
steel = material("Interior | satin alloy", (.34, .46, .53), .65)
lox = material("Interior | liquid oxygen blue", (.025, .38, .64), .35)
methane = material("Interior | methane amber", (.82, .30, .065), .3)
pipe_mat = material("Interior | feed pipe ivory", (.75, .81, .84), .4)
white = material("Labels | white", (.8, .9, 1), emission=1)
muted = material("Labels | muted blue", (.24, .45, .58), emission=1)
flame_mat = material("Exhaust | blue sheath", (.045, .22, 1), emission=3)
core_mat = material("Exhaust | hot core", (.7, .86, 1), emission=5)
smoke_mat = material("Exhaust | pale steam", (.24, .30, .37))

# Replace the opaque printing cradle with an open illustrative launch support.
base_col = bpy.data.collections["DISPLAY | Base"]
for x in (-9, 9):
    for y in (-4, 4):
        rod("BASE | open support leg", (x, y, 5), (x, y, 10.5), .45, steel, base_col, base)
        rod("BASE | support arm", (x, y, 10.5), (x * .7, y * .7, 10.5), .35, steel, base_col, base)

# Retain back-half shells in the introduction; keep intact shells for flight.
for parent, name in ((ship, "Starship"), (booster, "SuperHeavy")):
    for o in list(bpy.data.collections["DISPLAY | " + name].objects):
        if o.type not in {"MESH", "FONT"}:
            continue
        if o.name.startswith(("SHIP RVac", "SHIP SeaLevel", "BOOSTER Raptor")):
            continue
        visible_between(o, 145, 480)
        if o.type == "FONT":
            continue
        copy = o.copy()
        copy.data = o.data.copy()
        copy.animation_data_clear()
        copy.name = "CUT | " + o.name
        cutaway.objects.link(copy)
        # Source transforms contain translations as well as already-applied scale.
        bm = bmesh.new()
        bm.from_mesh(copy.data)
        plane = copy.matrix_world.inverted() @ Vector((0, 0, 0))
        normal = copy.matrix_world.to_3x3().transposed() @ Vector((0, 1, 0))
        bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                              dist=1e-8, plane_co=plane, plane_no=normal,
                              clear_inner=True, clear_outer=False)
        bm.to_mesh(copy.data)
        bm.free()
        visible_between(copy, 1, 144)
for o in bpy.data.collections["DISPLAY | Base"].objects:
    if o != base:
        visible_between(o, 145, 480)


def tank(name, bottom, top, mat, parent, col):
    radius, dome = 6.55, 2.5
    profile = [(bottom, .04)]
    for i in range(1, 13):
        angle = math.pi / 2 * i / 12
        profile.append((bottom + dome * (1 - math.cos(angle)), radius * math.sin(angle)))
    for i in range(13):
        angle = math.pi / 2 * i / 12
        profile.append((top - dome + dome * math.sin(angle), max(.04, radius * math.cos(angle))))
    o = lathe("TANK | " + name, profile, mat, col, parent)
    o["note"] = "Closed illustrative tank envelope; positions and dimensions are not engineering data."
    for z in (bottom + dome, top - dome):
        ring("Tank dome seam | " + name, radius, .07, z, steel, col, parent)
    return o


for parent, col, lo, hi, engine_z in ((booster, booster_inside, (16, 75), (77, 109), 12),
                                    (ship, ship_inside, (128, 149), (151, 169), 125.5)):
    tank(parent.name + " / LOX", *lo, lox, parent, col)
    tank(parent.name + " / CH4", *hi, methane, parent, col)
    ring("Engine thrust ring", 6.6, .30, engine_z, steel, col, parent)
    for j in range(8):
        angle = j * math.pi / 4
        rod("Engine support spoke", (0, 0, engine_z),
            (6.5 * math.cos(angle), 6.5 * math.sin(angle), engine_z), .18, steel, col, parent)
    for x, z, mat in ((-5.65, lo[0], lox), (5.65, hi[0], methane)):
        # Routing is shown along the shell, outside the tank envelopes.
        rod("Main feed line", (x, -3.9, engine_z), (x, -3.9, z + 3), .21, mat, col, parent)
        rod("Feed line elbow", (x, -3.9, z + 3), (x * .80, -3.0, z + 3), .21, mat, col, parent)
        rod("Engine manifold", (x, -3.9, engine_z), (0, 0, engine_z), .18, pipe_mat, col, parent)
    lathe("Payload floor" if parent == ship else "Upper tank support", [(hi[1] + 1, 6.65),
          (hi[1] + 1.3, 6.65)], steel, col, parent)

# Illustrative cargo envelope: deliberately distinguish it from propellant tanks.
for z in (173, 180, 187):
    ring("Payload bay frame", 6.25 if z < 187 else 5.0, .12, z, steel, ship_inside, ship)
for x in (-3.2, 3.2):
    rod("Payload support", (x, 2.6, 171), (x, 2.6, 187), .14, steel, ship_inside, ship)
payload = lathe("PAYLOAD | illustrative satellite", [(174, 2.7), (183, 2.7), (185, 1.7)],
                methane, ship_inside, ship)
payload["note"] = "Generic cargo placeholder; not a Starlink deployment assembly."
for x in (-4.1, 4.1):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x / 1000, 0, .178))
    o = link(bpy.context.object, ship_inside, ship)
    o.name = "PAYLOAD | folded panel"
    o.scale = (.0015, .0018, .008)
    o.data.materials.append(lox)
# Open annular hot-stage interface, independent of the printing sleeve.
for z in (118, 121):
    ring("FLIGHT | vented hot-stage rim", 7.4, .18, z, steel, booster_inside, booster)

intro = camera("CAM | 01 interior", 310, (0, 75))
flight = camera("CAM | 02 flight", 480, (0, 90))
staging = camera("CAM | 03 hot staging", 265, (0, 206))
pad = camera("CAM | 04 ignition closeup", 150, (-10, 33))
hud(intro, "01 / INSIDE THE STACK", "Two stages. Four tanks. One payload bay.", 1, 144)
hud(pad, "02 / IGNITION", "33 booster engines build thrust before liftoff.", 145, 204)
hud(flight, "03 / LIFTOFF", "Both stages climb together. The base stays on the ground.", 205, 288)
hud(staging, "04 / HOT STAGING", "Upper engines ignite first. Then the stages pull apart.", 289, 336)
hud(flight, "05 / SEPARATION", "Starship continues upward; the booster follows its own path.", 337, 480)
for body, x, z, color in (("SUPER HEAVY", -72, 129, white), ("STARSHIP", 23, 129, white),
                         ("CH4", -41, 95, methane), ("LIQUID OXYGEN", -41, 53, lox),
                         ("FEED LINES", -41, 29, white), ("THRUST FRAME", -41, 14, white),
                         ("PAYLOAD", 52, 95, white), ("CH4", 52, 75, methane),
                         ("LIQUID OXYGEN", 52, 56, lox), ("6 ENGINES", 52, 38, white)):
    obj = text("Interior label | " + body, body, 2.3, (x, -15, z), captions, mat=color)
    obj.rotation_euler.x = math.pi / 2
    visible_between(obj, 1, 144)
    if z < 120:
        left = x < 0
        line = rod("Interior label leader", (-50 if left else 44, -15, z),
                   (x - 2, -15, z), .07, muted, captions)
        visible_between(line, 1, 144)

flight_positions = [(145, (0, 0, 0)), (204, (0, 0, 0)), (240, (0, 0, 15)),
                    (288, (0, 0, 65)), (312, (0, 0, 90))]
key_location(booster, [(1, (-58, 0, 0)), (144, (-58, 0, 0)), *flight_positions,
                      (360, (-10, 0, 113)), (480, (-55, 0, 110))])
key_location(ship, [(1, (35, 0, -86)), (144, (35, 0, -86)), *flight_positions,
                   (360, (12, 0, 137)), (480, (48, 0, 260))])
for f, angle in ((1, 0), (312, 0), (360, -.07), (480, -.30)):
    booster.rotation_euler.y = angle
    booster.keyframe_insert("rotation_euler", frame=f)
key_location(flight, [(145, (0, -500, 90)), (204, (0, -500, 90)),
                      (240, (0, -500, 105)), (288, (0, -500, 155)), (312, (0, -500, 180)),
                      (360, (0, -500, 218)), (480, (0, -500, 285))])
key_location(staging, [(289, (0, -500, 201)), (312, (0, -500, 226)),
                       (336, (0, -500, 249))])
for f, width in ((145, .480), (312, .480), (480, .690)):
    flight.data.ortho_scale = width
    flight.data.keyframe_insert("ortho_scale", frame=f)
# HUD scales with orthographic zoom, using ordinary keyframes rather than drivers.
for o in captions.objects:
    if o.parent == flight:
        original = o.location.copy()
        for f, factor in ((145, 1), (312, 1), (480, .690 / .480)):
            o.location = (original.x * factor, original.y * factor, original.z)
            o.scale = (factor,) * 3
            o.keyframe_insert("location", frame=f)
            o.keyframe_insert("scale", frame=f)

# Exhaust anchored at the actual bell exits, including their radial positions.
for o in list(scene.objects):
    if not o.name.startswith(("BOOSTER Raptor", "SHIP SeaLevel", "SHIP RVac")):
        continue
    is_ship = o.parent == ship
    exit_z = min(v.co.z for v in o.data.vertices) * 1000
    radius = max(math.hypot(v.co.x, v.co.y) for v in o.data.vertices) * 1000
    for core, mat in ((False, flame_mat), (True, core_mat)):
        r, length = radius * (.48 if core else .82), (14 if core else 25) * (1.25 if is_ship else 1)
        flame = lathe("FLAME | " + o.name + (" core" if core else " sheath"),
                      [(-length, .02), (-length * .65, r * .48), (-length * .15, r), (0, r * .7)],
                      mat, effects, o.parent, segments=16)
        flame.location = (o.location.x, o.location.y, exit_z / 1000)
        keys = ([(1, .00001), (288, .00001), (289, .08), (300, 1), (480, 1)] if is_ship else
                [(1, .00001), (168, .00001), (169, .015), (192, .085), (204, .085),
                 (240, 1), (275, 1), (288, .7),
                 (300, .24 if int(o.name.split()[-1]) > 30 else .00001),
                 (336, .00001), (480, .00001)])
        for f, strength in keys:
            flame.scale = (max(.001, min(1, strength * 12)),) * 2 + (strength,)
            flame.keyframe_insert("scale", frame=f)

# Radial vent glow makes ignition visible while the bells are inside the interstage.
vent_fx = collection("FX | hot-stage vents")
for i in range(16):
    angle = 2 * math.pi * i / 16
    jet = lathe("Hot-stage vent exhaust", [(-3.5, .03), (-1, .48), (0, .34)],
                flame_mat, vent_fx, booster, segments=12)
    jet.location = (7.3 * math.cos(angle) / 1000, 7.3 * math.sin(angle) / 1000, .1195)
    jet.rotation_euler = Vector((-math.cos(angle), -math.sin(angle), 0)).to_track_quat("Z", "Y").to_euler()
    for f, scale in ((1, .00001), (288, .00001), (289, .1), (300, 1), (312, 1), (330, .00001)):
        jet.scale = (scale,) * 3
        jet.keyframe_insert("scale", frame=f)

random.seed(21)
for i in range(22):
    angle = 2 * math.pi * i / 22
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1)
    o = link(bpy.context.object, smoke_col)
    o.name = "Ground vapor %02d" % i
    o.data.materials.append(smoke_mat)
    for polygon in o.data.polygons:
        polygon.use_smooth = True
    r = random.uniform(.004, .010)
    start = 170 + i * 2
    for f, distance, scale in ((1, .009, .000001), (start, .009, .000001),
                              (start + 18, .022, r * .7), (start + 65, .048, r),
                              (start + 110, .070, .000001), (480, .070, .000001)):
        o.location = (distance * math.cos(angle), distance * math.sin(angle), .006)
        o.scale = (scale * 1.7, scale, scale * .6)
        o.keyframe_insert("location", frame=f)
        o.keyframe_insert("scale", frame=f)
    visible_between(o, start, start + 110)

# Studio lighting remains fixed in world coordinates; a broad upper light covers flight.
for name, loc, power, size, color in (
    ("Key", (.10, -.16, .25), 9, .25, (.73, .86, 1)),
    ("Rim", (-.15, .08, .28), 12, .23, (1, .62, .3)),
    ("Fill", (-.18, -.18, .12), 5, .25, (.55, .76, 1)),
    ("Flight light", (.1, -.12, .48), 12, .3, (.78, .88, 1))):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.shape, data.size, data.color = power, "DISK", size, color
    o = bpy.data.objects.new(name, data)
    studio.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector((0, 0, .16)) - o.location).to_track_quat("-Z", "Y").to_euler()
data = bpy.data.lights.new("Ignition glow", "POINT")
data.color, data.shadow_soft_size = (.3, .5, 1), .012
o = bpy.data.objects.new("Ignition glow", data)
studio.objects.link(o)
o.location = (0, -.01, .009)
o.parent = booster
for f, power in ((1, 0), (168, 0), (192, .13), (288, .13), (312, 0)):
    data.energy = power
    data.keyframe_insert("energy", frame=f)
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get("Background")
background.inputs[0].default_value = (.008, .017, .029, 1)
background.inputs[1].default_value = .5
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.frame_start, scene.frame_end = 1, 480
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = 0
scene.render.film_transparent = False
for frame, label, cam in ((1, "01 INSIDE / tanks & payload", intro),
                          (145, "02 ENGINE CLOSEUP", pad), (169, "BOOSTER IGNITION", None),
                          (205, "03 LIFTOFF", flight), (289, "04 SHIP IGNITION / hot staging", staging),
                          (313, "SEPARATION begins", None), (337, "05 INDEPENDENT FLIGHT", flight)):
    marker = scene.timeline_markers.new(label, frame=frame)
    if cam:
        marker.camera = cam
scene.camera = intro
# Linear curves prevent overshoot of the matched pre-separation trajectories.
for action in bpy.data.actions:
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = "CONSTANT" if fc.data_path.startswith("hide_") else "LINEAR"
scene["README"] = "Space = play. Frame 72 = cutaway; 192 ignition; 250 liftoff; 305 hot staging; 450 separated. Alt+A deselect. View > Viewpoint > Camera."
scene["Model scope"] = "Educational 6/33-engine baseline. Colored sealed tank envelopes, pipe routes and cargo are schematic. Not a flight revision replica."
scene["Source model"] = "Starship_Separable.blend (preserved unchanged)"
scene["Issue"] = "https://github.com/The-V-Factor/poly-bakery/issues/1"
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            area.spaces.active.region_3d.view_perspective = "CAMERA"
            area.spaces.active.clip_start = .0001
            area.spaces.active.clip_end = 100
            area.spaces.active.shading.color_type = "MATERIAL"
            area.spaces.active.overlay.show_extras = False
            area.spaces.active.region_3d.view_location = (0, 0, .065)
            area.spaces.active.region_3d.view_distance = .3
RENDERS.mkdir(exist_ok=True)
report = validate(baseline)
scene.render.image_settings.media_type = "VIDEO"
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.ffmpeg.audio_codec = "NONE"
scene.render.filepath = "//renders/Starship_Flight.mp4"
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT))
# Reopen before rendering to verify that no in-memory construction state is needed.
bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
scene = bpy.context.scene
report.update(validate(baseline))
REPORT.write_text(json.dumps(report, indent=2) + "\n")
if args.render in {"previews", "all"}:
    for name, frame in FRAMES.items():
        bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
        scene = bpy.context.scene
        scene.render.image_settings.media_type = "IMAGE"
        scene.render.image_settings.file_format = "PNG"
        scene.frame_set(frame)
        scene.render.filepath = str(RENDERS / ("animation_" + name + ".png"))
        bpy.ops.render.render(write_still=True)
if args.render in {"video", "all"}:
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
    scene = bpy.context.scene
    scene.render.image_settings.media_type = "VIDEO"
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.filepath = str(RENDERS / "Starship_Flight.mp4")
    bpy.ops.render.render(animation=True)
assert original_hashes() == baseline
print("ANIMATION_COMPLETE", json.dumps(report), flush=True)
