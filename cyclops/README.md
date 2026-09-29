# 洞穴独眼巨人 · 第一版资产

方向：以用户提供的两张图为参考，瘦长四肢、厚重肩背、单眼、阴郁人形；原创角色，面向 PC 近距离 Boss 的前期开发。当前为程序化造型与展示原型，不是已经完成电影级精雕、战斗动画验收的最终角色。

## 查看

- `CaveCyclops.blend`：可编辑主场景，分离的身体与细节、隐藏的连续高密度源网格、基础骨骼、4 秒呼吸预览、展示灯光和四台相机。
- `renders/01_hero.png`：全身三分之四视图。
- `renders/02_portrait.png`：头部近景。
- `renders/03_front.png`、`04_side.png`：正面与侧面。
- `renders/05_firelight.png`：低位火光展示。
- `renders/06_export_material_check.png`：烘焙后游戏版本材质检查。
- `renders/07_pose_check.png`：基础绑定姿态检查。

主场景的骨架默认在视口隐藏；在 Outliner 中显示 `RIG_CaveCyclops` 后可进入 Pose Mode。时间轴 1–120 帧、30 fps，播放呼吸预览。基础姿势为低角度 A 字姿势。

## 游戏开发交接

| 文件 | 内容 |
| --- | --- |
| `exports/CaveCyclops_Game.blend` | 合并整理后的游戏版本，2 个网格、2 个材质槽，贴图已打包 |
| `exports/CaveCyclops.fbx` | LOD0 骨骼网格，134,500 三角形 |
| `exports/CaveCyclops_LOD1.fbx` | 简化版本，70,449 三角形 |
| `exports/CaveCyclops_LOD2.fbx` | 简化版本，35,862 三角形 |
| `exports/CaveCyclops.glb` | 自包含的模型、骨骼与 PBR 贴图，方便预览 |
| `exports/A_Cyclops_Breathing.fbx` | 单独的呼吸预览动画 |
| `textures/` | 身体 2048²、眼睛 512² 的 BaseColor / Roughness / NormalGL / NormalDX |
| `export_validation.json` | 实际导出与重新导入验证记录 |

角色约 4.412 米，根骨骼位于原点。共 41 根自定义骨骼，包含手指和单眼骨骼；不是 Unreal Manny 的可直接替换骨架。每顶点最多 3 个非零权重，没有未绑定顶点。LOD 为自动简化版本，尚未对每种战斗动作逐一检验。

## UE5 导入说明

1. 将 `exports/CaveCyclops.fbx` 导入为 Skeletal Mesh。首次导入新建 Skeleton；不要直接指定 Manny Skeleton。导入后核对总高度约 441 cm、正面朝向和法线。
2. 导入 `textures/` 的 BaseColor、Roughness 和 **NormalDX**。BaseColor 使用 sRGB；Roughness 关闭 sRGB；NormalDX 使用法线贴图压缩并关闭 sRGB。Blender / GLB 使用 NormalGL，两者不要同时接入。
3. 建立身体和眼睛两个材质，分别连接对应 Base Color、Roughness、Normal。皮肤 SSS 和眼球的高级折射材质需要在 UE5 中单独调整。
4. LOD1、LOD2 文件用于手动添加对应精度；检查切换距离及轮廓变化。导入呼吸动画时指定第一步创建的 Skeleton。
5. 建立并检查 Physics Asset；本包不包含经 UE5 验证的碰撞体、布料模拟、Control Rig、IK 重定向或战斗逻辑。

已在 Blender 内完成 FBX 导出及重新导入检查，**没有在 UE5 编辑器内运行或验收**。Blender 输出 FBX 7.4；Epic 文档说明其 FBX 管线使用 2020.2，目标引擎版本仍需实际导入确认。

参考：[Epic 官方 FBX Skeletal Mesh Pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-skeletal-mesh-pipeline-in-unreal-engine)。

## 当前边界

- 网格采用连续体素合并与简化，局部细节为独立网格；尚未做针对肩、胯、嘴部表情的手工变形拓扑。
- 已提供基础骨骼和呼吸预览；大幅度攻击、抓握、蹲伏、眨眼和口型仍需进一步绑定与变形修正。
- 材质为程序化皮肤和烘焙 PBR，当前造型与表面精细度仍属于第一版原型，未达到电影写实近景的最终质量。

## 可复现制作脚本

使用 Blender 5.2.1 制作。按以下顺序在当前目录运行脚本：

1. `build_cyclops.py` — 基础网格、细节、骨骼、场景。
2. `polish_cyclops.py` — 眼睑、表面和展示修正。
3. `package_cyclops.py` — UV、PBR 烘焙、FBX/GLB、LOD、重新导入检查。
4. `verify_cyclops.py` — 导出材质和基础姿态检查、独立动画导出。

脚本仅在此目录生成文件，不需要下载外部模型、贴图或账户凭据。
