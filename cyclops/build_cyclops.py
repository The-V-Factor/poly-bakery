"""Build the original cave cyclops asset, locally in Blender. No external assets."""
import bpy, math, random, json, os
from mathutils import Vector
from math import sin, cos, pi

ROOT = os.path.dirname(os.path.abspath(__file__))
random.seed(17)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    if c.name != 'Collection': bpy.data.collections.remove(c)
base = bpy.data.collections.get('Collection'); base.name = '01_CHARACTER'
detail = bpy.data.collections.new('02_ANATOMICAL_DETAILS'); bpy.context.scene.collection.children.link(detail)
stage = bpy.data.collections.new('03_PRESENTATION'); bpy.context.scene.collection.children.link(stage)
source = bpy.data.collections.new('04_SCULPT_SOURCE'); bpy.context.scene.collection.children.link(source)
source.hide_render = True; source.hide_viewport = True

def move(obj, collection):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    collection.objects.link(obj)
    return obj

def material(name, color, rough=.5, metallic=0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metallic
    return m

skin = material('M_Cyclops_Skin | ash, ochre, weathered', (.27,.22,.17), .64)
nodes = skin.node_tree.nodes; links = skin.node_tree.links
p = nodes.get('Principled BSDF'); p.inputs['Subsurface Weight'].default_value=.075
p.inputs['Subsurface Radius'].default_value=(1,.42,.23)
tex = nodes.new('ShaderNodeTexCoord')
noise = nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=4.8; noise.inputs['Detail'].default_value=5
links.new(tex.outputs['Generated'],noise.inputs['Vector'])
ramp=nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position=.22; ramp.color_ramp.elements[0].color=(.027,.020,.015,1)
ramp.color_ramp.elements[1].position=.79; ramp.color_ramp.elements[1].color=(.19,.135,.083,1)
ramp.color_ramp.elements.new(.50).color=(.082,.06,.042,1)
links.new(noise.outputs['Fac'],ramp.inputs[0]); links.new(ramp.outputs[0],p.inputs['Base Color'])
fine=nodes.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value=150; fine.inputs['Detail'].default_value=3; fine.inputs['Roughness'].default_value=.72
links.new(tex.outputs['Generated'],fine.inputs['Vector'])
bump=nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.27; bump.inputs['Distance'].default_value=.018
links.new(fine.outputs['Fac'],bump.inputs['Height']); links.new(bump.outputs[0],p.inputs['Normal'])
lip=material('M_Lips | muted umber',(.19,.112,.079),.58)
crease=material('M_Recesses',(.052,.032,.021),.84)
scar=material('M_Healed_scars',(.30,.245,.185),.71)
nail=material('M_Keratin',(.15,.12,.075),.37)
sclera=material('M_Eye_sclera',(.46,.37,.24),.19)
pupil=material('M_Pupil',(.003,.004,.002),.10)
iris=bpy.data.materials.new('M_Iris | amber radial fibres'); iris.use_nodes=True
ip=iris.node_tree.nodes.get('Principled BSDF'); ip.inputs['Roughness'].default_value=.23
vc=iris.node_tree.nodes.new('ShaderNodeVertexColor'); vc.layer_name='IrisPigment'
iris.node_tree.links.new(vc.outputs['Color'],ip.inputs['Base Color'])
cloth=material('M_Hide | worn brown',(.09,.061,.033),.9)
cn=cloth.node_tree.nodes.new('ShaderNodeTexNoise'); cn.inputs['Scale'].default_value=85
cb=cloth.node_tree.nodes.new('ShaderNodeBump'); cb.inputs['Strength'].default_value=.45; cb.inputs['Distance'].default_value=.016
cloth.node_tree.links.new(cn.outputs['Fac'],cb.inputs['Height']); cloth.node_tree.links.new(cb.outputs[0],cloth.node_tree.nodes.get('Principled BSDF').inputs['Normal'])
rope_mat=material('M_Fibre',(.19,.14,.077),.93)
stone=material('M_Basalt',(.033,.04,.043),.88)

parts=[]
def ell(name,loc,scale,mat=skin,collect=base,segments=32,rings=20,body=False):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if mat: o.data.materials.append(mat)
    for f in o.data.polygons:f.use_smooth=True
    move(o,collect)
    if body: parts.append(o)
    return o

def limb(name,a,b,r1,r2,ry=None,body=True):
    a,b=Vector(a),Vector(b); mid=(a+b)*.5
    o=ell(name,mid,(r1,ry or r2,(b-a).length*.5+r2*.50),body=body)
    o.rotation_mode='QUATERNION'; o.rotation_quaternion=Vector((0,0,1)).rotation_difference(b-a)
    return o

def tube(name,pts,radii,mat=skin,collection=detail,sides=10):
    pts=[Vector(p) for p in pts]; verts=[]; faces=[]
    for i,v in enumerate(pts):
        t=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
        n=t.cross(Vector((0,1,0)))
        if n.length<.1:n=t.cross(Vector((1,0,0)))
        n.normalize(); b=t.cross(n).normalized()
        r=radii[i] if isinstance(radii,(tuple,list)) else radii
        for j in range(sides):verts.append(v+r*(cos(j*2*pi/sides)*n+sin(j*2*pi/sides)*b))
    for i in range(len(pts)-1):
        for j in range(sides):
            a=i*sides+j; d=i*sides+(j+1)%sides
            faces.append((a,d,d+sides,a+sides))
    faces.append(tuple(reversed(range(sides)))); faces.append(tuple((len(pts)-1)*sides+j for j in range(sides)))
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(verts,[],faces); mesh.update()
    o=bpy.data.objects.new(name,mesh); collection.objects.link(o); mesh.materials.append(mat)
    for f in mesh.polygons:f.use_smooth=True
    return o

# Continuous anatomy. Forward is -Y; height is 4.42 m.
ell('Pelvis',(0,.035,1.91),(.43,.285,.40),body=True)
ell('Abdomen',(0,-.025,2.30),(.365,.30,.49),body=True)
ell('Ribcage',(0,.035,2.77),(.51,.30,.56),body=True)
ell('Upper back',(0,.14,3.035),(.58,.315,.34),body=True)
for s in (-1,1):
    ell('Pectoral', (s*.252,-.203,2.895),(.29,.095,.19),body=True)
    limb('Trapezius',(s*.08,.11,3.41),(s*.54,.08,3.19),.19,.18)
    ell('Latissimus',(s*.35,.15,2.67),(.17,.19,.39),body=True)
    ell('Gluteus',(s*.22,.18,1.81),(.255,.245,.29),body=True)
ell('Soft belly',(0,-.205,2.16),(.29,.16,.31),body=True)
limb('Neck',(0,.10,3.1),(0,-.025,3.64),.245,.245)
for s in (-1,1):limb('Sternomastoid',(s*.15,-.14,3.46),(s*.12,-.23,3.13),.075,.066)
fingers=[]
for s in (-1,1):
    shoulder=(s*.62,.035,3.115); elbow=(s*1.01,-.025,2.57); wrist=(s*1.285,-.12,1.995)
    ell('Deltoid',shoulder,(.22,.22,.30),body=True)
    limb('Humerus',shoulder,elbow,.17,.15)
    limb('Biceps',(s*.72,-.07,2.97),(s*.96,-.10,2.63),.127,.122)
    ell('Elbow',elbow,(.157,.15,.17),body=True)
    limb('Ulna',elbow,wrist,.137,.112)
    limb('Forearm flexors',(s*1.025,-.10,2.51),(s*1.20,-.15,2.16),.157,.126)
    ell('Wrist',wrist,(.115,.10,.125),body=True)
    palm=(s*1.355,-.145,1.82)
    po=ell('Palm',palm,(.171,.099,.231),body=True); po.rotation_euler[1]=s*.16
    for j,(dx,length) in enumerate([(-.115,.30),(-.035,.385),(.05,.355),(.126,.28)]):
        x=s*(1.355+dx); z=1.695+abs(dx)*.28
        a=(x,-.155,z); b=(x+s*.026,-.205,z-length*.54); c=(x+s*.028,-.25,z-length)
        limb('Finger proximal',a,b,.043 if j<3 else .037,.04)
        limb('Finger distal',b,c,.037 if j<3 else .032,.031)
        ell('Finger joint',b,(.047,.044,.049),body=True)
        fingers.append((s,j,a,b,c))
    a=(s*1.22,-.17,1.86); b=(s*1.125,-.23,1.74); c=(s*1.09,-.30,1.61)
    limb('Thumb base',a,b,.07,.064); limb('Thumb tip',b,c,.052,.046)
    fingers.append((s,4,a,b,c))
    hip=(s*.245,.045,1.82); knee=(s*.355,-.125,1.07); ankle=(s*.385,.015,.285)
    limb('Femur',hip,knee,.217,.19)
    limb('Quadriceps',(s*.28,-.085,1.67),(s*.35,-.19,1.17),.16,.145)
    ell('Patella',(s*.355,-.22,1.08),(.128,.095,.145),body=True)
    ell('Knee',knee,(.15,.155,.18),body=True)
    limb('Shin',knee,ankle,.12,.115)
    limb('Calf',(s*.36,.11,.93),(s*.39,.125,.51),.156,.15)
    ell('Ankle',ankle,(.115,.12,.155),body=True)
    ell('Heel',(s*.385,.045,.15),(.145,.175,.13),body=True)
    ell('Foot',(s*.405,-.19,.125),(.183,.32,.115),body=True)
    for j in range(5):
        x=s*(.275+j*.068); y=-.465+ j*.018
        ell('Toe',(x,y,.095),(.047 if j else .061,.12-j*.01,.065),body=True)
        ell('Toenail',(x,y-.029,.148),(.033 if j else .043,.054-j*.005,.012),nail,detail,24,12)

# Head: a single orbital structure, long philtrum and pendant chin.
ell('Cranium',(0,.004,3.945),(.342,.294,.472),body=True)
ell('Occiput',(0,.115,3.89),(.33,.28,.36),body=True)
ell('Jaw',(0,-.071,3.639),(.275,.255,.275),body=True)
ell('Chin',(0,-.219,3.464),(.19,.142,.123),body=True)
for s in (-1,1):
    ell('Cheekbone',(s*.213,-.192,3.841),(.124,.107,.177),body=True)
    ell('Masseter',(s*.222,-.044,3.665),(.109,.19,.185),body=True)
    ell('Brow boss',(s*.125,-.238,4.136),(.167,.090,.067),body=True)
    ell('Ear',(s*.348,.005,3.956),(.088,.07,.151),body=True)
ell('Glabella',(0,-.21,4.192),(.10,.080,.13),body=True)
ell('Nose bridge',(0,-.287,3.852),(.074,.10,.146),body=True)
ell('Nose tip',(0,-.367,3.759),(.097,.103,.073),body=True)
for s in (-1,1):ell('Nasal ala',(s*.083,-.33,3.748),(.059,.073,.046),body=True)
ell('Muzzle',(0,-.247,3.629),(.17,.12,.132),body=True)

bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0]; bpy.ops.object.join()
body=bpy.context.object; body.name='SK_CaveCyclops_Body'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
rem=body.modifiers.new('Continuous sculpt union','REMESH'); rem.mode='VOXEL'; rem.voxel_size=.018
bpy.ops.object.modifier_apply(modifier=rem.name)
sm=body.modifiers.new('Organic surface relaxation','SMOOTH'); sm.factor=1.15; sm.iterations=9
bpy.ops.object.modifier_apply(modifier=sm.name)
# Carve one orbit; the eyelids meet the visible eyeball.
cut=ell('Orbital cavity cutter',(0,-.305,4.028),(.16,.15,.105),mat=None,segments=48,rings=32)
bpy.context.view_layer.objects.active=body
bo=body.modifiers.new('Single orbital socket','BOOLEAN'); bo.operation='DIFFERENCE'; bo.object=cut
bpy.ops.object.modifier_apply(modifier=bo.name); bpy.data.objects.remove(cut,do_unlink=True)
for f in body.data.polygons:f.use_smooth=True
for slot in body.material_slots:
    if slot.material is None: slot.material=skin
