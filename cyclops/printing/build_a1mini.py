"""Scale the existing print master to 170 mm for the A1 mini.

Run with Blender --background --python cyclops/printing/build_a1mini.py.
The 200 mm master and game assets remain unchanged.
"""
import hashlib
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "a1mini"
SOURCE = ROOT / "CaveCyclops_Print_200mm.blend"
HEIGHT = 170.0
SCALE = HEIGHT / 200.0


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def mesh_report(obj, millimetres_per_unit):
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    mesh.transform(obj.matrix_world)
    mesh.transform(Matrix.Scale(millimetres_per_unit, 4))
    mesh.verts.ensure_lookup_table()
    low = [min(v.co[i] for v in mesh.verts) for i in range(3)]
    high = [max(v.co[i] for v in mesh.verts) for i in range(3)]
    seen = set()
    components = 0
    for vertex in mesh.verts:
        if vertex.index in seen:
            continue
        components += 1
        seen.add(vertex.index)
        stack = [vertex]
        while stack:
            current = stack.pop()
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other.index not in seen:
                    seen.add(other.index)
                    stack.append(other)
    report = {
        "dimensions_mm": [round(b - a, 4) for a, b in zip(low, high)],
        "bounds_mm": [low, high],
        "vertices": len(mesh.verts),
        "triangles": sum(len(face.verts) - 2 for face in mesh.faces),
        "components": components,
        "boundary_edges": sum(edge.is_boundary for edge in mesh.edges),
        "nonmanifold_edges": sum(not edge.is_manifold for edge in mesh.edges),
        "zero_area_faces": sum(face.calc_area() < 1e-10 for face in mesh.faces),
        "signed_volume_cm3": round(mesh.calc_volume(signed=True) / 1000, 4),
    }
    mesh.free()
    assert report["components"] == 1, report
    assert report["boundary_edges"] == report["nonmanifold_edges"] == report["zero_area_faces"] == 0, report
    assert report["signed_volume_cm3"] > 0, report
    assert abs(report["dimensions_mm"][2] - HEIGHT) < 0.001, report
    assert abs(low[2]) < 0.001 and high[2] <= 180, report
    assert all(dimension < 180 for dimension in report["dimensions_mm"]), report
    return report


protected = [SOURCE, ROOT / "CaveCyclops_200mm_SOLID.stl",
             ROOT / "CaveCyclops_200mm_SOLID.3mf", ROOT.parent / "CaveCyclops.blend"]
original_hashes = {str(path.relative_to(ROOT.parent)): sha256(path) for path in protected}
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
statue = bpy.data.objects["CaveCyclops_PRINT_200mm_SOLID"]
statue.name = "CaveCyclops_PRINT_170mm_A1mini"
statue.data.transform(Matrix.Scale(SCALE, 4))
statue.data.update()
report = mesh_report(statue, 1000)
report.update(
    purpose="170 mm one-piece A1 mini / 0.4 mm nozzle / PETG print",
    source_file="../" + SOURCE.name,
    source_sha256=sha256(SOURCE),
    scale_from_200mm=SCALE,
    nominal_scaled_skirt_thickness_mm=round(1.595 * SCALE, 3),
    nominal_scaled_belt_tail_diameter_mm=round(1.754 * SCALE, 3),
    full_wall_thickness_certified=False,
    physical_print_tested=False,
    slicer_tested=False,
)

bpy.ops.object.select_all(action="DESELECT")
statue.select_set(True)
bpy.context.view_layer.objects.active = statue
stl = OUT / "CaveCyclops_170mm.stl"
bpy.ops.wm.stl_export(filepath=str(stl), export_selected_objects=True,
                      apply_modifiers=True, global_scale=1000, use_scene_unit=False)
bpy.ops.wm.stl_import(filepath=str(stl))
imported = bpy.context.object
report["stl_roundtrip"] = mesh_report(imported, 1)
assert report["triangles"] == report["stl_roundtrip"]["triangles"]
assert abs(report["signed_volume_cm3"] - report["stl_roundtrip"]["signed_volume_cm3"]) < 0.001
bpy.data.objects.remove(imported, do_unlink=True)
report["stl_sha256"] = sha256(stl)

# Preserve the existing preview composition at the smaller physical scale.
for obj in scene.objects:
    if obj == statue:
        continue
    obj.location *= SCALE
    if obj.type == "LIGHT":
        obj.data.energy *= SCALE ** 2
        obj.data.size *= SCALE
scene.camera = bpy.data.objects["PRINT Hero"]
scene.render.resolution_x = 864
scene.render.resolution_y = 1080
scene.cycles.samples = 32
scene.render.filepath = str(OUT / "preview.png")
bpy.ops.render.render(write_still=True)

report["preserved_sources_sha256"] = original_hashes
report["sources_unchanged"] = all(
    sha256(path) == original_hashes[str(path.relative_to(ROOT.parent))] for path in protected
)
assert report["sources_unchanged"]
(OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
print("A1MINI_GEOMETRY_VALIDATED", json.dumps(report), flush=True)
