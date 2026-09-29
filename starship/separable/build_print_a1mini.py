"""Printable opening-shell derivative. Run with Blender 5.2 in background.

Construction and STL coordinates are millimetres. Preserve all prior models.
0.4 mm nozzle / PETG: 1.4 mm shells, 1.2 mm relief pipes, 2 mm locating pins.
The interior inserts have flat backs and are glued into the rear shells.
"""
import hashlib
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "printing" / "a1mini"
OUT.mkdir(exist_ok=True)
SOURCE = ROOT / "printing" / "Starship_Separable_Print.blend"
ANIMATION = ROOT / "Starship_Interior_Animation.blend"
PROTECTED = [SOURCE, ANIMATION, ROOT / "Starship_Separable.blend"] + list((ROOT / "printing").glob("*.stl")) + list((ROOT / "printing").glob("*.3mf"))
before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in PROTECTED}
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
bpy.context.preferences.filepaths.save_version = 0
for o in list(bpy.data.objects):
    if not o.name.startswith("PRINT_"):
        bpy.data.objects.remove(o, do_unlink=True)
for c in bpy.data.collections:
    c.hide_render = c.hide_viewport = False
for o in list(scene.objects):
    o.data.transform(Matrix.Scale(1000, 4) @ o.matrix_world)
    o.matrix_world = Matrix.Identity(4)


def active(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def apply(o, modifier):
    active(o)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def box(name, center, size):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    o = bpy.context.object
    o.name, o.scale = name, size
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


def cylinder(name, radius, length, center, axis="Z"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=radius, depth=length, location=center)
    o = bpy.context.object
    o.name = name
    if axis == "Y":
        o.rotation_euler.x = math.pi / 2
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


def boolean(o, tool, operation="DIFFERENCE"):
    mod = o.modifiers.new(operation, "BOOLEAN")
    mod.operation, mod.solver, mod.object = operation, "EXACT", tool
    apply(o, mod)
    bpy.data.objects.remove(tool, do_unlink=True)


def duplicate(o, name):
    c = o.copy()
    c.data = o.data.copy()
    scene.collection.objects.link(c)
    c.name = name
    return c


def union(objects, name):
    active(objects[0])
    for o in objects:
        o.select_set(True)
    if len(objects) > 1:
        bpy.ops.object.join()
    o = bpy.context.object
    o.name = name
    mod = o.modifiers.new("Connected printable union", "REMESH")
    mod.mode, mod.voxel_size = "VOXEL", .075
    apply(o, mod)
    mod = o.modifiers.new("Print triangles", "TRIANGULATE")
    apply(o, mod)
    return o


def audit(o):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    # STL merges coincident vertices. Check the same topology here so a
    # vanishing wall cannot pass merely because its two sides use distinct IDs.
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=.001)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.verts.ensure_lookup_table()
    seen, groups = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, count = [v], 0
        seen.add(v.index)
        while stack:
            q = stack.pop()
            count += 1
            for edge in q.link_edges:
                n = edge.other_vert(q)
                if n.index not in seen:
                    seen.add(n.index)
                    stack.append(n)
        groups.append(count)
    result = {"components": len(groups), "nonmanifold_edges": sum(not e.is_manifold for e in bm.edges),
              "zero_area_faces": sum(f.calc_area() < 1e-10 for f in bm.faces),
              "volume_mm3": round(bm.calc_volume(), 3)}
    bm.to_mesh(o.data)
    bm.free()
    if result["components"] != 1 or result["nonmanifold_edges"] or result["zero_area_faces"]:
        raise AssertionError((o.name, result))
    assert result["volume_mm3"] > 0, (o.name, result)
    return result


def lathe(name, profile):
    n = 96
    vs = [(r * math.cos(2 * math.pi * j / n), r * math.sin(2 * math.pi * j / n), z)
          for z, r in profile for j in range(n)]
    fs = [(k*n+j, k*n+(j+1)%n, (k+1)*n+(j+1)%n, (k+1)*n+j)
          for k in range(len(profile)-1) for j in range(n)]
    fs += [tuple(reversed(range(n))), tuple((len(profile)-1)*n+j for j in range(n))]
    data = bpy.data.meshes.new(name)
    data.from_pydata(vs, [], fs)
    data.update()
    o = bpy.data.objects.new(name, data)
    scene.collection.objects.link(o)
    return o


def material(name, color):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    return m