# A retained pre-decimation sculpt, hidden from exports and renders.
hi=body.copy(); hi.data=body.data.copy(); source.objects.link(hi); hi.name='SCULPT_Cyclops_Continuous'
de=body.modifiers.new('Display topology budget','DECIMATE'); de.ratio=min(1,62000/max(1,len(body.data.polygons)*2))
bpy.context.view_layer.objects.active=body; bpy.ops.object.modifier_apply(modifier=de.name)

eye=ell('Eye_single',(0,-.319,4.029),(.168,.139,.119),sclera,detail,64,40)
# Circular iris on the convex front of the eye, with geometric radial pigment.
verts=[]; faces=[]; cols=[]; N=128
for ri,r in enumerate([.0,.026,.032,.048,.065,.074,.078]):
    for j in range(N):
        th=j*2*pi/N; x=r*cos(th); z=r*sin(th)
        y=-.319-.140*math.sqrt(max(.001,1-(x/.168)**2-(z/.119)**2))-.001
        verts.append((x,y,4.029+z))
        v=.60+.23*sin(j*1.71)+.16*sin(j*.47+ri*.7)
        c=(.17*v,.112*v,.039*v,1)
        if ri<2:c=(.002,.003,.001,1)
        if ri==6:c=(.033,.026,.012,1)
        cols.append(c)
