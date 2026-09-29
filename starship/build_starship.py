"""Starship / Super Heavy inspired display and 200 mm print models.

Independent fan-study geometry, not flight hardware or an exact flight revision.
All construction coordinates are millimetres. Blender scenes are saved in metres.
"""
import bpy, bmesh, math, os, json, random, zipfile
from mathutils import Vector
from math import sin, cos, pi, sqrt

ROOT=os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(ROOT,'renders'),exist_ok=True)
os.makedirs(os.path.join(ROOT,'printing'),exist_ok=True)
random.seed(27)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):bpy.data.collections.remove(c)
scene=bpy.context.scene
craft=bpy.data.collections.new('01 | STARSHIP + SUPER HEAVY');scene.collection.children.link(craft)
stand=bpy.data.collections.new('02 | DISPLAY BASE');scene.collection.children.link(stand)
printcol=bpy.data.collections.new('03 | PRINT CONSTRUCTION');scene.collection.children.link(printcol)
printparts=[];displayparts=[]

def material(name,color,metal=0,rough=.4):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    m.diffuse_color=(*color,1);return m
steel=material('Brushed stainless steel',(.48,.52,.58),.93,.30)
edge=material('Machined steel',(.64,.68,.73),.92,.22)
dark=material('Black ceramic thermal protection',(.009,.014,.019),.05,.83)
tiles=[material('Ceramic tile '+str(i),(.014+i*.0018,.019+i*.0018,.024+i*.0018),.03,.77+i*.016) for i in range(5)]
engine=material('Engine graphite',(.045,.049,.052),.8,.43)
base_mat=material('Obsidian plinth',(.015,.022,.031),.62,.29)
label=material('Warm white markings',(.74,.78,.83),.2,.36)
accent=material('Brass identification line',(.46,.25,.085),.8,.32)
resin=material('Neutral print resin',(.36,.39,.42),0,.58)
# Subtle brushed finish, confined to the display material.
ns=steel.node_tree.nodes;ls=steel.node_tree.links
t=ns.new('ShaderNodeTexNoise');t.inputs['Scale'].default_value=170;t.inputs['Detail'].default_value=2
b=ns.new('ShaderNodeBump');b.inputs['Strength'].default_value=.10;b.inputs['Distance'].default_value=.000015
ls.new(t.outputs['Fac'],b.inputs['Height']);ls.new(b.outputs[0],next(n for n in ns if n.type=='BSDF_PRINCIPLED').inputs['Normal'])

def register(o,printing=False,collection=None):
    for c in list(o.users_collection):c.objects.unlink(o)
    (collection or (printcol if printing else craft)).objects.link(o)
    (printparts if printing else displayparts).append(o)
    return o
def activate(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):activate(o);bpy.ops.object.modifier_apply(modifier=m.name)
def mesh(name,vs,fs,mat,printing=False,collection=None):
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(mat);me.update()
    o=bpy.data.objects.new(name,me);(collection or (printcol if printing else craft)).objects.link(o)
    (printparts if printing else displayparts).append(o)
    for f in me.polygons:f.use_smooth=True
    return o
def cylinder(name,r,depth,z,mat,x=0,y=0,printing=False,collection=None,vertices=96):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=depth,location=(x,y,z))
    o=bpy.context.object;o.name=name;register(o,printing,collection);o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
    return o
def torus(name,r,minor,z,mat,printing=False):
    bpy.ops.mesh.primitive_torus_add(major_radius=r,minor_radius=minor,major_segments=96,minor_segments=8,location=(0,0,z))
    o=bpy.context.object;o.name=name;register(o,printing);o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
    return o
def box(name,center,size,mat,printing=False,rotation=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.scale=size;o.rotation_euler[2]=rotation
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);register(o,printing);o.data.materials.append(mat)
    return o
