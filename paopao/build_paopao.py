"""Official-reference Jingqi Paopao fan sculpture, mm construction units."""
import bpy,bmesh,math,json,os,zipfile
from pathlib import Path
from mathutils import Vector,Matrix
from math import sin,cos,pi,sqrt
ROOT=Path(__file__).resolve().parent
for d in ('printing','renders'): (ROOT/d).mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):
    active(o);bpy.ops.object.modifier_apply(modifier=m.name)
def mat(name,color,rough=.35):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough
    return m
yellow=mat('01 | warm golden yellow',(1,.48,.003),.35)
white=mat('02 | porcelain eyes',(.96,.97,.91),.25)
brown=mat('03 | cocoa pupils and expression',(.018,.004,.001),.48)
iris=mat('04 | amber iris edge',(.29,.12,.012),.32)
grey=mat('Print | neutral clay',(.52,.56,.61),.58)
parts=[]
def mesh(name,vs,fs,m):
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
    o=bpy.data.objects.new(name,me);scene.collection.objects.link(o);me.materials.append(m)
    for f in me.polygons:f.use_smooth=True
    parts.append(o);return o
def normals(o):
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(o.data);bm.free()
def boolean(o,tool,operation):
    mod=o.modifiers.new(operation,'BOOLEAN');mod.operation=operation;mod.solver='EXACT';mod.object=tool;apply(o,mod)
    bpy.data.objects.remove(tool,do_unlink=True)
def box(loc,scale):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.scale=scale
    active(o);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return o
def surface(x,z):return -37*sqrt(max(.001,1-(x/44)**2-((z-44)/44)**2))
bpy.ops.mesh.primitive_uv_sphere_add(segments=144,ring_count=96,radius=1,location=(0,0,44))
body=bpy.context.object;body.name='BODY | round golden bubble';body.scale=(44,37,44)
active(body);bpy.ops.object.transform_apply(location=True,rotation=False,scale=True)
body.data.materials.append(yellow);parts.append(body)
for p in body.data.polygons:p.use_smooth=True
boolean(body,box((0,0,-48.5),(200,200,103)),'DIFFERENCE') # flat foot at z=3

# Eye lenses follow the round cheek, avoiding floating edges.
def eye_depth(x,z,cx):
    r2=((x-cx)/11.8)**2+((z-56)/13.0)**2
    return surface(x,z)-(.6+3.5*sqrt(max(0,1-r2)))
def lens(name,cx,cz,rx,rz,base,thickness,m):
    n=96;rings=20;vs=[];fs=[]
    vs.append((cx,base(cx,cz)-thickness,cz))
    for k in range(1,rings+1):
        r=k/rings
        for j in range(n):
            a=j*2*pi/n;x=cx+rx*r*cos(a);z=cz+rz*r*sin(a)
            vs.append((x,base(x,z)-thickness*sqrt(max(0,1-r*r)),z))
    for j in range(n):fs.append((0,1+j,1+(j+1)%n))
    for k in range(rings-1):
        for j in range(n):a=1+k*n+j;b=1+k*n+(j+1)%n;fs.append((a,b,b+n,a+n))
    end=len(vs);vs.append((cx,base(cx,cz)+5,cz))
    for j in range(n):fs.append((1+(rings-1)*n+j,end,1+(rings-1)*n+(j+1)%n))
    o=mesh(name,vs,fs,m);normals(o);return o
for cx in (-16,16):
    side='L' if cx<0 else 'R'
    lens('EYE '+side+' | large white',cx,56,11.8,13,lambda x,z:surface(x,z)-.6,3.5,white)
    lens('IRIS '+side+' | amber rim',cx,56,5.9,6.45,lambda x,z,c=cx:eye_depth(x,z,c)-.1,.9,iris)
    lens('PUPIL '+side+' | staring',cx,56,5.1,5.65,lambda x,z,c=cx:eye_depth(x,z,c)-.7,.8,brown)

def tube(name,points,radius,m):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=24;cu.bevel_depth=radius;cu.bevel_resolution=5;cu.use_fill_caps=True
    sp=cu.splines.new('BEZIER');sp.bezier_points.add(len(points)-1)
    for p,(x,z,r) in zip(sp.bezier_points,points):
        p.co=(x,surface(x,z)-.35,z);p.radius=r;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,cu);scene.collection.objects.link(o);cu.materials.append(m)
    active(o);bpy.ops.object.convert(target='MESH');parts.append(o);return o