parts = {}
report = {"printer": "Bambu Lab A1 mini", "nozzle_mm": .4, "material": "Generic PETG",
          "assembled_height_mm": 200, "shell_design_mm": 1.4, "pipe_diameter_mm": 1.2,
          "pin_diameter_mm": 2, "pin_radial_clearance_mm": .15,
          "physical_fit_tested": False, "slicer_tested": False, "parts": {}}
steel = material("Shell / PETG", (.48, .55, .61))
blue = material("Interior / optional paint", (.06, .36, .52))
orange = material("Payload / optional paint", (.75, .32, .07))

for stage, window, connectors in (("SuperHeavy", (12, 115), (14, 112)),
                                   ("Starship", (125, 192), (126.8, 171))):
    body = bpy.data.objects["PRINT_" + stage]
    if stage == "SuperHeavy":
        cavity = cylinder("Tank cavity", 6, 103, (0, 0, 64))
    else:
        profile = [(125, 6), (177, 6)] + [(177+23*i/36, max(.05, .16+7.24*math.cos(i/36*math.pi/2)-1.4)) for i in range(1, 29)]
        cavity = lathe("Tank and payload cavity", profile)
    boolean(body, cavity)
    cover = duplicate(body, stage + "_Cover")
    low, high = window
    boolean(cover, box("Front door", (0, -20.575, (low+high)/2), (80, 38.85, high-low-.30)), "INTERSECT")
    boolean(body, box("Front opening", (0, -20.5, (low+high)/2), (80, 39, high-low)))
    rear_bits, front_bits = [body], [cover]
    for z in connectors:
        rear_bits.append(box("Rear mounting bridge", (0, .35, z), (13.7, 2.7, 3.6)))
        beam = cylinder("Front mounting bridge", 7.32, 3.6, (0, 0, z))
        beam_low, beam_high = max(z-1.8, low+.15), min(z+1.8, high-.15)
        boolean(beam, box("Door bridge clip", (0, -20.575, (beam_low+beam_high)/2),
                          (80, 38.85, beam_high-beam_low)), "INTERSECT")
        front_bits.append(beam)
        for x in (-4, 4):
            front_bits.append(cylinder("Door locating pin", 1, 3.1, (x, -.15, z), "Y"))
    # Flat glue lands receive the separately printed flat-backed inserts.
    for z in ((22, 101) if stage == "SuperHeavy" else (135, 162, 181)):
        rear_bits.append(box("Interior glue land", (0, 4.65, z), (3.5, 2.9, 3)))
    body = union(rear_bits, stage + "_Rear")
    cover = union(front_bits, stage + "_Cover")
    for z in connectors:
        for x in (-4, 4):
            boolean(body, cylinder("Door socket", 1.15, 4, (x, .35, z), "Y"))
    body = union([body], stage + "_Rear")
    parts[body.name], parts[cover.name] = body, cover
    for o in (body, cover):
        o.data.materials.clear()
        o.data.materials.append(steel)
        report["parts"][o.name] = audit(o)
        print("PRINT_PART", o.name, report["parts"][o.name], flush=True)

# Reuse the four updated animation tank envelopes, adapting width and print backs.
with bpy.data.libraries.load(str(ANIMATION), link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.startswith("TANK |")]
tanks = {}
for o in dst.objects:
    if o:
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
        scene.collection.objects.link(o)
        for v in o.data.vertices:
            v.co *= 1000
            v.co.x *= .71
            v.co.y *= .71
        stage = "SuperHeavy" if "SuperHeavy" in o.name else "Starship"
        if stage == "Starship":
            # Leave room above the strengthened lower mounting bridge.
            for v in o.data.vertices:
                v.co.z = 129 + (v.co.z-128) * 40/41
        tanks.setdefault(stage, []).append(o)
for stage, objects in tanks.items():
    low, high = (16, 109) if stage == "SuperHeavy" else (129, 169)
    objects.append(box("Tank backbone", (0, 2.6, (low+high)/2), (2.4, 1.2, high-low)))
    for x, end in ((-4.6, 75 if stage == "SuperHeavy" else 149), (4.6, high)):
        objects.append(cylinder("Thickened feed pipe", .6, end-low-3, (x, -1.5, (end+low+3)/2)))
    core = union(objects, stage + "_Interior")
    boolean(core, box("Flat print back", (0, 20, (low+high)/2), (50, 33.6, high-low+10)))
    core.data.materials.clear()
    core.data.materials.append(blue)
    parts[core.name] = core
    report["parts"][core.name] = audit(core)