def lathe(name,profile,mat,printing=False,n=128):
    vs=[];fs=[]
    for z,r in profile:
        for j in range(n):a=2*pi*j/n;vs.append((r*cos(a),r*sin(a),z))
    for k in range(len(profile)-1):
        for j in range(n):a=k*n+j;b=k*n+(j+1)%n;fs.append((a,b,b+n,a+n))
    fs.append(tuple(reversed(range(n))));fs.append(tuple((len(profile)-1)*n+j for j in range(n)))
    return mesh(name,vs,fs,mat,printing)
def fin(name,polygon,angle,thickness,mat,printing=False):
    # Polygon coordinates are radial distance and height; tangential extrusion.
    vs=[];N=len(polygon)
    for tang in (-thickness/2,thickness/2):
        for r,z in polygon:vs.append((r*cos(angle)-tang*sin(angle),r*sin(angle)+tang*cos(angle),z))
    fs=[tuple(reversed(range(N))),tuple(N+i for i in range(N))]
    for i in range(N):j=(i+1)%N;fs.append((i,j,j+N,i+N))
    o=mesh(name,vs,fs,mat,printing)
    m=o.modifiers.new('Soft manufactured edges','BEVEL');m.width=.11 if printing else .075;m.segments=3;apply(o,m)
    for p in o.data.polygons:p.use_smooth=False
    return o
def nozzle(name,x,y,z,r,length):
    # Closed annular bell with a recessed interior, not a solid black cone.
    profile=[(z,r*.43),(z-length*.22,r*.49),(z-length*.62,r*.78),(z-length,r),
             (z-length,r-.10),(z-length*.60,max(.1,r*.78-.10)),(z-length*.20,max(.1,r*.49-.10)),(z,.16)]
    o=lathe(name,profile,engine,n=32)
    o.location.x=x;o.location.y=y
    return o
def surface_radius(z):
    if z<=177:return 7.4
    t=min(1,max(0,(z-177)/23))
    return .16+7.24*cos(t*pi/2)

# Main silhouettes: total assembly 200 mm, inclusive of its display base.
ship_profile=[(121.5,7.4),(177,7.4)]+[(177+23*i/36,surface_radius(177+23*i/36)) for i in range(1,37)]
for printing in (False,True):
    tag='PRINT ' if printing else ''
    lathe(tag+'Super Heavy | booster',[(9.6,7.35),(10.3,7.4),(117.9,7.4)],resin if printing else steel,printing)
    profile=[(z,max(.65,r)) for z,r in ship_profile] if printing else ship_profile
    lathe(tag+'Starship | upper stage',profile,resin if printing else steel,printing)
    cylinder(tag+'Hot-stage solid core',7.15,4.4,119.7,resin if printing else engine,printing=printing)
    for z in (117.9,121.7):torus(tag+'Hot-stage ring',7.43,.23 if printing else .16,z,resin if printing else edge,printing)
    # Four control flaps: two aft and two on the nose transition.
    for a in (0,pi):
        fin(tag+'Aft flap',[(7.05,126),(12.7,123.6),(12.0,140.2),(7.05,149)],a,1.45 if printing else .42,resin if printing else steel,printing)
        fin(tag+'Forward flap',[(6.75,177.8),(10.8,176),(10.0,184.5),(3.45,191.5)],a,1.4 if printing else .38,resin if printing else steel,printing)
    # Four grid fins: open lattices for display; backed ribs for print strength.
    for a in (0,pi/2,pi,3*pi/2):
        def gridbox(name,rad,tan,z,sizes,mat):
            return box(tag+name,(rad*cos(a)-tan*sin(a),rad*sin(a)+tan*cos(a),z),sizes,mat,printing,a)
        if printing:
            gridbox('Grid fin solid backing',9.75,0,112.6,(5.3,4.8,1.45),resin)
            for offset in (-1.5,0,1.5):gridbox('Grid fin raised rib',9.75,offset,113.42,(5.3,.55,.35),resin)
            for rad in (8.5,10,11.5):gridbox('Grid fin cross rib',rad,0,113.42,(.55,4.8,.35),resin)
            fin('PRINT Grid fin root gusset',[(6.7,109.5),(9.3,112.1),(6.7,112.1)],a,1.8,resin,True)
        else:
            for tan in (-2.35,2.35):gridbox('Grid fin outer rail',9.85,tan,112.6,(5.5,.30,.62),edge)
            for rad in (7.15,12.55):gridbox('Grid fin end rail',rad,0,112.6,(.28,4.9,.62),edge)
            for j in range(1,6):gridbox('Grid fin lattice',7.15+j*.90,0,112.6,(.17,4.7,.42),steel)
            for j in range(1,5):gridbox('Grid fin lattice cross',9.85,-2.35+j*.94,112.6,(5.4,.17,.42),steel)
    # Thick axial support joins the booster to its presentation base.
    cylinder(tag+'Axial display mount',2.7 if printing else 2.3,6.5,7.2,resin if printing else base_mat,printing=printing,collection=printcol if printing else stand)
    base=cylinder(tag+'Circular base',33,5,2.5,resin if printing else base_mat,printing=printing,collection=printcol if printing else stand,vertices=160)
    m=base.modifiers.new('Base bevel','BEVEL');m.width=.55;m.segments=3;apply(base,m)

