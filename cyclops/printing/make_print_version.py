"""Derive a 200 mm static print master without changing the game sources.

Run with Blender --background --python printing/make_print_version.py.
Mesh preparation and export use millimetres; the saved blend uses metres.
"""
import bpy, bmesh, json, math, os, hashlib, zipfile
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from xml.sax.saxutils import escape

OUT=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.dirname(OUT)
SOURCE=os.path.join(ROOT,'CaveCyclops.blend')
source_hash=hashlib.sha256(open(SOURCE,'rb').read()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=SOURCE)
scene=bpy.context.scene;scene.frame_set(1)
rig=bpy.data.objects.get('RIG_CaveCyclops')
if rig:
    rig.animation_data_clear()
    for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get()
source_objects=[o for o in bpy.data.objects if o.type=='MESH' and any(c.name in ('01_CHARACTER','02_ANATOMICAL_DETAILS') for c in o.users_collection)]
body_source=bpy.data.objects['SK_CaveCyclops_Body']
coords=[body_source.matrix_world@v.co for v in body_source.evaluated_get(dg).data.vertices]
zmin=min(v.z for v in coords);zmax=max(v.z for v in coords)
factor=194/(zmax-zmin)
zshift=6-zmin*factor
def pos(p):return Vector((p[0]*factor,p[1]*factor,p[2]*factor+zshift))

coll=bpy.data.collections.new('PRINT | 200 mm solid statue');scene.collection.children.link(coll)
parts=[]
omitted=[]
landmarks={}
for original in source_objects:
    if original.name.startswith(('Eye_single','Nostril')):
        coords=[pos(original.matrix_world@v.co) for v in original.evaluated_get(dg).data.vertices]
        landmarks[original.name]=sum(coords,Vector())/len(coords)
    # Shader-coloured surface inserts are replaced by a single physical surface.
    if original.name.startswith(('Iris_','Mouth closed recess','Nostril','Ear concha','Navel')):
        omitted.append(original.name);continue
    me=bpy.data.meshes.new_from_object(original.evaluated_get(dg),depsgraph=dg)
    me.transform(original.matrix_world)
    for v in me.vertices:v.co=pos(v.co)
    me.materials.clear()
    o=bpy.data.objects.new(original.name+'_PRINT',me);coll.objects.link(o);parts.append(o)

# Remove the loaded source scene from memory only; the original file is untouched.
for o in list(bpy.data.objects):
    if o not in parts:bpy.data.objects.remove(o,do_unlink=True)
for c in list(bpy.data.collections):
    if c!=coll:bpy.data.collections.remove(c)

def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):
    active(o);bpy.ops.object.modifier_apply(modifier=m.name)
def inflate(o,mm):
    o.data.update()
    directions=[v.normal.copy() for v in o.data.vertices]
    for v,n in zip(o.data.vertices,directions):v.co+=n*mm
    o.data.update()

for o in parts:
    if o.name.startswith('Integrated_eyelids'):
        m=o.modifiers.new('Physical eyelid thickness 1.6 mm','SOLIDIFY');m.thickness=1.6;m.offset=0;apply(o,m)
    elif o.name.startswith('Hide_wrap'):inflate(o,.60)
    elif o.name.startswith(('Belt tie','Twisted belt')):inflate(o,.35)
    elif o.name.startswith(('Fingernail','Toenail')):inflate(o,.15)
    elif o.name.startswith('SK_CaveCyclops_Body'):
        o.data.update();normals=[v.normal.copy() for v in o.data.vertices]
        for v,n in zip(o.data.vertices,normals):
            x,y,z=v.co;source_z=(z-zshift)/factor
            # Retain finger separation; strengthen only hands and distal fingers.
            if abs(x)>factor*1.03 and 1.15<source_z<1.94:
                blend=min(1,(1.94-source_z)/.10,(source_z-1.15)/.10)
                v.co+=n*(.22*max(0,blend))

def ellipsoid(name,loc,radii):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,location=loc)
    o=bpy.context.object;o.name=name;o.scale=radii
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    for c in list(o.users_collection):c.objects.unlink(o)
    coll.objects.link(o);parts.append(o);return o