tube('BROW L | high surprised arch',[(-28,73,.3),(-24,76,.9),(-18,78,1),(-12,76.8,.95),(-7,73.5,.35)],2.25,brown)
tube('BROW R | high surprised arch',[(7,73.5,.35),(12,76.8,.95),(18,78,1),(24,76,.9),(28,73,.3)],2.25,brown)
tube('MOUTH | stunned shallow frown',[(-14,28.8,.5),(-8,30.1,1),(0,30.5,1),(8,30.1,1),(14,28.8,.5)],1.05,brown)

# A single sealed sculpture with raised facial details survives monochrome printing.
copies=[]
for o in parts:
    c=o.copy();c.data=o.data.copy();scene.collection.objects.link(c);copies.append(c)
active(copies[0])
for o in copies:o.select_set(True)
bpy.ops.object.join();full=bpy.context.object;full.name='PRINT | complete sculpture'
active(full);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
m=full.modifiers.new('Watertight union','REMESH');m.mode='VOXEL';m.voxel_size=.16;apply(full,m)
m=full.modifiers.new('Gentle smoothing','SMOOTH');m.factor=.25;m.iterations=2;apply(full,m)
m=full.modifiers.new('Printable triangle budget','DECIMATE');m.ratio=min(1,350000/sum(len(p.vertices)-2 for p in full.data.polygons));apply(full,m)
m=full.modifiers.new('Triangulate','TRIANGULATE');apply(full,m);normals(full)
full.data.materials.clear();full.data.materials.append(grey)