# Ring welds and mechanical structure on the stainless booster.
for z in [14+i*4.0 for i in range(26)]:
    torus('Booster ring weld',7.405,.034,z,edge)
    # A reduced set of broader real ridges survives the 200 mm print scale.
    if int(round((z-14)/4))%2==0:torus('PRINT booster weld',7.36,.15,z,resin,True)
for z in (124,130,138,146,154,162,170,177):torus('Ship weld',7.405,.035,z,edge)
for j in range(32):
    a=2*pi*j/32
    box('Hot-stage vent rib',(7.35*cos(a),7.35*sin(a),119.8),(.32,.40,3.6),edge,rotation=a)
    box('PRINT hot-stage rib',(7.32*cos(a),7.32*sin(a),119.8),(.55,.58,3.7),resin,True,a)

# 33 simplified nozzle bells: 20 perimeter + 10 middle + 3 central.
for count,radius,bell in ((20,5.63,.74),(10,3.42,.81),(3,1.10,.87)):
    for j in range(count):
        a=2*pi*j/count+.12
        nozzle('Super Heavy engine bell',radius*cos(a),radius*sin(a),10.5,bell,2.8)
# Printable engine skirt is structural; little bells become embedded relief lobes.
for j in range(20):
    a=2*pi*j/20+.12
    cylinder('PRINT nozzle relief',.83,2.6,9.0,resin,x=5.63*cos(a),y=5.63*sin(a),printing=True,vertices=24)

# The forward half of Starship receives real hexagonal ceramic tiles.
# Hex grids are mapped over the cylindrical/ogive profile; no image assets needed.
hex_r=.45;du=sqrt(3)*hex_r;dz=1.5*hex_r
vs=[];fs=[];tile_materials=[]
rows=int((199-122.1)/dz)
for row in range(rows):
    zc=122.1+row*dz;rad=surface_radius(zc)
    if rad<.6:continue
    circumference=pi*rad
    n=int(circumference/du)
    for col in range(n):
        u=(col+.5+.5*(row%2))*du
        if u>circumference-.25:continue
        theta=pi+u/rad
        start=len(vs)
        for j in range(6):
            a=pi/6+2*pi*j/6
            zz=zc+hex_r*.94*sin(a)
            rr=surface_radius(zz)+.055
            th=theta+hex_r*.94*cos(a)/max(.6,rad)
            vs.append((rr*cos(th),rr*sin(th),zz))
        fs.append(tuple(start+j for j in range(6)));tile_materials.append(random.randrange(5))
