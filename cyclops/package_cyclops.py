"""Bake portable PBR maps, make LOD exports, and verify the FBX round trip."""
import bpy, bmesh, os, json, math
from mathutils import Vector
ROOT=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT,'CaveCyclops.blend'))
scene=bpy.context.scene;scene.frame_set(1)
rig=bpy.data.objects['RIG_CaveCyclops'];rig.hide_set(False)
rig.animation_data_clear()
for b in rig.pose.bones:b.rotation_euler=(0,0,0)
scene.cycles.samples=8
texdir=os.path.join(ROOT,'textures');os.makedirs(texdir,exist_ok=True)
objects=[o for c in ('01_CHARACTER','02_ANATOMICAL_DETAILS') for o in bpy.data.collections[c].objects if o.type=='MESH']
# Keep eyes separate for their glossy response and dedicated UV area.
eyes=[o for o in objects if o.name.startswith(('Eye_single','Iris_'))]
meshes=[o for o in objects if o not in eyes]
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['SK_CaveCyclops_Body'];bpy.ops.object.join()
body=bpy.context.object;body.name='SK_CaveCyclops_LOD0'
for slot in body.material_slots:
    if slot.material is None:slot.material=bpy.data.materials['M_Cyclops_Skin | ash, ochre, weathered']

def unwrap(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.2,island_margin=.004)
    bpy.ops.object.mode_set(mode='OBJECT')

def bake(o,prefix,size):
    unwrap(o)
    mats=list(set(s.material for s in o.material_slots if s.material))
    imgs={}
    for kind in ('BaseColor','Roughness','NormalGL'):
        image=bpy.data.images.new(prefix+'_'+kind,width=size,height=size,alpha=False)
        if kind!='BaseColor':image.colorspace_settings.name='Non-Color'
        imgs[kind]=image
        saved=[]
        for m in mats:
            nt=m.node_tree;ns=nt.nodes;ls=nt.links
            n=ns.new('ShaderNodeTexImage');n.image=image;ns.active=n
            output=next(n for n in ns if n.type=='OUTPUT_MATERIAL')
            p=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
            if kind=='BaseColor':
                old=output.inputs['Surface'].links[0].from_socket
                em=ns.new('ShaderNodeEmission')
                if p.inputs['Base Color'].is_linked:ls.new(p.inputs['Base Color'].links[0].from_socket,em.inputs['Color'])
                else:em.inputs['Color'].default_value=p.inputs['Base Color'].default_value
                ls.new(em.outputs[0],output.inputs['Surface']);saved.append((m,old,em,output))
        scene.render.bake.margin=12;scene.render.bake.use_clear=True
        scene.render.bake.use_selected_to_active=False
        bpy.ops.object.bake(type={'BaseColor':'EMIT','Roughness':'ROUGHNESS','NormalGL':'NORMAL'}[kind])
        image.filepath_raw=os.path.join(texdir,image.name+'.png');image.file_format='PNG';image.save()
        for m,old,em,out in saved:
            m.node_tree.links.new(old,out.inputs['Surface']);m.node_tree.nodes.remove(em)
        print('BAKED',image.name,flush=True)
    m=bpy.data.materials.new('M_'+prefix+'_PBR');m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');ns=m.node_tree.nodes;ls=m.node_tree.links
    for kind,socket in (('BaseColor','Base Color'),('Roughness','Roughness')):
        n=ns.new('ShaderNodeTexImage');n.image=imgs[kind];ls.new(n.outputs['Color'],p.inputs[socket])
    n=ns.new('ShaderNodeTexImage');n.image=imgs['NormalGL'];nm=ns.new('ShaderNodeNormalMap')
    ls.new(n.outputs['Color'],nm.inputs['Color']);ls.new(nm.outputs[0],p.inputs['Normal'])
    o.data.materials.clear();o.data.materials.append(m)
    for f in o.data.polygons:f.material_index=0
    # Explicit DirectX tangent-space normal for Unreal, derived from the baked image.
    src=imgs['NormalGL'];pixels=list(src.pixels[:])
    for i in range(1,len(pixels),4):pixels[i]=1-pixels[i]
    dx=bpy.data.images.new(prefix+'_NormalDX',width=size,height=size,alpha=False)
    dx.colorspace_settings.name='Non-Color';dx.pixels.foreach_set(pixels)
    dx.filepath_raw=os.path.join(texdir,dx.name+'.png');dx.file_format='PNG';dx.save()
    return m