for k in range(6):
    for j in range(N):faces.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
me=bpy.data.meshes.new('Iris fibres'); me.from_pydata(verts,[],faces); me.materials.append(iris); me.update()
ob=bpy.data.objects.new('Iris_amber',me); detail.objects.link(ob)
ca=me.color_attributes.new(name='IrisPigment',type='FLOAT_COLOR',domain='POINT')
for i,c in enumerate(cols):ca.data[i].color=c
for f in me.polygons:f.use_smooth=True

for upper in (True,False):
    pts=[]; rs=[]
    for i in range(33):
        t=pi*i/32; x=.174*cos(t); z=4.026+(.098 if upper else -.087)*sin(t)
        y=-.337-.064*sin(t)
        pts.append((x,y,z)); rs.append(.020+(.014 if upper else .003)*sin(t))
    tube('Upper eyelid' if upper else 'Lower eyelid',pts,rs,skin)
# Sagging infraorbital folds.
for s in (-1,1):
    for k in range(2):
        pts=[]
        for i in range(18):
            t=i/17; pts.append((s*(.018+.22*t),-.325-.023*sin(pi*t)+.05*t,3.902-k*.031+.041*t))
        tube('Under-eye fold',pts,[.003+.007*sin(pi*i/17) for i in range(18)],skin,sides=8)
    ell('Nostril',(s*.071,-.387,3.724),(.030,.017,.014),crease,detail,24,12)
    tube('Nasolabial fold',[(s*.112,-.342,3.74),(s*.158,-.329,3.68),(s*.172,-.303,3.60)],[.009,.013,.006],skin)
    ell('Ear concha',(s*.377,-.054,3.961),(.038,.011,.080),lip,detail,24,16)
    pts=[(s*(.357+.061*cos(2*pi*i/32)),-.050-.01*sin(2*pi*i/32),3.958+.122*sin(2*pi*i/32)) for i in range(33)]
    tube('Ear helix',pts,.015,skin)
    tube('Tragus',[(s*.349,-.077,3.924),(s*.365,-.08,3.959),(s*.353,-.07,3.99)],.014,skin)

