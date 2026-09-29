# 瞪眼泡泡 / 惊奇泡泡

根据《梦幻西游》手游官网的[惊奇泡泡图鉴](https://my.163.com/chongwu/pets/98.html)重新建模，参考[官方立绘](https://my.res.netease.com/pc/zt/20210527183342/data/role/98.png)及[官方动态展示](https://my.res.netease.com/2022/zhlgif/98_cg_pt_1.gif)。保留黄色球体、大白眼、棕色瞳孔、拱起眉毛和浅下弯嘴型；采用基础造型，没有添加装饰头饰。属于依据参考制作的模型，并非游戏原始资产。

成品约 **宽 88 × 深 76.6 × 高 85 mm**。底部有小平面，方便桌面摆放。表情都是立体几何，单色打印也保留起伏。

## Blender 文件

- [Jingqi_Paopao.blend](Jingqi_Paopao.blend)：彩色展示模型，眼白、瞳孔、眉毛等可单独修改材质。
- [Paopao_Print.blend](printing/Paopao_Print.blend)：打印几何，默认显示两半平放布局；完整雕塑保留为隐藏对象。
- [彩色预览](renders/01_color.png)、[正面预览](renders/02_front.png)、[单色完整预览](renders/03_print_complete.png)、[前后半球预览](renders/04_print_halves.png)。

## A1 mini 推荐使用的文件

已使用本机 Bambu Studio 02.08.02.61，按 **A1 mini、0.4 mm 喷嘴、Generic PLA、纹理 PEI 板**生成了两份独立切片工程：

| 工程文件 | 内容 | 软件估算时间 | 估算用料 |
|---|---|---|---|
| [A1mini_Front_PLA_04.3mf](printing/A1mini_Front_PLA_04.3mf) | 有表情的前半球 | 约 2 小时 26 分 | 48.6 g |
| [A1mini_Back_PLA_04.3mf](printing/A1mini_Back_PLA_04.3mf) | 后半球 | 约 2 小时 13 分 | 47.0 g |

工艺为 **0.16 mm 层高、3 层墙、15% 陀螺填充、关闭支撑**。接合面朝下，表面朝上；每半占地约 88 × 85 mm，前半高约 39.6 mm，后半高约 37 mm。按两盘分别打印，保持 100% 比例。

1. 用 Bambu Studio **打开工程**，保留工程中的模型方向和参数；如果只导入几何，参数不会完整带入。
2. 核对实际机器确为 A1 mini，喷嘴确为 0.4 mm。耗材和打印板需与实物一致；尚未确认你的耗材及喷嘴，工程中的 PLA 和 0.4 mm 属于明确假设。
3. 若使用拓竹 PLA Basic，可选对应耗材预设；其他品牌按实际选预设。改变材料、板材或喷嘴后，重新切片。
4. 查看逐层预览，确认表情和第一层完整，再点击“打印单盘”，选择实际耗材位置。保留热床调平；延时摄影先关闭。
5. 冷却后取下。前后两半先对齐底部的小平面，再沿接合面粘合。两半没有卡扣或插销，采用平面胶合；使用适用于 PLA 的胶，按胶的使用说明操作。
6. 可用黄色 PLA 打印，再将眼白涂白、瞳孔和眉毛嘴巴涂深棕色。**工程是单色打印，Blender 的彩色材质不会自动变成 AMS 多色打印。**

上述为切片估算，实际耗时、用料及质量由机器和材料决定。没有连接打印机或启动打印，也尚未实物试打。

## 通用几何文件

| 模型 | 明确毫米单位的 3MF | STL（毫米坐标） |
|---|---|---|
| 前半球 | [Paopao_Front.3mf](printing/Paopao_Front.3mf) | [Paopao_Front.stl](printing/Paopao_Front.stl) |
| 后半球 | [Paopao_Back.3mf](printing/Paopao_Back.3mf) | [Paopao_Back.stl](printing/Paopao_Back.stl) |
| 一体完整雕塑 | [Paopao_Complete.3mf](printing/Paopao_Complete.3mf) | [Paopao_Complete.stl](printing/Paopao_Complete.stl) |

通用文件只含几何，不含打印机参数。一体雕塑未做切片验证，球体下部及面部悬垂需另行处理；A1 mini 首次打印优先使用前后分半工程。

## 验证与源文件

- [网格验证](printing/validation.json)：三份几何均为单连通封闭网格，开放边、非流形边、退化面为 0；STL 导出后重新导入检查通过。
- [切片验证](printing/slice_validation.json)：前后半球在 A1 mini 范围内完成切片，无支撑，G-code 校验和正确。切片器另有传统延时摄影不支持提示，未发现其他切片警告。实际打印质量尚未验证。
- `build_paopao.py`：本地 Blender 建模、几何检查、导出与渲染脚本。
- `prepare_slice_profiles.py`：解析 Bambu Studio 随程序附带的公开预设，补齐继承项和机器 G-code；不使用用户账号或设备配置。
- `printing/profiles/`：此次验证使用的完整预设。

Blender 内部使用米、界面显示毫米，几何 STL/3MF 已按毫米导出；不要用默认导出倍率覆盖打印文件。重新执行建模脚本会重置几何验证记录，需重新切片后更新切片验证结果。