# The source has a few floating nail inserts. Seat each into the actual hand/foot.
body=next(o for o in parts if o.name.startswith('SK_CaveCyclops_Body'))
bpy.context.view_layer.update()
body_bvh=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
nail_adjustments=[]
for o in parts:
    if o.name.startswith(('Fingernail','Toenail')):
        center=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
        hit,n,_,distance=body_bvh.find_nearest(center)
        if distance>.12:
            delta=(hit-center).normalized()*(distance-.12)
            for v in o.data.vertices:v.co+=delta
            nail_adjustments.append({'name':o.name,'movement_mm':round(delta.length,3)})

# Hidden backing ribs turn the hanging belt tails into supported relief.
for o in list(parts):
    if o.name.startswith('Belt tie'):
        vs=[v.co for v in o.data.vertices]
        lo=Vector(tuple(min(v[i] for v in vs) for i in range(3)))
        hi=Vector(tuple(max(v[i] for v in vs) for i in range(3)))
        cen=(lo+hi)/2;cen.y+=.9
        ellipsoid('Belt tail backing',cen,(1.15,1.7,(hi.z-lo.z)*.5+.5))

# One integral base, penetrating the feet by 1 mm before union.
bpy.ops.mesh.primitive_cylinder_add(vertices=192,radius=58,depth=7,location=(0,0,3.5))
base=bpy.context.object;base.name='Integral_base'
for c in list(base.users_collection):c.objects.unlink(base)
coll.objects.link(base);parts.append(base)
m=base.modifiers.new('Base rim bevel','BEVEL');m.width=.9;m.segments=3;apply(base,m)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)

active(parts[0])
for o in parts:o.select_set(True)
bpy.ops.object.join();statue=bpy.context.object;statue.name='CaveCyclops_PRINT_200mm_SOLID'
rem=statue.modifiers.new('Watertight union 0.16 mm','REMESH');rem.mode='VOXEL';rem.voxel_size=.16
apply(statue,rem)
sm=statue.modifiers.new('Gentle surface relaxation','SMOOTH');sm.factor=.42;sm.iterations=3;apply(statue,sm)

def components(mesh):
    bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table()
    seen=set();out=[]
    for v in bm.verts:
        if v.index in seen:continue
        ids=[];stack=[v];seen.add(v.index)
        while stack:
            q=stack.pop();ids.append(q.index)
            for e in q.link_edges:
                u=e.other_vert(q)
                if u.index not in seen:seen.add(u.index);stack.append(u)
        center=sum((bm.verts[i].co for i in ids),Vector())/len(ids)
        out.append({'vertices':len(ids),'center_mm':list(center),'ids':ids})
    bm.free();return sorted(out,key=lambda r:r['vertices'],reverse=True)

groups=components(statue.data)
print('UNION_COMPONENTS',json.dumps([{k:v for k,v in g.items() if k!='ids'} for g in groups]),flush=True)
specks=[g for g in groups[1:] if g['vertices']<=12]
if specks:
    bm=bmesh.new();bm.from_mesh(statue.data);bm.verts.ensure_lookup_table()
    ids={i for g in specks for i in g['ids']}
    # Limit cleanup to sub-voxel numerical fragments, never anatomical parts.
    for g in specks:
        coords=[bm.verts[i].co for i in g['ids']]
        assert max(max(v[k] for v in coords)-min(v[k] for v in coords) for k in range(3))<.4
    bmesh.ops.delete(bm,geom=[bm.verts[i] for i in ids],context='VERTS')
    bm.to_mesh(statue.data);bm.free();groups=components(statue.data)
# A substantial disconnected component means the adaptation needs correction.
assert len(groups)==1, 'Disconnected pieces remain: inspect UNION_COMPONENTS before exporting.'