mouth=[]
for i in range(33):
    x=-.157+.314*i/32; q=x/.157
    mouth.append((x,-.35+.044*q*q,3.594-.034*abs(q)**1.7+.004*cos(q*pi*2)))
tube('Mouth closed recess',mouth,[.006+.008*sin(pi*i/32) for i in range(33)],crease)
for upper in (True,False):
    pts=[(x,y-.002,z+(.014 if upper else -.019)) for x,y,z in mouth]
    tube('Upper lip' if upper else 'Lower lip',pts,[.005+(.013 if upper else .019)*sin(pi*i/32) for i in range(33)],lip)
tube('Chin crease',[(-.105,-.325,3.493),(0,-.352,3.481),(.10,-.325,3.493)],[.003,.006,.003],lip)
# Wrinkles placed on forehead and across sternum; deliberately sparse.
for k in range(3):
    pts=[]
    for i in range(25):
        x=-.21+.42*i/24; z=4.257+k*.037-.022*(x/.21)**2
        y=-.246+ .063*(x/.21)**2 +k*.014
        pts.append((x,y,z))
    tube('Forehead fold',pts,[.0025+.0035*sin(pi*i/24) for i in range(25)],skin,sides=8)
for s in (-1,1):
    tube('Clavicle',[(s*.06,-.253,3.142),(s*.23,-.265,3.137),(s*.43,-.20,3.144)],[.016,.025,.013],skin)
    for k in range(3):
        tube('Neck fold',[(s*.03,-.245,3.32-k*.052),(s*.10,-.246,3.31-k*.052),(s*.16,-.206,3.30-k*.052)],[.003,.006,.003],skin,sides=8)
    for k in range(3):
        tube('Rib plane',[(s*.28,-.257,2.72-k*.11),(s*.37,-.215,2.70-k*.11),(s*.43,-.12,2.72-k*.11)],[.004,.012,.003],skin)
