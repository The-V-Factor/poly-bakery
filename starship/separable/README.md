# 可分体 Starship + Super Heavy

分体结构由三大部分组成：Starship 飞船、Super Heavy 助推器（含热分级环）、独立底座。装配总高约 200 mm，底座直径约 66 mm。原有一体版本保留在上一级目录。

**想看内部和发射动画？** 打开 [动画模型](Starship_Interior_Animation.blend)，按空格播放。也可以直接看 [20 秒视频](renders/Starship_Flight.mp4)。[简单操作说明](animation.md) 写了怎么看储箱、点火和分离。

**A1 mini、0.4 mm 喷嘴、PETG 打印：** 使用 [可拆外壳版的四盘工程](printing/a1mini/Starship_A1mini_PETG_4plates.3mf)，先看 [简单打印说明](printing/a1mini/README.md)。它包含打印用内部结构；下方表格中的旧打印件仍保留。

## 打开与拆开

- [展示模型](Starship_Separable.blend)：有金属材质、隔热瓦和独立发动机。
- [旧版打印模型](printing/Starship_Separable_Print.blend)：三个独立封闭网格，包含全部 39 个简化发动机喷口。
- [拆分预览](renders/02_separated.png)、[星舰六台发动机](renders/03_starship_6_engines.png)、[助推器 33 台发动机](renders/04_booster_33_engines.png)、[打印网格预览](renders/05_print_separated.png)。

展示文件打开时是装配状态。在右上角 Outliner 选择 `MOVE_Starship`，按 **G → Z**，向上拖动即可整级拆开；选择 `MOVE_SuperHeavy` 可把助推器从底座抬起。选择这些控制器按 **Alt+G** 恢复装配位置。请移动控制器，避免只移动某一块隔热瓦或焊缝。

打印文件里直接选择 `PRINT_Starship`、`PRINT_SuperHeavy` 或 `PRINT_Base`，同样按 G → Z 移动，Alt+G 复位。数字小键盘 0 退出相机视图，中键旋转查看。

## 实际结构与模型结构

参考公开的六发动机 Starship 配置：上面级为 3 台较大的真空发动机和 3 台海平面发动机，助推器为 33 台，按 20+10+3 分布。发动机喷管均有几何形状和凹腔，拆级或移除底座后可以查看。热分级环保留在助推器顶部。

参考来源：[SpaceX Starship](https://www.spacex.com/vehicles/starship/)；[NASA 对星舰试飞、33 台助推器发动机和 6 台上面级发动机的说明](https://www.nasa.gov/directorates/esdmd/artemis-campaign-development-division/human-landing-system-program/nasa-artemis-mission-progresses-with-spacex-starship-test-flight/)。

本件是按真实两级关系制作的外形参考模型，不对应特定最新飞行架次或工程图。热分级环、发动机内部和管线有所简化。**D 形环套是为模型拆装设计的接口，不是实箭的分离机构。**

## 旧版打印文件（不含内部件）

| 部件 | 推荐使用明确毫米单位的 3MF | STL（坐标为毫米） |
|---|---|---|
| Starship 飞船 | [Starship.3mf](printing/Starship.3mf) | [Starship.stl](printing/Starship.stl) |
| Super Heavy 助推器 | [SuperHeavy.3mf](printing/SuperHeavy.3mf) | [SuperHeavy.stl](printing/SuperHeavy.stl) |
| 底座 | [Base.3mf](printing/Base.3mf) | [Base.stl](printing/Base.stl) |
| 插头试配件 | [Fit_Male.3mf](printing/Fit_Male.3mf) | [Fit_Male.stl](printing/Fit_Male.stl) |
| 插槽试配件 | [Fit_Female.3mf](printing/Fit_Female.3mf) | [Fit_Female.stl](printing/Fit_Female.stl) |

每个导出件已单独落到 Z=0，便于导入切片器。3MF 只包含几何，不包含打印机参数、支撑或切片结果。Blender 内部使用米，界面显示毫米；不要直接用默认 STL 导出设置覆盖这些文件。

## 装配与配合

1. 先按同一材料、同一打印参数打印一对试配件，检查是否能轻松插入、拔出。
2. 底座放平，将助推器底部放入环形托座。托座支撑箭体周边，发动机尖端与底座顶面名义间隔 2.8 mm。
3. 对齐上面级插头与助推器插槽的 D 形平边，再垂直插入约 3.1 mm。接口环绕发动机舱，不穿过发动机群。
4. 拆卸时扶住下一级，沿轴向拔出。接口为重力插接，没有卡扣锁定；搬运时托住底座和各级。

级间接口名义单边间隙 0.30 mm；在重建后的实际网格上采样 216 个径向位置，间隙为 0.300–0.311 mm。底座与助推器也留出名义单边 0.30 mm 间隙。设备误差、首层扩张、树脂收缩及涂层都会影响配合，试配件不能省略。缩放整个模型会同时缩放间隙。

## 旧版打印条件与验证范围

打印版将细部加厚、并为 39 个喷口制作约 0.85 mm 深的浅凹腔。20 cm 整体尺寸下，助推器喷口的名义壁厚仅约 0.36 mm，普通 0.4 mm 喷嘴可能丢失细节；要表现喷口，优先考虑高精度树脂或小喷嘴 FDM，并在切片预览中逐个检查。

文件没有预制支撑。底座可平放打印；两个箭体的发动机、襟翼和栅格舵需要结合设备安排方向和支撑，不要直接把发动机口当作稳定接触面。去支撑时避免撬断喷管。FDM 填充由切片器设置；树脂若要空心，需另行设计排液和通气孔。

[validation.json](printing/validation.json) 记录各件的连通性、开放边、非流形边、退化面、正体积、STL 重新导入和接口间隙检查。三件主件及试配件均为单连通封闭网格，开放边、非流形边、退化面为 0。39 个喷口的中心射线检查通过。

**尚未进行目标设备切片、完整壁厚认证或实物试打试装。** 网格和间隙检查不能代替打印机校准。

## 再生成

`build_separable.py` 复用上一级 `build_starship.py` 的几何构建段，然后新增分体接口、发动机及控制器，输出到本目录。旧版展示文件用哈希确认未被改写。