tile_obj=mesh('TPS | individual hexagonal tiles',vs,fs,tiles[0])
for m in tiles[1:]:tile_obj.data.materials.append(m)
for p,i in zip(tile_obj.data.polygons,tile_materials):p.material_index=i;p.use_smooth=False
# Dark backing under the tile joints, with a slight shell offset.
vs=[];fs=[];NZ=110;NA=64
for k in range(NZ):
    z=121.7+(199.95-121.7)*k/(NZ-1);r=surface_radius(z)+.026
    for j in range(NA):a=pi+pi*j/(NA-1);vs.append((r*cos(a),r*sin(a),z))
for k in range(NZ-1):
    for j in range(NA-1):i=k*NA+j;fs.append((i,i+1,i+1+NA,i+NA))
mesh('TPS | continuous backing',vs,fs,dark)
# Thin black ceramic panels on the windward face of the four flaps.
for a in (0,pi):
    for name,poly in (('Aft flap TPS',[(7.18,126.4),(12.48,124.2),(11.8,140),(7.18,148.3)]),('Forward flap TPS',[(6.85,178),(10.58,176.5),(9.8,184.3),(3.70,191)])):
        o=fin(name,poly,a,.08,dark);o.location.y=-.25

# Broad seam marks on the printable thermal side (relief, not loose tiles).
for z in (132,140,148,156,164,172):
    # A half-ring with capped ends intersects the main skin by more than one voxel.
    vs=[];fs=[];N=64;S=8
    for i in range(N):
        a=pi+pi*i/(N-1)
        for j in range(S):
            t=2*pi*j/S;r=7.36+.18*cos(t);vs.append((r*cos(a),r*sin(a),z+.18*sin(t)))
    for i in range(N-1):
        for j in range(S):q=i*S+j;qq=i*S+(j+1)%S;fs.append((q,qq,qq+S,q+S))
    fs.extend([tuple(reversed(range(S))),tuple((N-1)*S+j for j in range(S))])
    mesh('PRINT thermal surface seam',vs,fs,resin,True)

# Service conduits sit on the leeward side and remain attached on the print.
for a in (pi/3,2*pi/3):
    cylinder('External service conduit',.17,80,65,edge,x=7.43*cos(a),y=7.43*sin(a),vertices=24)
    cylinder('PRINT service conduit',.45,80,65,resin,x=7.34*cos(a),y=7.34*sin(a),printing=True,vertices=24)
    for z in range(29,103,8):
        box('Conduit mounting shoe',(7.4*cos(a),7.4*sin(a),z),(.6,.6,.26),engine,rotation=a)

def text_object(name,body,size,loc,mat,rotation=(pi/2,0,0),collection=craft):
    d=bpy.data.curves.new(name,'FONT');d.body=body;d.size=size;d.align_x='CENTER';d.extrude=.008;d.bevel_depth=.004
    o=bpy.data.objects.new(name,d);collection.objects.link(o);o.location=loc;o.rotation_euler=rotation;d.materials.append(mat);displayparts.append(o);return o
# Markings use plain type, not a traced corporate logo.
text_object('Booster marking','SPACEX',2.0,(0,-7.50,78),engine)
text_object('Booster stage label','SUPER HEAVY',.88,(0,-7.51,74.8),engine)
text_object('Serial','SH / 01',.72,(0,-7.51,71.8),engine)
text_object('Base identification','STARSHIP',3.2,(0,-19,5.015),label,rotation=(0,0,0),collection=stand)
text_object('Base subtitle','SUPER HEAVY  /  STUDY 01',1.0,(0,-23,5.018),label,rotation=(0,0,0),collection=stand)
# An inlaid ring and index ticks give the stand an engineering-display character.
o=torus('Base brass inlay',30,.11,5.01,accent)
for c in list(o.users_collection):c.objects.unlink(o)
stand.objects.link(o)
for j in range(48):
    a=2*pi*j/48;r=29.0
    o=box('Base graduation',(r*cos(a),r*sin(a),5.022),(.55 if j%4 else 1.05,.07,.025),label,rotation=a)
    for c in list(o.users_collection):c.objects.unlink(o)
    stand.objects.link(o)