bake(body,'T_Cyclops',2048)
# Iris and sclera share one material atlas while retaining the eye bone.
bpy.ops.object.select_all(action='DESELECT')
for o in eyes:o.select_set(True)
bpy.context.view_layer.objects.active=eyes[0];bpy.ops.object.join();eye=bpy.context.object;eye.name='SK_Cyclops_Eye'
bake(eye,'T_CyclopsEye',512)

# Enforce triangles and a maximum of four normalized influences.
for o in (body,eye):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    t=o.modifiers.new('Explicit triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=t.name)
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.dissolve_degenerate(bm,dist=1e-7,edges=list(bm.edges))
    degenerate=[f for f in bm.faces if f.calc_area()<1e-12]
    if degenerate:bmesh.ops.delete(bm,geom=degenerate,context='FACES_ONLY')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(o.data);bm.free();o.data.update()
    bpy.ops.object.vertex_group_limit_total(limit=4)
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)

def select_export():
    bpy.ops.object.select_all(action='DESELECT')
    for o in (body,eye,rig):o.select_set(True)
    bpy.context.view_layer.objects.active=rig

def export(filename):
    select_export()
    bpy.ops.export_scene.fbx(filepath=os.path.join(ROOT,'exports',filename),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,mesh_smooth_type='FACE',path_mode='RELATIVE')

export('CaveCyclops.fbx')
select_export()
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT,'exports','CaveCyclops.glb'),export_format='GLB',use_selection=True,export_animations=False,export_skins=True)
counts={}
for level,ratio in ((0,1),(1,.5),(2,.23)):
    if level:
        mod=body.modifiers.new('LOD preview','DECIMATE');mod.ratio=ratio
    dg=bpy.context.evaluated_depsgraph_get(); dg.update()
    counts['LOD'+str(level)]=sum(len(p.vertices)-2 for o in (body,eye) for p in o.evaluated_get(dg).data.polygons)
    if level:
        export(f'CaveCyclops_LOD{level}.fbx');body.modifiers.remove(mod)

for image in bpy.data.images:
    if image.name.startswith('T_Cyclops') and image.has_data:image.pack()
scene.camera=bpy.data.objects['CAM_01_Hero']
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'exports','CaveCyclops_Game.blend'))

report={'triangles':counts,'bones':len(rig.data.bones),'material_slots':2,'body_texture_resolution':2048,'eye_texture_resolution':512,'uv_layers':{o.name:len(o.data.uv_layers) for o in (body,eye)},'max_influences':max(len(v.groups) for o in (body,eye) for v in o.data.vertices),'unweighted_vertices':sum(not v.groups for o in (body,eye) for v in o.data.vertices),'ue5_editor_tested':False}
# Round trip into a clean scene checks that files contain a usable rig and mesh.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT,'exports','CaveCyclops.fbx'))
report['fbx_roundtrip']={'armatures':len([o for o in bpy.data.objects if o.type=='ARMATURE']),'meshes':len([o for o in bpy.data.objects if o.type=='MESH']),'bones':sum(len(o.data.bones) for o in bpy.data.objects if o.type=='ARMATURE')}
report['fbx_roundtrip']['height_m']=round(max((o.matrix_world@v.co).z for o in bpy.data.objects if o.type=='MESH' for v in o.data.vertices),3)
assert report['unweighted_vertices']==0
assert report['fbx_roundtrip']['armatures']==1 and report['fbx_roundtrip']['meshes']==2
assert report['max_influences']<=4
with open(os.path.join(ROOT,'export_validation.json'),'w') as f:json.dump(report,f,indent=2)
print('PACKAGE_COMPLETE',json.dumps(report),flush=True)
