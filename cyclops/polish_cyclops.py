import bpy,os,math,random
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from math import sin,cos,pi
ROOT=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT,'CaveCyclops.blend'))
scene=bpy.context.scene;scene.frame_set(1)
rig=bpy.data.objects['RIG_CaveCyclops'];body=bpy.data.objects['SK_CaveCyclops_Body']
detail=bpy.data.collections['02_ANATOMICAL_DETAILS'];stage=bpy.data.collections['03_PRESENTATION']
skin=bpy.data.materials['M_Cyclops_Skin | ash, ochre, weathered']
# Replace the applied crease strips with a clean, continuous surface.
remove=('Forehead fold','Under-eye fold','Nasolabial fold','Clavicle','Neck fold','Rib plane','Old brow scar','Old shoulder scar','Chin crease','Upper eyelid','Lower eyelid','Knuckle crease')
for o in list(detail.objects):
    if o.name.startswith(remove):bpy.data.objects.remove(o,do_unlink=True)
for o in detail.objects:
    if o.name.startswith(('Eye_single','Iris_')):
        for v in o.data.vertices:v.co.y+=.040
    if o.name.startswith(('Upper lip','Lower lip')):
        center=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
        for v in o.data.vertices:
            v.co.x*=.91;v.co.z=center.z+(v.co.z-center.z)*.69;v.co.y+=.008

bvh=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
verts=[];faces=[];N=96;R=8
for k in range(R):
    t=k/(R-1)
    for j in range(N):
        a=2*pi*j/N
        xi=.123*cos(a);zi=4.029+(.046 if sin(a)>0 else .039)*sin(a)
        xo=.186*cos(a);zo=4.029+(.133 if sin(a)>0 else .132)*sin(a)
        yi=-.249-.140*math.sqrt(max(.001,1-(xi/.13608)**2-((zi-4.029)/.08687)**2))-.001
        hit,_,_,_=bvh.ray_cast(Vector((xo,-3,zo)),Vector((0,1,0)))
        yo=hit.y+.005 if hit is not None else -.25
        x=xi*(1-t)+xo*t;z=zi*(1-t)+zo*t
        y=yi*(1-t)+yo*t-.009*sin(pi*t)
        verts.append((x,y,z))
for k in range(R-1):
    for j in range(N):faces.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
me=bpy.data.meshes.new('Fleshy single orbital annulus');me.from_pydata(verts,[],faces);me.materials.append(skin);me.update()
o=bpy.data.objects.new('Integrated_eyelids',me);detail.objects.link(o)
for p in me.polygons:p.use_smooth=True
g=o.vertex_groups.new(name='head');g.add(list(range(len(verts))),1,'REPLACE')
m=o.modifiers.new('Rig attachment','ARMATURE');m.object=rig;o.parent=rig

ns=skin.node_tree.nodes;ls=skin.node_tree.links;p=ns.get('Principled BSDF')
# Metre-scaled mottling and pores avoid the stretched, stone-like first-pass bump.
tex=ns.get('Texture Coordinate');noise=ns.get('Noise Texture');fine=ns.get('Noise Texture.001')
ls.new(tex.outputs['Object'],noise.inputs['Vector']);noise.inputs['Scale'].default_value=3.8
ls.new(tex.outputs['Object'],fine.inputs['Vector']);fine.inputs['Scale'].default_value=175
ns.get('Bump').inputs['Strength'].default_value=.20;ns.get('Bump').inputs['Distance'].default_value=.0018
p.inputs['Subsurface Weight'].default_value=.035;p.inputs['Subsurface Radius'].default_value=(.05,.025,.012)
r=ns.get('Color Ramp').color_ramp
r.elements[0].color=(.021,.014,.008,1);r.elements[1].color=(.083,.047,.025,1);r.elements[2].color=(.155,.099,.055,1)
for mat in bpy.data.materials:
    if mat.use_nodes:
        bs=mat.node_tree.nodes.get('Principled BSDF')
        if bs:mat.diffuse_color=bs.inputs['Base Color'].default_value

# A curved sweep keeps the background continuous at portrait camera height.
vs=[];fs=[]
profile=[(-100,-.15),(3,-.15)]
for i in range(1,25):
    a=(pi/2)*i/24;profile.append((3+5*sin(a),-.15+5*(1-cos(a))))
profile.append((8,50))
for y,z in profile:vs.extend([(-100,y,z),(100,y,z)])
for i in range(len(profile)-1):fs.append((i*2,i*2+1,i*2+3,i*2+2))
mesh=bpy.data.meshes.new('Backdrop sweep');mesh.from_pydata(vs,[],fs);mesh.materials.append(bpy.data.materials['M_Backdrop'])
o=bpy.data.objects.new('Curved studio backdrop',mesh);stage.objects.link(o)
for f in mesh.polygons:f.use_smooth=True
bpy.data.objects['Studio floor'].hide_render=True
scene.view_settings.exposure=-.25
scene.cycles.samples=64
# Keep a reproducible rest-pose master with final materials and cameras.
scene.camera=bpy.data.objects['CAM_01_Hero']
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'CaveCyclops.blend'))
for camera,name in (('CAM_01_Hero','01_hero'),('CAM_02_Portrait','02_portrait'),('CAM_03_Front','03_front'),('CAM_04_Side','04_side')):
    scene.camera=bpy.data.objects[camera];scene.render.filepath=os.path.join(ROOT,'renders',name+'.png');bpy.ops.render.render(write_still=True)

# Additional low firelight portrait, without changing the saved neutral master.
for o in stage.objects:
    if o.type=='LIGHT':o.hide_render=True
def light(name,loc,power,color,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);stage.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,3.5))-o.location).to_track_quat('-Z','Y').to_euler()
light('Fire bounce',(-1.5,-2,1.8),520,(1,.27,.055),1.1)
light('Moon edge',(1.5,1.6,5.2),700,(.21,.4,1),2)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.035
scene.camera=bpy.data.objects['CAM_02_Portrait'];scene.render.filepath=os.path.join(ROOT,'renders','05_firelight.png');bpy.ops.render.render(write_still=True)
print('POLISH_COMPLETE',flush=True)
