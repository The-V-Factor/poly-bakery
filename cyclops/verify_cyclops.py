import bpy,os,json,math
from mathutils import Vector
ROOT=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT,'exports','CaveCyclops_Game.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['RIG_CaveCyclops']
body=bpy.data.objects['SK_CaveCyclops_LOD0'];eye=bpy.data.objects['SK_Cyclops_Eye']
report=json.load(open(os.path.join(ROOT,'export_validation.json')))
report['zero_area_faces']=sum(p.area<1e-12 for o in (body,eye) for p in o.data.polygons)
report['nonfinite_vertices']=sum(not all(math.isfinite(c) for c in v.co) for o in (body,eye) for v in o.data.vertices)
assert report['nonfinite_vertices']==0
assert report['zero_area_faces']==0
scene.camera=bpy.data.objects['CAM_01_Hero'];scene.cycles.samples=32
scene.render.resolution_x=960;scene.render.resolution_y=1200
scene.render.filepath=os.path.join(ROOT,'renders','06_export_material_check.png')
bpy.ops.render.render(write_still=True)
# A moderate elbow/head test; this is not a combat animation acceptance test.
rig.pose.bones['lowerarm_l'].rotation_mode='XYZ';rig.pose.bones['lowerarm_l'].rotation_euler[0]=-.40
rig.pose.bones['head'].rotation_euler[1]=.10
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
evaluated=body.evaluated_get(dg)
report['pose_test']={'description':'left elbow rotation 0.4 rad, head tilt 0.1 rad','finite_vertices':all(all(math.isfinite(c) for c in v.co) for v in evaluated.data.vertices)}
scene.render.filepath=os.path.join(ROOT,'renders','07_pose_check.png');bpy.ops.render.render(write_still=True)
with open(os.path.join(ROOT,'export_validation.json'),'w') as f:json.dump(report,f,indent=2)
# Export the original four-second breathing preview as a separate skeletal animation.
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT,'CaveCyclops.blend'))
rig=bpy.data.objects['RIG_CaveCyclops'];rig.hide_set(False)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=os.path.join(ROOT,'exports','A_Cyclops_Breathing.fbx'),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,axis_forward='-Y',axis_up='Z')
print('VERIFIED',json.dumps(report))
