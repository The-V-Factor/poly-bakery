"""Check saved STL geometry and the actual cover pin/socket clearances."""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = Path(__file__).resolve().parent / "printing" / "a1mini"
report = json.loads((OUT / "validation.json").read_text())
bpy.ops.wm.open_mainfile(filepath=str(OUT / "Starship_Opening_Print.blend"))
clearances = {}
for stage, heights in (("Starship", (126.8, 171)), ("SuperHeavy", (14, 112))):
    trees = []
    for suffix in ("Rear", "Cover"):
        bm = bmesh.new()
        bm.from_mesh(bpy.data.objects[stage + "_" + suffix].data)
        for v in bm.verts:
            v.co *= 1000
        trees.append(BVHTree.FromBMesh(bm))
        bm.free()
    intersections = len(trees[0].overlap(trees[1]))
    assert intersections == 0, (stage, "cover intersects rear shell", intersections)
    core = bpy.data.objects[stage + "_Interior"]
    core_low = min(v.co.z for v in core.data.vertices) * 1000
    core_high = max(v.co.z for v in core.data.vertices) * 1000
    assert core_low > heights[0]+1.8 and core_high < heights[1]-1.8, (stage, core_low, core_high)
    gaps = []
    for z in heights:
        for x in (-4, 4):
            for y in (-.5, 0, .8):
                for angle in range(0, 360, 30):
                    a = math.radians(angle)
                    origin, direction = Vector((x, y, z)), Vector((math.cos(a), 0, math.sin(a)))
                    hits = [tree.ray_cast(origin, direction, 2)[3] for tree in trees]
                    assert all(hit is not None for hit in hits), (stage, x, y, z, angle, hits)
                    gaps.append(hits[0] - hits[1])
    assert min(gaps) > .05 and max(gaps) < .3, (stage, min(gaps), max(gaps))
    clearances[stage] = {"sample_count": len(gaps), "minimum_mm": round(min(gaps), 4),
                         "maximum_mm": round(max(gaps), 4), "cover_rear_intersections": intersections,
                         "tank_to_lower_bridge_mm": round(core_low-heights[0]-1.8, 4),
                         "tank_to_upper_bridge_mm": round(heights[1]-1.8-core_high, 4)}
    print("COVER_CLEARANCE", stage, clearances[stage], flush=True)
report["measured_cover_radial_clearance"] = clearances

# Reimport the files that the slicer receives, at their millimetre coordinates.
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for name, part in report["parts"].items():
    bpy.ops.wm.stl_import(filepath=str(OUT / (name + ".stl")), global_scale=1)
    o = bpy.context.object
    bm = bmesh.new()
    bm.from_mesh(o.data)
    result = {"nonmanifold_edges": sum(not e.is_manifold for e in bm.edges),
              "zero_area_faces": sum(f.calc_area() < 1e-10 for f in bm.faces),
              "volume_mm3": round(bm.calc_volume(), 3), "triangles": len(bm.faces)}
    assert not result["nonmanifold_edges"] and not result["zero_area_faces"], (name, result)
    assert result["volume_mm3"] > 0, (name, result)
    low = [min(v.co[i] for v in bm.verts) for i in range(3)]
    high = [max(v.co[i] for v in bm.verts) for i in range(3)]
    assert abs(low[2]) < .001, (name, low)
    assert all(abs(high[i]-low[i]-part["print_dimensions_mm"][i]) < .002 for i in range(3))
    bm.free()
    bpy.data.objects.remove(o, do_unlink=True)
    part["stl_roundtrip"] = result
    print("STL_VERIFIED", name, result, flush=True)
(OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