# Build and validate the print version while all geometry is in mm.
activate(printparts[0])
for o in printparts:o.select_set(True)
bpy.ops.object.convert(target='MESH');bpy.ops.object.join()
printed=bpy.context.object;printed.name='PRINT_Starship_SuperHeavy_200mm_SOLID'
rem=printed.modifiers.new('Solid union 0.10 mm','REMESH');rem.mode='VOXEL';rem.voxel_size=.10;apply(printed,rem)
sm=printed.modifiers.new('Edge relaxation','SMOOTH');sm.factor=.32;sm.iterations=2;apply(printed,sm)
de=printed.modifiers.new('Print tessellation','DECIMATE');de.ratio=min(1,650000/sum(len(p.vertices)-2 for p in printed.data.polygons));apply(printed,de)
t=printed.modifiers.new('Triangles','TRIANGULATE');apply(printed,t)
bm=bmesh.new();bm.from_mesh(printed.data);bmesh.ops.dissolve_degenerate(bm,dist=.000001,edges=list(bm.edges));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(printed.data);bm.free()
lo=min(v.co.z for v in printed.data.vertices);hi=max(v.co.z for v in printed.data.vertices);s=200/(hi-lo)
for v in printed.data.vertices:v.co.x*=s;v.co.y*=s;v.co.z=(v.co.z-lo)*s
printed.data.materials.clear();printed.data.materials.append(resin)
for p in printed.data.polygons:p.use_smooth=True

def audit(o):
    bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();seen=set();components=[]
    for v in bm.verts:
        if v.index in seen:continue
        stack=[v];seen.add(v.index);count=0;center=Vector()
        while stack:
            q=stack.pop();count+=1;center+=q.co
            for e in q.link_edges:
                u=e.other_vert(q)
                if u.index not in seen:seen.add(u.index);stack.append(u)
        components.append({'vertices':count,'center':list(center/count)})
    r={'components':len(components),'component_details':components,'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-10 for f in bm.faces),'volume_cm3':bm.calc_volume(signed=True)/1000,'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'dimensions_mm':[round(max(v.co[i] for v in o.data.vertices)-min(v.co[i] for v in o.data.vertices),3) for i in range(3)]}
    bm.free();return r
report=audit(printed);print('PRINT_AUDIT',json.dumps(report),flush=True)
assert report['components']==1 and report['boundary_edges']==report['nonmanifold_edges']==report['zero_area_faces']==0,report
assert report['volume_cm3']>0 and report['dimensions_mm'][2]==200
activate(printed);stl=os.path.join(ROOT,'printing','Starship_FullStack_200mm.stl')
bpy.ops.wm.stl_export(filepath=stl,export_selected_objects=True,apply_modifiers=True,global_scale=1,use_scene_unit=False)
me=printed.data;me.calc_loop_triangles()
vs=''.join(f'<vertex x="{v.co.x:.6f}" y="{v.co.y:.6f}" z="{v.co.z:.6f}"/>' for v in me.vertices)
ts=''.join(f'<triangle v1="{t.vertices[0]}" v2="{t.vertices[1]}" v3="{t.vertices[2]}"/>' for t in me.loop_triangles)
xml='<?xml version="1.0"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1" type="model" name="Starship Super Heavy 200mm"><mesh><vertices>'+vs+'</vertices><triangles>'+ts+'</triangles></mesh></object></resources><build><item objectid="1"/></build></model>'
with zipfile.ZipFile(os.path.join(ROOT,'printing','Starship_FullStack_200mm.3mf'),'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    z.writestr('3D/3dmodel.model',xml)
bpy.ops.wm.stl_import(filepath=stl);reimported=bpy.context.object
report['stl_roundtrip']=audit(reimported);bpy.data.objects.remove(reimported,do_unlink=True)
assert report['stl_roundtrip']['nonmanifold_edges']==0 and report['stl_roundtrip']['components']==1
report.update({'height_includes_base':True,'solid':True,'minimum_flap_design_mm':1.4,'grid_fin_backing_design_mm':1.45,'slicer_tested':False,'physical_print_tested':False,'full_wall_thickness_certified':False,'exact_flight_revision_replica':False})
with open(os.path.join(ROOT,'printing','validation.json'),'w') as f:json.dump(report,f,indent=2)

# Scale display and print objects into real metres for Blender's saved scenes.
for o in list(craft.objects)+list(stand.objects)+list(printcol.objects):
    o.location*=.001;o.scale*=.001
    if o.type=='MESH':activate(o);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS';scene.unit_settings.scale_length=1
printcol.hide_render=True;printcol.hide_viewport=True

stage=bpy.data.collections.new('04 | STUDIO');scene.collection.children.link(stage)
def camera(name,loc,target,lens):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);stage.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_start=.0001;return o
hero=camera('CAM 01 | full stack',(.255,-.44,.245),(0,0,.105),75)
upper=camera('CAM 02 | Starship detail',(.073,-.12,.176),(0,0,.162),68)
aft=camera('CAM 03 | metal and grid fins',(-.08,.15,.128),(0,0,.112),70)
def area(name,loc,target,power,size,color=(1,1,1),size_y=None):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color
    d.shape='RECTANGLE' if size_y else 'DISK';d.size=size
    if size_y:d.size_y=size_y
    o=bpy.data.objects.new(name,d);stage.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('KEY | long softbox',(.10,-.15,.20),(0,0,.1),4,.07,(.86,.92,1),.32)