ell('Navel',(0,-.359,2.225),(.027,.011,.020),lip,detail,24,16)
# Healed marks give a little history without adding armour or jewellery.
tube('Old brow scar',[(.183,-.263,4.30),(.168,-.31,4.235),(.158,-.345,4.17)],[.004,.007,.003],scar)
tube('Old shoulder scar',[(-.65,-.22,3.22),(-.72,-.224,3.16),(-.77,-.215,3.08)],[.004,.009,.003],scar)
for s,j,a,b,c in fingers:
    o=ell('Fingernail', (c[0],c[1]-.028,c[2]+.025),(.027 if j<4 else .038,.009,.041),nail,detail,24,12)
    for k in range(2):
        tube('Knuckle crease',[(b[0]-.028,b[1]-.033,b[2]+k*.015),(b[0],b[1]-.043,b[2]-.005+k*.015),(b[0]+.028,b[1]-.033,b[2]+k*.015)],.0028,lip,sides=6)

# Recess the eye and conform surface details to the actual sculpt.
for o in list(detail.objects):
    if o.name.startswith(('Eye_single','Iris_','Upper eyelid','Lower eyelid')):
        bpy.context.view_layer.update()
        for v in o.data.vertices:
            w=o.matrix_world@v.co
            w.x*=.81; w.z=4.029+(w.z-4.029)*.73; w.y+=.030
            v.co=o.matrix_world.inverted()@w
from mathutils.bvhtree import BVHTree
bvh=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
conform=('Forehead fold','Under-eye fold','Nasolabial fold','Clavicle','Neck fold','Rib plane','Old brow scar','Old shoulder scar','Chin crease')
for o in list(detail.objects):
    if o.name.startswith(conform):
        bpy.context.view_layer.update()
        for v in o.data.vertices:
            w=o.matrix_world@v.co
            hit,normal,_,_=bvh.ray_cast(Vector((w.x,-3,w.z)),Vector((0,1,0)))
            if hit is not None:
                w.y=hit.y-.0015
                v.co=o.matrix_world.inverted()@w

# A thin, irregular hide wrap. No speculative armour or weapons.
N=64; R=10; vs=[]; fs=[]
for k in range(R):
    t=k/(R-1)
    for j in range(N):
        a=2*pi*j/N; hem=1.60+.10*sin(3*a+.8)+.045*sin(7*a)
        z=2.025*(1-t)+hem*t
        rx=.447+.052*t; ry=.313+.07*t
        fold=.012*sin(a*15+.3)*t+.007*sin(a*27)*t
        vs.append(((rx+fold)*cos(a),(ry+fold)*sin(a)+.023,z))
for k in range(R-1):
    for j in range(N):fs.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
me=bpy.data.meshes.new('Hide wrap'); me.from_pydata(vs,[],fs); me.materials.append(cloth); me.update()
wrap=bpy.data.objects.new('Hide_wrap',me); base.objects.link(wrap)
so=wrap.modifiers.new('Leather thickness','SOLIDIFY'); so.thickness=.009
su=wrap.modifiers.new('Soft leather','SUBSURF'); su.levels=2
for f in me.polygons:f.use_smooth=True
for offset in (0,.024):
    pts=[(.458*cos(2*pi*i/128),.331*sin(2*pi*i/128)+.023,2.025+offset+.009*sin(i*.22)) for i in range(129)]
    tube('Twisted belt',pts,.014,rope_mat)
for s in (-1,1):
    tube('Belt tie',[(s*.05,-.32,2.038),(s*.04,-.363,1.97),(s*.08,-.385,1.83),(s*.065,-.386,1.72)],.012,rope_mat)
ell('Belt knot',(0,-.333,2.025),(.047,.031,.036),rope_mat,detail)

# Explicit UVs on every export mesh. Body remains an honest concept mesh.
char_objects=[o for c in (base,detail) for o in c.objects if o.type=='MESH']
for o in char_objects:
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    for mod in list(o.modifiers): bpy.ops.object.modifier_apply(modifier=mod.name)
    if not o.data.uv_layers:
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.015)
        bpy.ops.object.mode_set(mode='OBJECT')

