"""Derive separable Starship, Super Heavy and base; do not overwrite V1.

All construction uses mm. The coupling is a scale-model D sleeve with 0.30 mm
nominal radial/flat clearance, not a flight separation mechanism.
"""
import os,sys,json,math,zipfile,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
original_hash=hashlib.sha256((PARENT/'Starship_FullStack.blend').read_bytes()).hexdigest()
# Reuse only the original builder's geometry definitions; stop before any exports.
prefix=(PARENT/'build_starship.py').read_text().split('# Build and validate the print version')[0]
original_file=__file__
__file__=str(PARENT/'build_starship.py')
exec(compile(prefix,str(PARENT/'build_starship.py'),'exec'),globals())
__file__=original_file
ROOT=str(HERE)
for folder in ('printing','renders'):os.makedirs(os.path.join(ROOT,folder),exist_ok=True)
from mathutils import Matrix

def remove(o):
    if o in printparts:printparts.remove(o)
    if o in displayparts:displayparts.remove(o)
    bpy.data.objects.remove(o,do_unlink=True)

# Remove the V1 opaque interstage core, central stand and incomplete print engines.
for o in list(bpy.data.objects):
    if any(s in o.name for s in ('Hot-stage solid core','Axial display mount','PRINT nozzle relief','Super Heavy engine bell')):remove(o)
    elif 'Hot-stage ring' in o.name and o.location.z>120:o.location.z-=.45
    elif 'stage' in o.name.lower() and 'rib' in o.name.lower():o.location.z-=.20

def outward(o):
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(o.data);bm.free()

def boolean(o,tool,operation):
    m=o.modifiers.new('Manufactured interface','BOOLEAN');m.operation=operation;m.solver='EXACT';m.object=tool
    apply(o,m);remove(tool)

def ring(name,profile,mat,printing=False,n=128):
    # Closed cross-section lathe, unlike a capped solid-cylinder profile.
    vs=[];fs=[]
    for z,r in profile:
        for j in range(n):a=2*pi*j/n;vs.append((r*cos(a),r*sin(a),z))
    for k in range(len(profile)):
        kk=(k+1)%len(profile)
        for j in range(n):jj=(j+1)%n;fs.append((k*n+j,k*n+jj,kk*n+jj,kk*n+j))
    o=mesh(name,vs,fs,mat,printing);outward(o);return o

def d_cylinder(name,radius,flat_x,zlow,zhigh,printing=False):
    c=cylinder(name,radius,zhigh-zlow,(zlow+zhigh)/2,resin,printing=printing,vertices=128)
    # Retain x <= flat_x, forming a rotationally keyed circular sleeve.
    cut=box('D profile cutter',(flat_x+20,0,(zlow+zhigh)/2),(40,40,zhigh-zlow+4),resin,printing)
    boolean(c,cut,'DIFFERENCE');return c

def bell(name,x,y,top,radius,length,printing=False):
    # Tiny printing bells have a blind shallow cup, avoiding deep resin traps.
    wall=.36 if printing else .10
    lip_inner=max(.21,radius-wall)
    cup=min(.85,length*.30) if printing else length*.65
    prof=[(top,radius*.48),(top-length*.25,radius*.52),
          (top-length*.68,radius*.80),(top-length,radius),
          (top-length,lip_inner),(top-length+cup,max(.14,lip_inner*.45))]
    o=lathe(name,prof,resin if printing else engine,printing,n=48 if printing else 64)
    o.location.x=x;o.location.y=y;outward(o)
    o['component']='engine';o['printing_bell_wall_mm']=wall if printing else 0
    return o