# Physical pupil dimple and nostrils replace colour-only marks.
def carve(name,x,z,radius,depth,stretch=(1,1,1)):
    active(statue)
    bvh=BVHTree.FromObject(statue,bpy.context.evaluated_depsgraph_get())
    hit,n,_,_=bvh.ray_cast(Vector((x,-120,z)),Vector((0,1,0)))
    if hit is None:raise RuntimeError('No surface for '+name)
    # Sphere intersection gives a rounded, shallow depression with a closed bottom.
    center=hit.copy();center.y-=radius-depth
    cutter=ellipsoid(name,center,tuple(radius*s for s in stretch))
    m=statue.modifiers.new(name,'BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter;apply(statue,m)
    bpy.data.objects.remove(cutter,do_unlink=True)
    assert len(statue.data.vertices)>10000, 'Boolean unexpectedly removed the body'
print('LANDMARKS',json.dumps({k:list(v) for k,v in landmarks.items()}),flush=True)
eye_position=next(v for k,v in landmarks.items() if k.startswith('Eye_single'))
carve('Engraved pupil',eye_position.x,eye_position.z,.85,.40)
for name,v in landmarks.items():
    if name.startswith('Nostril'):carve('Nostril relief',v.x,v.z,.75,.45,(1.1,1,.68))

# Keep the printable surface detailed without shipping millions of flat triangles.
de=statue.modifiers.new('Print mesh budget','DECIMATE')
de.ratio=min(1,950000/sum(len(p.vertices)-2 for p in statue.data.polygons));apply(statue,de)

# Explicit triangles; remove degenerate elements and orient the connected surface.
t=statue.modifiers.new('Export triangles','TRIANGULATE');apply(statue,t)
bm=bmesh.new();bm.from_mesh(statue.data)
bmesh.ops.dissolve_degenerate(bm,dist=1e-6,edges=list(bm.edges))
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(statue.data);bm.free()
me=statue.data
# Normalize the final union exactly to 200 mm and make the contact plane flat.
minimum=min(v.co.z for v in me.vertices);maximum=max(v.co.z for v in me.vertices)
scale=200/(maximum-minimum)
for v in me.vertices:
    v.co.x*=scale;v.co.y*=scale;v.co.z=(v.co.z-minimum)*scale
    if v.co.z<.16:v.co.z=0
me.update()
for f in me.polygons:f.use_smooth=True

bm=bmesh.new();bm.from_mesh(me)
report={'source_sha256':source_hash,'source_file':'../CaveCyclops.blend','purpose':'200 mm static solid print prototype',
        'dimensions_mm':[round(max(v.co[i] for v in me.vertices)-min(v.co[i] for v in me.vertices),3) for i in range(3)],
        'triangles':sum(len(p.vertices)-2 for p in me.polygons),'vertices':len(me.vertices),
        'components':len(components(me)),'boundary_edges':sum(e.is_boundary for e in bm.edges),
        'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
        'zero_area_faces':sum(f.calc_area()<1e-10 for f in bm.faces),
        'signed_volume_cm3':round(bm.calc_volume(signed=True)/1000,3),
        'nominal_skirt_thickness_mm_before_union':round(.009*factor+1.2,3),
        'nominal_belt_tail_diameter_mm_before_union':round(.024*factor+.7,3),
        'union_voxel_mm':.16,'hollow':False,'supports_generated':False,
        'nail_seating_adjustments':nail_adjustments,'removed_subvoxel_specks':len(specks),
        'slicer_validated':False,'physical_print_tested':False,'full_wall_thickness_certified':False,
        'omitted_shader_inserts':omitted}
bm.free()
assert report['components']==1
assert report['boundary_edges']==report['nonmanifold_edges']==report['zero_area_faces']==0,report
assert report['signed_volume_cm3']>0
assert abs(report['dimensions_mm'][2]-200)<.001
assert hashlib.sha256(open(SOURCE,'rb').read()).hexdigest()==source_hash

# Binary STL contains explicit mm vertex coordinates (STL itself has no units).
active(statue)
stlpath=os.path.join(OUT,'CaveCyclops_200mm_SOLID.stl')
bpy.ops.wm.stl_export(filepath=stlpath,export_selected_objects=True,apply_modifiers=True,global_scale=1,use_scene_unit=False)

# Portable 3MF core package, explicitly declaring millimetres.
me.calc_loop_triangles()
vertices=''.join(f'<vertex x="{v.co.x:.6f}" y="{v.co.y:.6f}" z="{v.co.z:.6f}"/>' for v in me.vertices)
triangles=''.join(f'<triangle v1="{t.vertices[0]}" v2="{t.vertices[1]}" v3="{t.vertices[2]}"/>' for t in me.loop_triangles)
xml='<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1" type="model" name="CaveCyclops 200mm solid"><mesh><vertices>'+vertices+'</vertices><triangles>'+triangles+'</triangles></mesh></object></resources><build><item objectid="1"/></build></model>'
with zipfile.ZipFile(os.path.join(OUT,'CaveCyclops_200mm_SOLID.3mf'),'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    z.writestr('3D/3dmodel.model',xml)

# Verify the serialized STL, without confusing its unitless coordinates with metres.
bpy.ops.wm.stl_import(filepath=stlpath)
imported=bpy.context.object
bm=bmesh.new();bm.from_mesh(imported.data)
report['stl_roundtrip']={'height_mm':round(max(v.co.z for v in imported.data.vertices)-min(v.co.z for v in imported.data.vertices),3),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'triangles':len(imported.data.polygons)}
bm.free();bpy.data.objects.remove(imported,do_unlink=True)
assert report['stl_roundtrip']['height_mm']==200
assert report['stl_roundtrip']['nonmanifold_edges']==0
with open(os.path.join(OUT,'print_validation.json'),'w') as f:json.dump(report,f,indent=2)
print('PRINT_VALIDATED',json.dumps(report),flush=True)

# The editable Blender artifact uses real metres and displays millimetres.
for v in me.vertices:v.co*=.001
me.update()
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene.unit_settings.length_unit='MILLIMETERS'
mat=bpy.data.materials.new('Neutral resin | geometry only');mat.use_nodes=True
p=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
p.inputs['Base Color'].default_value=(.28,.30,.32,1);p.inputs['Roughness'].default_value=.58
me.materials.clear();me.materials.append(mat)
stage=bpy.data.collections.new('PREVIEW | not included in STL or 3MF');scene.collection.children.link(stage)
def move_stage(o):
    for c in list(o.users_collection):c.objects.unlink(o)
    stage.objects.link(o)
def light(name,location,energy,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);stage.objects.link(o);o.location=location;o.rotation_euler=(Vector((0,0,.105))-o.location).to_track_quat('-Z','Y').to_euler()
light('Large key',(.20,-.25,.35),5,.22)
light('Soft fill',(-.22,-.10,.20),1.5,.20)
light('Rim',(.1,.20,.30),4,.18)
world=bpy.data.worlds.new('Print preview');scene.world=world;world.use_nodes=True
back=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');back.inputs[0].default_value=(.07,.08,.10,1);back.inputs[1].default_value=.4
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.0002));floor=bpy.context.object;floor.name='Preview floor';move_stage(floor)
fm=bpy.data.materials.new('Dark backdrop');fm.diffuse_color=(.045,.05,.058,1);fm.use_nodes=True
fp=next(n for n in fm.node_tree.nodes if n.type=='BSDF_PRINCIPLED');fp.inputs['Base Color'].default_value=(.045,.05,.058,1);fp.inputs['Roughness'].default_value=.8;floor.data.materials.append(fm)
def camera(name,loc,target,lens):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);stage.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_start=.0005;d.clip_end=300;return o
hero=camera('PRINT Hero',(.27,-.49,.26),(0,0,.102),65)
front=camera('PRINT Front',(0,-.57,.14),(0,0,.101),65)
ex=eye_position.x*.001;ez=eye_position.z*.001
face=camera('PRINT Face',(ex+.040,-.195,ez),(ex,eye_position.y*.001,ez-.010),70)
scene.camera=hero;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=1080;scene.render.resolution_y=1350;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-.5
scene.render.image_settings.file_format='PNG'
active(statue)
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':
        a.spaces.active.region_3d.view_location=(0,0,.10);a.spaces.active.region_3d.view_distance=.4
        a.spaces.active.clip_start=.0001;a.spaces.active.clip_end=100
        a.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'CaveCyclops_Print_200mm.blend'))
for cam,name in ((hero,'preview_hero'),(front,'preview_front'),(face,'preview_face')):
    scene.camera=cam;scene.render.filepath=os.path.join(OUT,name+'.png');bpy.ops.render.render(write_still=True)
print('PRINT_VERSION_COMPLETE',flush=True)