# An articulated proxy rig, rigid secondary parts, smooth body weights.
bpy.ops.object.armature_add(enter_editmode=True,location=(0,0,0))
rig=bpy.context.object; rig.name='RIG_CaveCyclops'; move(rig,base)
eb=rig.data.edit_bones; eb.remove(eb[0])
def bone(name,h,t,parent=None):
    b=eb.new(name); b.head=h; b.tail=t
    if parent:b.parent=eb[parent]
    return b
bone('root',(0,0,0),(0,0,.2))
bone('pelvis',(0,.035,1.75),(0,.035,2.05),'root')
bone('spine_01',(0,.035,2.05),(0,.035,2.52),'pelvis')
bone('spine_02',(0,.035,2.52),(0,.06,3.10),'spine_01')
bone('neck',(0,.06,3.10),(0,0,3.52),'spine_02')
bone('head',(0,0,3.52),(0,0,4.32),'neck')
bone('eye',(0,-.319,4.029),(0,-.55,4.029),'head')
for s,label in ((-1,'r'),(1,'l')):
    bone('clavicle_'+label,(0,.06,3.10),(s*.62,.035,3.115),'spine_02')
    bone('upperarm_'+label,(s*.62,.035,3.115),(s*1.01,-.025,2.57),'clavicle_'+label)
    bone('lowerarm_'+label,(s*1.01,-.025,2.57),(s*1.285,-.12,1.995),'upperarm_'+label)
    bone('hand_'+label,(s*1.285,-.12,1.995),(s*1.355,-.17,1.67),'lowerarm_'+label)
    bone('thigh_'+label,(s*.245,.045,1.82),(s*.355,-.125,1.07),'pelvis')
    bone('calf_'+label,(s*.355,-.125,1.07),(s*.385,.015,.285),'thigh_'+label)
    bone('foot_'+label,(s*.385,.015,.285),(s*.405,-.43,.12),'calf_'+label)
    for ss,j,a,b,c in fingers:
        if ss==s:
            bone(f'digit{j}_01_{label}',a,b,'hand_'+label)
            bone(f'digit{j}_02_{label}',b,c,f'digit{j}_01_{label}')
bpy.ops.object.mode_set(mode='OBJECT'); rig.show_in_front=True

def distance_segment(p,a,b):
    v=b-a; t=max(0,min(1,(p-a).dot(v)/v.length_squared)); return (p-(a+t*v)).length
bones={b.name:(b.head_local.copy(),b.tail_local.copy()) for b in rig.data.bones if b.name not in ('root','eye')}
groups={n:body.vertex_groups.new(name=n) for n in bones}
for v in body.data.vertices:
    p=v.co; x,y,z=p; side='l' if x>=0 else 'r'
    if z>3.46:names=['head','neck']
    elif z>3.13 and abs(x)<.34:names=['head','neck','spine_02']
    elif abs(x)>.70 and z>1.1:
        names=['upperarm_'+side,'lowerarm_'+side,'hand_'+side,'clavicle_'+side]
        if z<1.82:names+= [n for n in bones if n.startswith('digit') and n.endswith(side)]
    elif z<1.78:names=['pelvis','thigh_'+side,'calf_'+side,'foot_'+side]
    else:names=['pelvis','spine_01','spine_02','neck','clavicle_'+side,'upperarm_'+side]
    ds=sorted((distance_segment(p,*bones[n]),n) for n in names)[:3]
    weights=[1/(d+.055)**5 for d,n in ds]; total=sum(weights)
    for (d,n),w in zip(ds,weights):groups[n].add([v.index],w/total,'REPLACE')
arm=body.modifiers.new('Cyclops deformation','ARMATURE'); arm.object=rig; body.parent=rig
for o in char_objects:
    if o==body:continue
    center=o.matrix_world @ (sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices))
    if o.name.startswith(('Eye_','Iris_')):bn='eye'
    elif center.z>3.42:bn='head'
    elif o==wrap or o.name.startswith(('Belt','Twisted')):bn='pelvis'
    else:bn=min(bones,key=lambda n:distance_segment(center,*bones[n]))
    g=o.vertex_groups.new(name=bn);g.add(list(range(len(o.data.vertices))),1,'REPLACE')
    m=o.modifiers.new('Rig attachment','ARMATURE');m.object=rig;o.parent=rig