engine_manifest=[]
for printing in (False,True):
    tag='PRINT ' if printing else ''
    mat=resin if printing else steel
    hull=next(o for o in (printparts if printing else displayparts) if o.name.startswith(tag+'Starship |'))
    # Real engine bay beneath the ship; its roof anchors all six engines.
    cutter=cylinder('Upper stage bay cutter',5.12,10,119.0,resin,printing=printing)
    boolean(hull,cutter,'DIFFERENCE') # bay ceiling at z = 124.0
    sleeve=d_cylinder(tag+'SHIP keyed male sleeve',6.30,6.00,118.40,122.80,printing)
    bore=cylinder('Sleeve engine clearance',5.30,6.5,120.4,resin,printing=printing)
    boolean(sleeve,bore,'DIFFERENCE')
    sleeve.data.materials.clear();sleeve.data.materials.append(mat)
    collar=cylinder(tag+'BOOSTER hot-stage receiver',7.50,4.0,119.50,mat,printing=printing)
    socket=d_cylinder('D socket cutter',6.60,6.30,117.80,122.30,printing)
    boolean(collar,socket,'DIFFERENCE')
    # The existing booster deck ends at 117.9; recess its central floor slightly.
    booster=next(o for o in (printparts if printing else displayparts) if o.name.startswith(tag+'Super Heavy |'))
    socket=d_cylinder('Booster clearance cutter',6.60,6.30,117.55,122.30,printing)
    boolean(booster,socket,'DIFFERENCE')
    # Upper stage: 3 larger outer RVac + 3 smaller inner sea-level bells.
    for kind,count,radial,radius,length,offset in (
        ('RVac',3,3.60,1.45,5.30,0),
        ('SeaLevel',3,1.45,.92,4.00,pi/3)):
        for j in range(count):
            a=offset+2*pi*j/count;x=radial*cos(a);y=radial*sin(a)
            o=bell(tag+f'SHIP {kind} {j+1:02d}',x,y,124.5,radius,length,printing)
            if not printing:engine_manifest.append({'stage':'Starship','type':kind,'position_mm':[x,y,124.5-length]})
    # Booster: 20 outer + 10 middle + 3 central engines, all present in both versions.
    number=0
    for count,radial,radius in ((20,5.63,.74),(10,3.42,.81),(3,1.10,.87)):
        for j in range(count):
            number+=1;a=2*pi*j/count+.12;x=radial*cos(a);y=radial*sin(a)
            bell(tag+f'BOOSTER Raptor {number:02d}',x,y,10.7,radius,2.9,printing)
            if not printing:engine_manifest.append({'stage':'Super Heavy','type':'SeaLevel','position_mm':[x,y,7.8]})
    # A removable launch collar supports the booster perimeter, not its engines.
    support=ring(tag+'BASE removable launch cradle',[(4.5,9.5),(13.6,9.5),(13.6,7.7),(9.6,7.7),(9.6,6.7),(4.5,6.7)],resin if printing else base_mat,printing)
    if not printing:
        for c in list(support.users_collection):c.objects.unlink(support)
        stand.objects.link(support)

def part_group(o):
    n=o.name
    if 'Circular base' in n or 'BASE ' in n:return 'Base'
    if any(s in n for s in ('Starship |','SHIP ','Ship weld','Aft flap','Forward flap','thermal surface seam','TPS |')):return 'Starship'
    return 'SuperHeavy'

