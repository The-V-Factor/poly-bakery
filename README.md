# 3D 模型项目

按模型组织源文件、制作脚本、预览和交付物。打开具体模型的说明，查看尺寸、制作步骤及验证范围。

| 模型 | 说明 | 可编辑场景 | 预览 | 打印文件 |
| --- | --- | --- | --- | --- |
| 洞穴独眼巨人 | [模型与游戏资产](cyclops/README.md) · [打印说明](cyclops/printing/README.md) | [CaveCyclops.blend](cyclops/CaveCyclops.blend) | [全身](cyclops/renders/01_hero.png) | [printing/](cyclops/printing/) |
| 惊奇泡泡 | [制作与打印说明](paopao/README.md) | [Jingqi_Paopao.blend](paopao/Jingqi_Paopao.blend) | [彩色](paopao/renders/01_color.png) | [printing/](paopao/printing/) |
| 星舰一体版 | [制作与打印说明](starship/README.md) | [Starship_FullStack.blend](starship/Starship_FullStack.blend) | [完整组合](starship/renders/01_full_stack.png) | [printing/](starship/printing/) |
| 星舰分体版 | [装配与打印说明](starship/separable/README.md) | [Starship_Separable.blend](starship/separable/Starship_Separable.blend) | [拆分](starship/separable/renders/02_separated.png) | [printing/](starship/separable/printing/) |
| 星舰内部与发射动画 | [播放说明](starship/separable/animation.md) | [Starship_Interior_Animation.blend](starship/separable/Starship_Interior_Animation.blend) | [内部](starship/separable/renders/animation_interior.png) · [20 秒视频](starship/separable/renders/Starship_Flight.mp4) | [A1 mini 可拆外壳四盘](starship/separable/printing/a1mini/README.md) |

## 目录约定

```text
3d_modes/
├── README.md          # 项目导航
├── cyclops/           # 独眼巨人：原根目录中的模型、脚本和资源
│   ├── exports/       # 游戏版 Blender、FBX、GLB、动画
│   ├── textures/      # PBR 贴图
│   ├── renders/       # 展示预览
│   └── printing/      # 打印模型、预览、脚本及验证记录
├── paopao/            # 惊奇泡泡
│   ├── renders/
│   └── printing/      # 几何、切片工程、预设及验证记录
├── starship/          # 星舰一体版
│   ├── renders/
│   ├── printing/
│   └── separable/     # 分体版本及其脚本、预览和打印文件
└── reports/           # 暂未确定所属模型的历史记录
```

各模型的主 `.blend`、制作脚本和 README 放在该模型目录；派生文件按用途放入 `renders/`、`printing/`、`exports/`、`textures/`。只创建实际需要的目录。验证 JSON 保留在对应产物附近，`.blend1` 备份保留在原场景旁。

星舰分体版的脚本复用上一级一体版脚本，因此继续放在 `starship/separable/`。

## 资产版本管理

Git 保存“用了哪些模型”的小纸条，B2 保存真正的模型和图片。**做完先 `push`，换版本后 `pull`，不确定就 `status`。** 第一次使用先看 [简单使用说明](docs/assets.md)。

```bash
.venv/bin/python tools/assets.py status  # 看看哪些模型改过了
.venv/bin/python tools/assets.py push    # 保存模型后上传，成功后再提交 Git
.venv/bin/python tools/assets.py pull    # 换电脑或切换 Git 版本后取回模型
```

Windows 用户把 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。

## 运行脚本

脚本需要 Blender 的 Python 环境。以本机 macOS 安装位置为例，从项目根目录运行：

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --python cyclops/build_cyclops.py
```

脚本按自身所在目录定位输入和输出；重新运行会覆盖对应模型的派生文件。独眼巨人的完整执行顺序见 [制作说明](cyclops/README.md)，其他模型见各自 README。

## 整理说明

- 原根目录的独眼巨人资产整体移至 `cyclops/`，内部相对路径保持不变；泡泡和星舰目录保持原样。
- 原根目录的 `result.json` 移至 [reports/result.json](reports/result.json)。它只记录一次成功的工具执行结果，没有模型标识，不能作为任何模型的验收记录。
- 独眼巨人的现有 Blender 场景保留了历史渲染输出路径 `/Users/lam/odyssey/renders/04_side.png`。在界面中渲染并写入文件前，将输出目录设为当前模型的 `renders/`；打印预览可设为 `printing/`。制作脚本会自行设置渲染路径。游戏版场景的贴图已内嵌，显示不依赖其历史绝对路径。
