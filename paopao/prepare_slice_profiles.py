"""Resolve bundled Bambu presets, including inheritance and machine G-code."""
import json
from pathlib import Path
root=Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL')
out=Path(__file__).resolve().parent/'printing'/'profiles'
out.mkdir(exist_ok=True)
def resolve(category,name):
    d=json.loads((root/category/(name+'.json')).read_text());v={}
    if d.get('inherits'):v.update(resolve(category,d['inherits']))
    for inc in d.get('include',[]):v.update(resolve(category,inc))
    v.update(d);v.pop('inherits',None);v.pop('include',None);return v
specs=[('machine','Bambu Lab A1 mini 0.4 nozzle'),('process','0.16mm High Quality @BBL A1M'),('filament','Generic PLA @BBL A1M')]
for cat,name in specs:
    d=resolve(cat,name)
    if cat=='process':d.update(wall_loops='3',sparse_infill_density='15%',enable_support='0',brim_type='no_brim',brim_width='0')
    if cat=='filament':d['filament_colour']=['#FFD522']
    (out/(cat+'.json')).write_text(json.dumps(d,indent=2))
    print(cat,{'name':d['name'],'keys':len(d),'layer_height':d.get('layer_height'),'density':d.get('filament_density'),'start_gcode_length':len(d.get('machine_start_gcode',''))})