payload = union([box("Payload back", (0, 2.6, 180.5), (2.4, 1.2, 13)),
                 cylinder("Illustrative payload", 2.6, 10, (0, 0, 179.5)),
                 box("Payload panel left", (-3.5, 0, 179.5), (1.4, 3.8, 10)),
                 box("Payload panel right", (3.5, 0, 179.5), (1.4, 3.8, 10)),
                 box("Payload cross support", (0, 1.7, 179.5), (7.5, 1.4, 2))], "Starship_Payload")
boolean(payload, box("Payload flat back", (0, 20, 180), (30, 33.6, 30)))
payload.data.materials.clear()
payload.data.materials.append(orange)
parts[payload.name] = payload
parts["Base"] = bpy.data.objects["PRINT_Base"]
parts["Base"].name = "Base"

# A small socket coupon in the same standing orientation as the doors.
coupon_bits = [box("Coupon base", (0, 0, 1), (22, 8, 2))]
for x in (-7, 0, 7):
    coupon_bits.append(box("Socket coupon wall", (x, .35, 4), (4, 2.7, 6)))
coupon = union(coupon_bits, "Fit_Sockets")
for x, clearance in ((-7, .10), (0, .15), (7, .20)):
    boolean(coupon, cylinder("Socket coupon hole", 1+clearance, 4, (x, .35, 4), "Y"))
pin = union([box("Pin coupon foot", (0, -4, 1), (8, 6, 2)),
             box("Pin coupon wall", (0, -2.35, 4), (4, 2.4, 6)),
             cylinder("Pin coupon", 1, 3.1, (0, -.15, 4), "Y")], "Fit_Pin")
parts["Fit_Sockets"], parts["Fit_Pin"] = coupon, pin

# Export individual grounded pieces. Interior flat backs face the bed.
for name, o in parts.items():
    report["parts"][name] = audit(o)
    copy = duplicate(o, "Export " + name)
    copy.hide_render = copy.hide_viewport = False
    copy.hide_set(False)
    if name.endswith(("_Interior", "_Payload")):
        copy.data.transform(Matrix.Rotation(-math.pi/2, 4, "X"))
    low = [min(v.co[i] for v in copy.data.vertices) for i in range(3)]
    high = [max(v.co[i] for v in copy.data.vertices) for i in range(3)]
    size = [round(high[i]-low[i], 3) for i in range(3)]
    for v in copy.data.vertices:
        v.co -= Vector(((high[0]+low[0])/2, (high[1]+low[1])/2, low[2]))
    assert max(size) < 170, (name, size)
    audit(copy)  # Validate after rotation/translation at STL's float precision.
    active(copy)
    bpy.ops.wm.stl_export(filepath=str(OUT / (name + ".stl")), export_selected_objects=True,
                          apply_modifiers=True, global_scale=1, use_scene_unit=False)
    report["parts"][name]["print_dimensions_mm"] = size
    bpy.data.objects.remove(copy, do_unlink=True)

# Only the new parts remain in the editable assembly. Units are metres on disk.
for o in list(scene.objects):
    if o not in parts.values():
        bpy.data.objects.remove(o, do_unlink=True)
for o in parts.values():
    o.data.transform(Matrix.Scale(.001, 4))
    for p in o.data.polygons:
        p.use_smooth = True
    o["assembly_note"] = "Front cover pulls forward. Glue flat-backed interior inserts to rear lands. Test PETG fit coupon first."
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "MILLIMETERS"
scene.unit_settings.scale_length = 1
# Park coupons separately; retain assembled model transforms.
parts["Fit_Pin"].location.x = .05
parts["Fit_Sockets"].location.x = .075
scene["README"] = "Use the A1 mini 4-plate Bambu project to print. Remove front covers along -Y to inspect interiors. Print coupon first."
scene["Nozzle / material"] = "0.4 mm / PETG"
scene["Source"] = "Existing separable print exterior + animation tank envelopes; earlier files preserved."
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Starship_Opening_Print.blend"))
assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in before.items())
report["source_files_unchanged"] = before
report["blender"] = bpy.app.version_string
(OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
print("PRINT_A1MINI_COMPLETE", json.dumps(report), flush=True)
