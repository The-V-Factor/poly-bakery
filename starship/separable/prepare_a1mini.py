"""Build a four-plate A1 mini / 0.4 mm / PETG Bambu Studio project.

Uses bundled factory presets, never the user's printer/account configuration.
Run with ordinary Python after build_print_a1mini.py. No printer is contacted.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import shutil
import hashlib
import struct
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "printing" / "a1mini"
APP = Path("/Applications/BambuStudio.app/Contents")
PRESETS = APP / "Resources/profiles/BBL"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--slice", action="store_true", help="also slice all plates for verification")
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


with tempfile.TemporaryDirectory(prefix="starship-a1mini-") as scratch:
    tmp = Path(scratch)
    settings = []
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
        settings.append(path)
    plates = []
    names = [("01 - Fit test first", ["Fit_Pin", "Fit_Sockets"]),
             ("02 - Starship", ["Starship_Rear", "Starship_Cover", "Starship_Interior", "Starship_Payload"]),
             ("03 - Super Heavy", ["SuperHeavy_Rear", "SuperHeavy_Cover", "SuperHeavy_Interior"]),
             ("04 - Base", ["Base"])]
    for title, parts in names:
        plates.append({"plate_name": title, "need_arrange": True,
                       "objects": [{"path": str(OUT / (name + ".stl")), "count": 1, "filaments": [1]}
                                   for name in parts]})
    assemble = tmp / "plates.json"
    assemble.write_text(json.dumps({"plates": plates}, indent=2))
    filename = "Starship_A1mini_PETG_4plates.3mf"
    command = [str(APP / "MacOS/BambuStudio"), "--datadir", str(tmp / "user"), "--debug", "3",
               "--load-settings", str(settings[0]) + ";" + str(settings[1]),
               "--load-filaments", str(settings[2]), "--load-assemble-list", str(assemble),
               "--arrange", "1", "--orient", "0", "--ensure-on-bed", "--outputdir", str(tmp),
               "--export-3mf", filename]
    if args.slice:
        command += ["--slice", "0"]
    result = subprocess.run(command, cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    Path(tempfile.gettempdir(), "poly-bakery-a1mini-slicer.log").write_text(result.stdout)
    if result.returncode:
        print(result.stdout[-6000:])
    result.check_returncode()
    with zipfile.ZipFile(tmp / filename) as project:
        settings = json.loads(project.read("Metadata/project_settings.config"))
        assert settings["printer_model"] == "Bambu Lab A1 mini"
        assert settings["nozzle_diameter"] == ["0.4"]
        assert settings["filament_type"] == ["PETG"]
        assert settings["layer_height"] == "0.16"
        model = ET.fromstring(project.read("Metadata/model_settings.config"))
        assert [len(p.findall("model_instance")) for p in model.findall("plate")] == [2, 4, 3, 1]
        for part in model.findall("object/part"):
            metadata = {m.get("key"): m.get("value") for m in part.findall("metadata")}
            stats = part.find("mesh_stat").attrib
            assert all(int(value) == 0 for key, value in stats.items() if key != "face_count"), stats
            with (OUT / metadata["source_file"]).open("rb") as stl:
                stl.seek(80)
                assert struct.unpack("<I", stl.read(4))[0] == int(stats["face_count"])
        if args.slice:
            sliced = ET.fromstring(project.read("Metadata/slice_info.config"))
            plate_results = []
            for i, plate in enumerate(sliced.findall("plate"), 1):
                info = {m.get("key"): m.get("value") for m in plate.findall("metadata")}
                assert info["outside"] == "false"
                assert all(o.get("skipped") == "false" for o in plate.findall("object"))
                assert len(project.read(f"Metadata/plate_{i}.gcode")) > 10000
                bounds = json.loads(project.read(f"Metadata/plate_{i}.json"))["bbox_all"]
                assert 0 <= bounds[0] < bounds[2] <= 180 and 0 <= bounds[1] < bounds[3] <= 180
                warnings = sorted({w.get("msg") for w in plate.findall("warning")})
                assert set(warnings) <= {"not_support_traditional_timelapse"}, warnings
                plate_results.append({"plate": i, "name": names[i-1][0],
                                      "objects": len(plate.findall("object")), "first_layer_bounds_mm": bounds,
                                      "predicted_seconds": int(info["prediction"]),
                                      "filament_grams": float(info["weight"]), "warnings": warnings})
                (OUT / f"plate_{i}.png").write_bytes(project.read(f"Metadata/plate_{i}.png"))
            assert len(plate_results) == 4
            report = json.loads((OUT / "validation.json").read_text())
            report["slicer_tested"] = True
            report["slicer"] = {"version": "Bambu Studio " + sliced.find("header/header_item[@key='X-BBL-Client-Version']").get("value"),
                                "plates": plate_results, "automatic_mesh_repairs": 0,
                                "project_sha256": hashlib.sha256((tmp / filename).read_bytes()).hexdigest()}
            (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(plate_results, indent=2))
    shutil.copy2(tmp / filename, OUT / filename)
    print("A1MINI_PROJECT", OUT / "Starship_A1mini_PETG_4plates.3mf")