# Restrained idle for inspection, not a production animation pack.
scene=bpy.context.scene; scene.frame_start=1; scene.frame_end=120; scene.render.fps=30
for frame,v in ((1,0),(31,1),(61,0),(91,-1),(120,0)):
    for name,rot in [('spine_02',(v*.008,0,v*.004)),('head',(v*.014,v*.012,0)),('upperarm_l',(0,v*.007,v*.006)),('upperarm_r',(0,-v*.007,-v*.006))]:
        pb=rig.pose.bones[name];pb.rotation_mode='XYZ';pb.rotation_euler=rot;pb.keyframe_insert(data_path='rotation_euler',frame=frame,group=name)
rig.animation_data.action.name='A_Cyclops_Breathing_Preview'
scene.frame_set(1)

# Export only the character; bake maps in a separate optional stage.
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for o in char_objects:o.select_set(True)
os.makedirs(os.path.join(ROOT,'exports'),exist_ok=True)
bpy.ops.export_scene.fbx(filepath=os.path.join(ROOT,'exports','CaveCyclops.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,mesh_smooth_type='FACE',path_mode='AUTO')

# Presentation: a low basalt plinth and an uncluttered photographic background.
bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=1.30,depth=.13,location=(0,0,-.075))
plinth=bpy.context.object;plinth.name='Basalt display plinth';move(plinth,stage);plinth.data.materials.append(stone)
bev=plinth.modifiers.new('Worn rim','BEVEL');bev.width=.042;bev.segments=3
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.15));floor=bpy.context.object;floor.name='Studio floor';move(floor,stage);floor.data.materials.append(material('M_Backdrop',(.017,.022,.025),.9))
def area(name,loc,power,color,size,target):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);stage.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
area('KEY | cool daylight',(3,-4.5,6),1050,(.77,.85,1),4,(0,0,2.5))
area('FILL | warm bounce',(-3,-2,3.4),420,(1,.71,.43),3,(0,0,2.5))
area('RIM | cave opening',(1,2.5,5.5),1550,(.64,.78,1),3,(0,0,2.7))
area('Eye catchlight',(-.9,-3,4.7),85,(1,.88,.71),.65,(0,-.2,4))
world=bpy.data.worlds.new('Cave studio');scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.075,.09,.12,1);world.node_tree.nodes['Background'].inputs[1].default_value=.23
def camera(name,loc,target,lens):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);stage.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;return o
hero=camera('CAM_01_Hero',(5.3,-10.5,4.5),(0,0,2.22),65)
portrait=camera('CAM_02_Portrait',(1.48,-3.5,4.13),(0,-.10,3.90),80)
front=camera('CAM_03_Front',(0,-11,2.4),(0,0,2.22),65)
side=camera('CAM_04_Side',(10,-.2,3.0),(0,0,2.22),60)
scene.camera=hero
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=1500;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False
scene.view_settings.exposure=-.7
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':
        a.spaces.active.region_3d.view_distance=7
        a.spaces.active.region_3d.view_location=(0,0,2.2)
        a.spaces.active.shading.type='MATERIAL'
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
rig.hide_set(True)
stats={'height_m':round(max(v.co.z for v in body.data.vertices),3),'body_vertices':len(body.data.vertices),'body_triangles':sum(len(p.vertices)-2 for p in body.data.polygons),'total_mesh_triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in char_objects),'bones':len(rig.data.bones),'materials':len(set(m.name for o in char_objects for m in o.data.materials if m)),'stage':'concept mesh with proxy rig; manual deformation retopology and UE5 import validation still required'}
with open(os.path.join(ROOT,'asset_report.json'),'w') as f:json.dump(stats,f,indent=2)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'CaveCyclops.blend'))
os.makedirs(os.path.join(ROOT,'renders'),exist_ok=True)
for cam,name in ((hero,'01_hero'),(portrait,'02_portrait'),(front,'03_front'),(side,'04_side')):
    scene.camera=cam;scene.render.filepath=os.path.join(ROOT,'renders',name+'.png');bpy.ops.render.render(write_still=True)
scene.camera=hero
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'CaveCyclops.blend'))
print('CYCLOPS_COMPLETE',json.dumps(stats))