area('RIM | warm strip',(-.095,.075,.19),(0,0,.11),5,.055,(1,.79,.54),.30)
area('FILL | front',(-.10,-.20,.15),(0,0,.1),1.5,.18,(.70,.82,1))
area('TOP | reflection',(.03,.02,.34),(0,0,.1),2,.13)
world=bpy.data.worlds.new('Orbital studio');world.use_nodes=True;scene.world=world
p=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');p.inputs[0].default_value=(.11,.14,.20,1);p.inputs[1].default_value=.22
# Seamless sweep behind the miniature.
profile=[(-10,-.00025),(.10,-.00025)]+[(.10+.15*sin(pi/2*i/24),-.00025+.15*(1-cos(pi/2*i/24))) for i in range(1,25)]+[(.25,5)]
verts=[];faces=[]
for y,z in profile:verts.extend([(-5,y,z),(5,y,z)])
for i in range(len(profile)-1):faces.append((2*i,2*i+1,2*i+3,2*i+2))
floor=mesh('Seamless backdrop',verts,faces,material('Studio charcoal',(.018,.028,.044),.1,.66),collection=stage)
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=1700;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-.35;scene.render.image_settings.file_format='PNG'
scene.camera=hero
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.clip_start=.0001;a.spaces.active.region_3d.view_location=(0,0,.1);a.spaces.active.region_3d.view_distance=.4
activate(next(o for o in craft.objects if o.name.startswith('Starship |')))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'Starship_FullStack.blend'))
for cam,name in ((hero,'01_full_stack'),(upper,'02_starship_detail'),(aft,'03_booster_detail')):
    scene.camera=cam;scene.render.filepath=os.path.join(ROOT,'renders',name+'.png');bpy.ops.render.render(write_still=True)

# Dedicated print scene contains the one solid mesh plus clearly separated studio.
craft.hide_render=True;stand.hide_render=True;craft.hide_viewport=True;stand.hide_viewport=True
printcol.hide_render=False;printcol.hide_viewport=False
scene.camera=hero
activate(printed)
for c in (craft,stand):
    for o in list(c.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.collections.remove(c)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'printing','Starship_Print_200mm.blend'))
scene.render.filepath=os.path.join(ROOT,'renders','04_print_version.png');bpy.ops.render.render(write_still=True)
print('STARSHIP_COMPLETE',json.dumps(report),flush=True)
