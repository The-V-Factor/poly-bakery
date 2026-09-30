# 独眼巨人 · A1 mini 打印版

**17 cm 高，一整件，一盘打印，不用拼装。** 原来的 20 cm 模型保留在上一级目录。

## 怎么打印？

1. 用 Bambu Studio 打开 **[CaveCyclops_A1mini_PETG_170mm.3mf](CaveCyclops_A1mini_PETG_170mm.3mf)**，选择打开为项目，保留里面的设置。
2. 确认机器是 **A1 mini / 0.4 mm 喷嘴**，耗材是你实际使用的 **PETG**，打印板是**纹理 PEI 板**。
3. 点击“切片单盘”，看一眼预览，再发送打印。使用其他品牌或型号的 PETG 时，选择对应耗材预设后重新切片。
4. 打完等板子冷却，再取下模型。树状支撑分小段拆，手指附近不要用力扭。

当前配置预计 **5 小时 22 分钟，用料约 85 g**，包含支撑。实际时间和耗材会随耗材预设及打印设置改变。

## 已经替你设置好了

| 项目 | 设置 |
| --- | --- |
| 模型尺寸（含底座） | 约 115 × 99 × 170 mm |
| 材料 | Generic PETG，单色 |
| 层高 / 外墙 / 填充 | 0.16 mm / 3 层 / 15% |
| 支撑 | 自动树状支撑，允许从模型表面生长 |
| 支撑接触间隙 | 上下各 0.24 mm |
| 底边 | 5 mm 外侧 brim，帮助粘住打印板 |
| 温度 | 喷嘴 255°C / 纹理 PEI 板 70°C |

![打印模型预览](preview.png)

## 文件和检查结果

- `.3mf` 是日常使用的打印工程，包含模型、设置和已验证的切片结果。
- [CaveCyclops_170mm.stl](CaveCyclops_170mm.stl) 是备用模型，不包含打印设置。
- [validation.json](validation.json) 记录尺寸、网格检查、原文件校验值和切片结果。
- Bambu Studio 2.08.02.61 实际切片通过：1 盘、1 个模型、1062 层、自动修补 0 次，最高打印层 169.96 mm；首层连同支撑和底边均在 180 × 180 mm 内。唯一提示是该机型不支持传统延时摄影。
- 模型和 STL 重新导入均为单个封闭实体，没有开放边、非流形边或零面积面。**尚未实物试打，也没有完成全表面最小壁厚认证。**

需要重新生成时，在仓库根目录运行：

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --python cyclops/printing/build_a1mini.py
python3 cyclops/printing/prepare_a1mini.py --slice
```

脚本使用本机 Blender 和 Bambu Studio 的工厂预设，不连接打印机；只重建本目录产物，不改原游戏模型和 20 cm 打印主文件。