def audit(o):
    bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();seen=set();components=0
    for v in bm.verts:
        if v.index in seen:continue
        components+=1;todo=[v];seen.add(v.index)
        while todo:
            q=todo.pop()
            for e in q.link_edges:
                v2=e.other_vert(q)
                if v2.index not in seen:seen.add(v2.index);todo.append(v2)
    r={'components':components,'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-9 for f in bm.faces),'volume_mm3':bm.calc_volume(signed=True),'triangles':len(o.data.polygons)}
    bm.free();r['dimensions_mm']=[round(max(v.co[i] for v in o.data.vertices)-min(v.co[i] for v in o.data.vertices),3) for i in range(3)]
    assert r['components']==1 and r['boundary_edges']==r['nonmanifold_edges']==r['degenerate_faces']==0 and r['volume_mm3']>0,r
    assert max(r['dimensions_mm'])<160,r
    return r
def export3mf(o,path):
    me=o.data;me.calc_loop_triangles()
    vs=''.join(f'<vertex x="{v.co.x:.6f}" y="{v.co.y:.6f}" z="{v.co.z:.6f}"/>' for v in me.vertices)
    ts=''.join(f'<triangle v1="{t.vertices[0]}" v2="{t.vertices[1]}" v3="{t.vertices[2]}"/>' for t in me.loop_triangles)
    xml=f'<?xml version="1.0"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1" type="model"><mesh><vertices>{vs}</vertices><triangles>{ts}</triangles></mesh></object></resources><build><item objectid="1"/></build></model>'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('3D/3dmodel.model',xml)
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
def export(o,name):
    active(o);bpy.ops.wm.stl_export(filepath=str(ROOT/'printing'/f'{name}.stl'),export_selected_objects=True,use_scene_unit=False)
    export3mf(o,ROOT/'printing'/f'{name}.3mf')
    r=audit(o)
    bpy.ops.wm.stl_import(filepath=str(ROOT/'printing'/f'{name}.stl'));test=bpy.context.object
    r['stl_roundtrip']=audit(test);bpy.data.objects.remove(test,do_unlink=True);return r
report={'reference':'https://my.163.com/chongwu/pets/98.html','printer_target':'Bambu Lab A1 mini','physical_print_tested':False,'slicer_tested':False,'parts':{}}
print_objects=[]
for side in ('Front','Back'):
    o=full.copy();o.data=full.data.copy();scene.collection.objects.link(o);o.name='PRINT_'+side
    boolean(o,box((0,100 if side=='Front' else -100,45),(250,200,250)),'DIFFERENCE')
    m=o.modifiers.new('Clean planar half','REMESH');m.mode='VOXEL';m.voxel_size=.16;apply(o,m)
    m=o.modifiers.new('Half budget','DECIMATE');m.ratio=min(1,300000/sum(len(p.vertices)-2 for p in o.data.polygons));apply(o,m)
    m=o.modifiers.new('Triangles','TRIANGULATE');apply(o,m);normals(o)
    o.data.transform(Matrix.Rotation(-pi/2 if side=='Front' else pi/2,4,'X'))
    # Flat equatorial bonding surface is the build plate; face/back surface points up.
    minz=min(v.co.z for v in o.data.vertices)
    for v in o.data.vertices:v.co.z-=minz
    report['parts'][side]=export(o,'Paopao_'+side)
    print_objects.append(o)
for v in full.data.vertices:v.co.z-=3
report['parts']['Complete']=export(full,'Paopao_Complete')
for v in full.data.vertices:v.co.z+=3
(ROOT/'printing'/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('VALIDATION',json.dumps(report),flush=True)

display=bpy.data.collections.new('01 | COLORED SCULPTURE');scene.collection.children.link(display)
printing=bpy.data.collections.new('02 | PRINTING');scene.collection.children.link(printing)
def move(o,c):
    for old in list(o.users_collection):old.objects.unlink(o)
    c.objects.link(o)
for o in parts:move(o,display)
for o in [full]+print_objects:move(o,printing)
printing.hide_render=True;printing.hide_viewport=True
for o in list(bpy.data.objects):
    if o.type=='MESH':o.data.transform(Matrix.Scale(.001,4));o.location*=.001
scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'

studio=bpy.data.collections.new('03 | STUDIO');scene.collection.children.link(studio)
def cam(name,loc,target,lens=58):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_start=.001;return o
hero=cam('CAM | three quarter',(.115,-.25,.127),(0,0,.044),62)
frontcam=cam('CAM | front',(0,-.275,.070),(0,0,.044),62)
printcam=cam('CAM | print halves',(.17,-.22,.24),(0,0,.015),55)
def light(name,loc,power,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,.04))-o.location).to_track_quat('-Z','Y').to_euler()
light('Key softbox',(-.12,-.16,.22),3,.16);light('Fill',(.14,-.09,.12),1.4,.12);light('Rim',(.01,.15,.19),3,.12)
floor=box((0,0,.001),(200,200,.003));floor.name='Studio floor';move(floor,studio);floor.data.materials.append(mat('Backdrop',(.045,.072,.11),.75))
world=bpy.data.worlds.new('Soft studio');world.use_nodes=True;scene.world=world
world.node_tree.nodes.get('Background').inputs[0].default_value=(.18,.23,.32,1);world.node_tree.nodes.get('Background').inputs[1].default_value=.35
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.render.resolution_x=1400;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard';scene.view_settings.exposure=-2.2;scene.render.image_settings.file_format='PNG'
scene.camera=hero
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.clip_start=.001
active(body)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Jingqi_Paopao.blend'))
for name,c in [('01_color',hero),('02_front',frontcam)]:
    scene.camera=c;scene.render.filepath=str(ROOT/'renders'/f'{name}.png');bpy.ops.render.render(write_still=True)
display.hide_render=True;display.hide_viewport=True;printing.hide_render=False;printing.hide_viewport=False
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-.8
for o in print_objects:o.hide_render=True;o.hide_set(True)
scene.camera=hero;scene.render.filepath=str(ROOT/'renders'/'03_print_complete.png');bpy.ops.render.render(write_still=True)
full.hide_render=True;full.hide_set(True)
for i,o in enumerate(print_objects):o.hide_render=False;o.hide_set(False);o.location.x=(-.049 if i==0 else .049);o.location.y=(-.044 if i==0 else .044)
floor.location.z=-.002;scene.camera=printcam
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'printing'/'Paopao_Print.blend'))
scene.render.filepath=str(ROOT/'renders'/'04_print_halves.png');bpy.ops.render.render(write_still=True)
print('PAOPAO_COMPLETE',flush=True)