def audit(o):
    bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();seen=set();groups=[]
    for v in bm.verts:
        if v.index in seen:continue
        todo=[v];seen.add(v.index);count=0
        while todo:
            q=todo.pop();count+=1
            for e in q.link_edges:
                v2=e.other_vert(q)
                if v2.index not in seen:seen.add(v2.index);todo.append(v2)
        groups.append(count)
    r={'connected_components':len(groups),'component_vertex_counts':groups,'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-10 for f in bm.faces),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'volume_cm3':round(bm.calc_volume(signed=True)/1000,5)}
    bm.free();return r

def merge_group(objects,name):
    activate(objects[0])
    for o in objects:o.select_set(True)
    bpy.ops.object.join();o=bpy.context.object;o.name=name
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    m=o.modifiers.new('Closed print union','REMESH');m.mode='VOXEL';m.voxel_size=.065;apply(o,m)
    m=o.modifiers.new('Light edge smoothing','SMOOTH');m.factor=.20;m.iterations=1;apply(o,m)
    m=o.modifiers.new('Print polygon budget','DECIMATE');m.ratio=min(1,380000/sum(len(p.vertices)-2 for p in o.data.polygons));apply(o,m)
    m=o.modifiers.new('Explicit triangles','TRIANGULATE');apply(o,m)
    outward(o)
    for f in o.data.polygons:f.use_smooth=True
    o.data.materials.clear();o.data.materials.append(resin)
    return o

groups={name:[o for o in printparts if part_group(o)==name] for name in ('Starship','SuperHeavy','Base')}
printed={};report={'engines':{'Starship':{'vacuum':3,'sea_level':3},'SuperHeavy':33},'engine_manifest':engine_manifest,
    'interface':{'type':'gravity fit D-shaped annular sleeve','male_outer_radius_mm':6.30,'female_inner_radius_mm':6.60,'male_flat_x_mm':6.00,'female_flat_x_mm':6.30,'nominal_radial_clearance_mm':.30,'sleeve_inner_radius_mm':5.30,'vacuum_engine_outer_envelope_mm':5.05,'nominal_engine_side_clearance_mm':.25,'male_bottom_z_mm':118.40,'receiver_floor_z_mm':117.90,'minimum_nominal_floor_clearance_mm':.50,'insertion_depth_mm':3.10},
    'base_fit':{'receiver_radius_mm':7.70,'booster_radius_mm':7.40,'nominal_radial_clearance_mm':.30,'engine_tips_z_mm':7.8,'base_top_z_mm':5.0,'nominal_engine_bottom_clearance_mm':2.8},
    'slicer_tested':False,'physical_fit_tested':False,'full_wall_thickness_certified':False,'parts':{}}

def export_3mf(o,path):
    me=o.data;me.calc_loop_triangles()
    vertices=''.join(f'<vertex x="{v.co.x:.6f}" y="{v.co.y:.6f}" z="{v.co.z:.6f}"/>' for v in me.vertices)
    triangles=''.join(f'<triangle v1="{t.vertices[0]}" v2="{t.vertices[1]}" v3="{t.vertices[2]}"/>' for t in me.loop_triangles)
    xml='<?xml version="1.0"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1" type="model" name="'+o.name+'"><mesh><vertices>'+vertices+'</vertices><triangles>'+triangles+'</triangles></mesh></object></resources><build><item objectid="1"/></build></model>'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model',xml)

def export_piece(o,name):
    # Ground each printable part individually; retain assembled coordinates in blend.
    minz=min(v.co.z for v in o.data.vertices)
    for v in o.data.vertices:v.co.z-=minz
    activate(o);path=os.path.join(ROOT,'printing',name+'.stl')
    bpy.ops.wm.stl_export(filepath=path,export_selected_objects=True,apply_modifiers=True,global_scale=1,use_scene_unit=False)
    export_3mf(o,os.path.join(ROOT,'printing',name+'.3mf'))
    bpy.ops.wm.stl_import(filepath=path);test=bpy.context.object
    r=audit(test);r['height_mm']=round(max(v.co.z for v in test.data.vertices)-min(v.co.z for v in test.data.vertices),3)
    bpy.data.objects.remove(test,do_unlink=True)
    assert r['connected_components']==1 and r['boundary_edges']==r['nonmanifold_edges']==r['zero_area_faces']==0,r
    for v in o.data.vertices:v.co.z+=minz
    return r

for name,objs in groups.items():
    o=merge_group(objs,'PRINT_'+name);printed[name]=o
    r=audit(o);print('PART',name,json.dumps(r),flush=True)
    assert r['connected_components']==1 and r['boundary_edges']==r['nonmanifold_edges']==r['zero_area_faces']==0 and r['volume_cm3']>0,r
    r['stl_roundtrip']=export_piece(o,name)
    report['parts'][name]=r

# Verify sampled engine outlets remain actual open depressions after voxel union.
from mathutils.bvhtree import BVHTree
def outlet_depth_check(o,positions,top_mm,expected):
    bpy.context.view_layer.update();bvh=BVHTree.FromObject(o,bpy.context.evaluated_depsgraph_get());depths=[]
    for x,y,bottom in positions:
        hit,_,_,_=bvh.ray_cast(Vector((x,y,bottom-.8)),Vector((0,0,1)),top_mm-bottom+2)
        assert hit is not None
        depths.append(round(hit.z-bottom,3))
    assert len(depths)==expected and min(depths)>.18,depths
    return depths
report['engine_outlet_depths_mm']={
    'Starship':outlet_depth_check(printed['Starship'],[e['position_mm'] for e in engine_manifest if e['stage']=='Starship'],125,6),
    'SuperHeavy':outlet_depth_check(printed['SuperHeavy'],[e['position_mm'] for e in engine_manifest if e['stage']=='Super Heavy'],11,33)}

# A cheap full-size fitting coupon uses the exact same male/female cross sections.
coupons=[]
for name in ('Male','Female'):
    if name=='Male':
        c=d_cylinder('Fit_Male',6.30,6.00,1.5,5.6,True)
        b=cylinder('Fit base',8.3,1.6,.8,resin,printing=True)
        hole=cylinder('Test sleeve bore',5.30,7,3.0,resin,printing=True)
        boolean(c,hole,'DIFFERENCE')
    else:
        c=cylinder('Fit_Female',8.3,5.5,2.75,resin,printing=True)
        tool=d_cylinder('Fit D cavity',6.60,6.30,1.2,7,True);boolean(c,tool,'DIFFERENCE')
        b=None
    coupons.append(merge_group([c,b] if b else [c],'Fit_'+name))
    report['parts']['Fit_'+name]=export_piece(coupons[-1],'Fit_'+name)

# Ray checks quantify clearances on the actual remeshed D interface.
ship=printed['Starship'];booster=printed['SuperHeavy']
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
sb=BVHTree.FromObject(ship,dg);bb=BVHTree.FromObject(booster,dg)
clearances=[]
for z in (118.7,119.5,120.7):
    for i in range(72):
        a=2*pi*i/72;d=Vector((cos(a),sin(a),0));start=d*6.1;start.z=z
        # Female inner boundary: ray outward from the empty receiver centre.
        fh,_,_,_=bb.ray_cast(Vector((0,0,z)),d,9)
        # Male outer surface: ray inward from outside the sleeve.
        origin=d*7.2;origin.z=z;mh,_,_,_=sb.ray_cast(origin,-d,3)
        if fh is not None and mh is not None:
            clearances.append((fh-mh).dot(d))
report['measured_radial_fit_clearance_mm']={'samples':len(clearances),'minimum':round(min(clearances),3),'maximum':round(max(clearances),3)}
assert min(clearances)>.12,report['measured_radial_fit_clearance_mm']
assert hashlib.sha256((PARENT/'Starship_FullStack.blend').read_bytes()).hexdigest()==original_hash
report['original_display_unchanged']=True
with open(os.path.join(ROOT,'printing','validation.json'),'w') as f:json.dump(report,f,indent=2)
print('VALIDATED',json.dumps({k:v for k,v in report.items() if k not in ('engine_manifest','parts')}),flush=True)

# Remove fitting coupon meshes from the visual scene, retaining exported test files.
for o in coupons:bpy.data.objects.remove(o,do_unlink=True)
# Group all display geometry into three independently movable controllers.
controllers={}
for name in ('Starship','SuperHeavy','Base'):
    c=bpy.data.collections.new('DISPLAY | '+name);scene.collection.children.link(c)
    ctrl=bpy.data.objects.new('MOVE_'+name,None);c.objects.link(ctrl);ctrl.empty_display_size=10;controllers[name]=ctrl
    for o in list(displayparts):
        if o.name not in bpy.data.objects:continue
        group='Base' if stand in o.users_collection else part_group(o)
        if group==name:
            for old in list(o.users_collection):old.objects.unlink(o)
            c.objects.link(o);o.parent=ctrl

# Scale mm geometry and locations into metres for a correct Blender scene.
for o in list(bpy.data.objects):
    if o.type in ('MESH','FONT'):
        o.location*=.001;o.scale*=.001
        if o.type=='MESH':activate(o);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
for ctrl in controllers.values():ctrl.empty_display_size=.01
scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
printcol.hide_viewport=True;printcol.hide_render=True
stage=bpy.data.collections.new('STUDIO');scene.collection.children.link(stage)
def cam(name,loc,target,lens=60):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);stage.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_start=.0001;return o
hero=cam('CAM_Assembled',(.25,-.44,.245),(0,0,.102),75)
exploded=cam('CAM_Separated',(.30,-.48,.27),(0,0,.128),68)
shipcam=cam('CAM_Ship_6_engines',(.030,-.034,.090),(0,0,.122),55)
boostcam=cam('CAM_Booster_33_engines',(.021,-.028,-.027),(0,0,.010),62)
def light(name,loc,target,power,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);stage.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
light('Key',(.12,-.16,.22),(0,0,.1),3,.18)
light('Rim',(-.10,.10,.20),(0,0,.1),4,.16)
light('Engine inspection',(.02,-.08,-.04),(0,0,.04),.6,.08)
world=bpy.data.worlds.new('Separable studio');world.use_nodes=True;scene.world=world
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.07,.09,.13,1);bg.inputs[1].default_value=.35
# No floor in underside views, so the nozzles can be inspected without obstruction.
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-.6
scene.camera=hero
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.clip_start=.0001;a.spaces.active.region_3d.view_distance=.4
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'Starship_Separable.blend'))
scene.render.filepath=os.path.join(ROOT,'renders','01_assembled.png');bpy.ops.render.render(write_still=True)
controllers['Starship'].location.z=.045;controllers['SuperHeavy'].location.z=.012
scene.camera=exploded;scene.render.filepath=os.path.join(ROOT,'renders','02_separated.png');bpy.ops.render.render(write_still=True)
for c in controllers.values():c.location=(0,0,0)
controllers['SuperHeavy'].hide_render=True
# Hide by child collection as hiding an empty alone does not hide its children.
bpy.data.collections['DISPLAY | SuperHeavy'].hide_render=True;bpy.data.collections['DISPLAY | Base'].hide_render=True
scene.camera=shipcam;scene.render.resolution_x=1400;scene.render.resolution_y=1200
scene.render.filepath=os.path.join(ROOT,'renders','03_starship_6_engines.png');bpy.ops.render.render(write_still=True)
bpy.data.collections['DISPLAY | SuperHeavy'].hide_render=False;bpy.data.collections['DISPLAY | Starship'].hide_render=True
scene.camera=boostcam;scene.render.filepath=os.path.join(ROOT,'renders','04_booster_33_engines.png');bpy.ops.render.render(write_still=True)

# Save a clean three-piece print Blender file in assembled position.
for name in controllers:
    c=bpy.data.collections['DISPLAY | '+name]
    for o in list(c.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.collections.remove(c)
printcol.hide_render=False;printcol.hide_viewport=False
scene.camera=hero;scene.render.resolution_x=1200;scene.render.resolution_y=1600
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'printing','Starship_Separable_Print.blend'))
printed['Starship'].location.z=.045;printed['SuperHeavy'].location.z=.012
scene.camera=exploded;scene.render.filepath=os.path.join(ROOT,'renders','05_print_separated.png');bpy.ops.render.render(write_still=True)
print('SEPARABLE_COMPLETE',flush=True)
