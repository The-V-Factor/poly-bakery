"""Create the 170 mm Cyclops A1 mini / 0.4 mm / PETG Bambu project.

Run after exporting the 170 mm STL, with --slice to verify the toolpaths.
Only bundled factory presets and a temporary user directory are used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

OUT = Path(__file__).resolve().parent / "a1mini"
APP = Path("/Applications/BambuStudio.app/Contents")
PRESETS = APP / "Resources/profiles/BBL"
STL = OUT / "CaveCyclops_170mm.stl"
FILENAME = "CaveCyclops_A1mini_PETG_170mm.3mf"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--slice", action="store_true", help="also slice the plate for verification")
args = parser.parse_args()


def resolve(category, name):
    data = json.loads((PRESETS / category / (name + ".json")).read_text())
    value = resolve(category, data["inherits"]) if data.get("inherits") else {}
    for include in data.get("include", []):
        value.update(resolve(category, include))
    value.update(data)
    value.pop("inherits", None)
    value.pop("include", None)
    return value


report = json.loads((OUT / "validation.json").read_text())
dimensions = report["dimensions_mm"]
assert len(dimensions) == 3 and all(0 < d <= 180 for d in dimensions), dimensions
assert abs(dimensions[2] - 170) < .001, dimensions
with STL.open("rb") as source:
    source.seek(80)
    triangle_count = struct.unpack("<I", source.read(4))[0]
assert STL.stat().st_size == 84 + triangle_count * 50

with tempfile.TemporaryDirectory(prefix="cyclops-a1mini-") as scratch:
    tmp = Path(scratch)
    presets = []
    for category, name in (("machine", "Bambu Lab A1 mini 0.4 nozzle"),
                           ("process", "0.16mm Optimal @BBL A1M"),
                           ("filament", "Generic PETG @BBL A1M")):
        value = resolve(category, name)
        if category == "process":
            value.update(wall_loops="3", sparse_infill_density="15%", enable_support="1",
                         support_type="tree(auto)", support_top_z_distance="0.24",
                         support_bottom_z_distance="0.24", support_on_build_plate_only="0",
                         brim_type="outer_only", brim_width="5", print_sequence="by layer",
                         enable_prime_tower="0", curr_bed_type="Textured PEI Plate")
        if category == "filament":
            value["filament_colour"] = ["#909BA3"]
        path = tmp / (category + ".json")
        path.write_text(json.dumps(value, indent=2))
        presets.append(path)
    assemble = tmp / "plate.json"
    assemble.write_text(json.dumps({"plates": [{
        "plate_name": "01 - Cave Cyclops 170 mm", "need_arrange": True,
        "objects": [{"path": str(STL), "count": 1, "filaments": [1]}],
    }]}, indent=2))
    command = [str(APP / "MacOS/BambuStudio"), "--datadir", str(tmp / "user"), "--debug", "3",
               "--load-settings", str(presets[0]) + ";" + str(presets[1]),
               "--load-filaments", str(presets[2]), "--load-assemble-list", str(assemble),
               "--arrange", "1", "--orient", "0", "--ensure-on-bed", "--outputdir", str(tmp),
               "--export-3mf", FILENAME]
    if args.slice:
        command += ["--slice", "0"]
    result = subprocess.run(command, cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    Path(tempfile.gettempdir(), "poly-bakery-cyclops-a1mini-slicer.log").write_text(result.stdout)
    if result.returncode:
        print(result.stdout[-6000:])
    result.check_returncode()

    with zipfile.ZipFile(tmp / FILENAME) as project:
        settings = json.loads(project.read("Metadata/project_settings.config"))
        expected = {"printer_model": "Bambu Lab A1 mini", "nozzle_diameter": ["0.4"],
                    "filament_type": ["PETG"], "layer_height": "0.16", "wall_loops": "3",
                    "sparse_infill_density": "15%", "enable_support": "1", "support_type": "tree(auto)",
                    "support_top_z_distance": "0.24", "support_bottom_z_distance": "0.24",
                    "support_on_build_plate_only": "0", "brim_type": "outer_only", "brim_width": "5",
                    "print_sequence": "by layer", "enable_prime_tower": "0",
                    "curr_bed_type": "Textured PEI Plate"}
        assert all(settings[k] == v for k, v in expected.items()), {k: settings[k] for k in expected}
        model = ET.fromstring(project.read("Metadata/model_settings.config"))
        assert [len(p.findall("model_instance")) for p in model.findall("plate")] == [1]
        parts = model.findall("object/part")
        assert len(parts) == 1
        stats = parts[0].find("mesh_stat").attrib
        assert int(stats["face_count"]) == triangle_count
        assert all(int(v) == 0 for k, v in stats.items() if k != "face_count"), stats
        report["slicer_tested"] = args.slice
        report["slicer"] = {
            "automatic_mesh_repairs": 0,
            "project_sha256": hashlib.sha256((tmp / FILENAME).read_bytes()).hexdigest(),
            "input_stl_sha256": hashlib.sha256(STL.read_bytes()).hexdigest(),
            "actual_settings": {k: settings[k] for k in list(expected) + [
                "initial_layer_print_height", "nozzle_temperature", "textured_plate_temp",
                "support_threshold_angle", "support_object_xy_distance", "filament_max_volumetric_speed"]},
        }
        if args.slice:
            sliced = ET.fromstring(project.read("Metadata/slice_info.config"))
            plates = sliced.findall("plate")
            assert len(plates) == 1
            plate = plates[0]
            info = {m.get("key"): m.get("value") for m in plate.findall("metadata")}
            objects = plate.findall("object")
            assert len(objects) == 1 and all(o.get("skipped") == "false" for o in objects)
            assert info["outside"] == "false"
            gcode = project.read("Metadata/plate_1.gcode").decode()
            assert len(gcode) > 10000
            heights = [float(z) for z in re.findall(r"^; Z_HEIGHT: ([\d.]+)$", gcode, re.MULTILINE)]
            assert heights and 0 < max(heights) <= 180, heights[-5:]
            assert abs(max(heights) - dimensions[2]) <= .2, (max(heights), dimensions)
            bounds = json.loads(project.read("Metadata/plate_1.json"))["bbox_all"]
            assert 0 <= bounds[0] < bounds[2] <= 180 and 0 <= bounds[1] < bounds[3] <= 180, bounds
            warnings = sorted({w.get("msg") for w in plate.findall("warning")})
            assert set(warnings) <= {"not_support_traditional_timelapse"}, warnings
            report["slicer"].update({
                "version": "Bambu Studio " + sliced.find("header/header_item[@key='X-BBL-Client-Version']").get("value"),
                "plates": 1, "objects": 1, "first_layer_bounds_mm": bounds,
                "maximum_layer_z_mm": max(heights), "layer_count": len(heights),
                "predicted_seconds": int(info["prediction"]), "filament_grams": float(info["weight"]),
                "support_used": info["support_used"] == "true", "warnings": warnings,
            })
            (OUT / "plate_1.png").write_bytes(project.read("Metadata/plate_1.png"))
    shutil.copy2(tmp / FILENAME, OUT / FILENAME)
    (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["slicer"], indent=2))
    print("A1MINI_PROJECT", OUT / FILENAME)
