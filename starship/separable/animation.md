# 看星舰内部，再看它起飞

**只想看动画：** 打开 [20 秒视频](renders/Starship_Flight.mp4)。

**想自己转着看：** 用 Blender 打开 [动画模型](Starship_Interior_Animation.blend)。把鼠标放到画面上，按一下 **空格**开始，再按一下暂停。

前 6 秒把外壳切开给你看：**蓝色是液氧箱，橙色是甲烷箱**。星舰上端是货舱，里面放了一个示意卫星。细管子把推进剂送到下方的发动机。然后切到完整外壳，点火、起飞，最后分成两级。

## 想看哪一段，就跳到哪一帧

在底部时间线找到“当前帧”的数字，输入下面的数字，按回车。

| 输入 | 看到什么 |
| --- | --- |
| 72 | 内部储箱和货舱 |
| 192 | 助推器点火 |
| 250 | 整箭离开底座 |
| 305 | 上面级已经点火，两级还没分开 |
| 450 | 两级已经分开 |

想换角度看内部，先停在 **72**。在画面上方点 **视图 → 视角 → 摄像机**（View → Viewpoint → Camera）退出相机，再用鼠标中键拖动旋转。Mac 没有中键时，可在 **Blender → 设置 → 输入**打开“模拟三键鼠标”，然后按住 **Option + 鼠标左键**拖动。看完再点一次“摄像机”回到动画取景。

两级各有一个总控制器：`MOVE_Starship` 和 `MOVE_SuperHeavy`。储箱、管线、发动机和喷焰都跟着它们走。这份文件已经有动画，手动拖动后再切帧会回到动画位置；想自己改动作，请先“另存为”一份。

## 这份模型补了什么

- 两级各有液氧箱、甲烷箱，带封闭的圆顶封头和分隔空间。
- 有主要输送管路、发动机支撑环和支架，以及上面级货舱。
- 前半段使用剖开的外壳；发射时换回完整外壳。内部零件始终保留。
- 动画顺序是助推器点火、整箭起飞、上面级点火、两级分离。底座留在原地。

这是**科普示意模型**。液氧/甲烷推进剂、两级关系、现有 6/33 台发动机配置，以及“上面级先点火、再分离”的热分级关系有公开资料依据。储箱尺寸和间距、独立封头、管线路径、支架、货舱卫星、喷焰和运动轨迹是为了讲清楚原理做的近似，不是工程图，也不对应某次真实飞行。没有加入回收、着陆或精确轨道仿真。

动画里的颜色帮助区分部件，不是液体真实外观；20 秒是压缩后的演示时间。原来的展示和打印文件保持原样；打印用的 D 形插接套没有带进动画，托座换成了方便看清点火的开放支架。

公开参考：[SpaceX 星舰介绍](https://www.spacex.com/vehicles/starship/)、[NASA 第三次试飞说明](https://www.nasa.gov/directorates/esdmd/artemis-campaign-development-division/human-landing-system-program/nasa-artemis-mission-progresses-with-spacex-starship-test-flight/)、[NASA 热分级研究](https://www.nas.nasa.gov/SC24/research/project24.php)。

## 需要重新生成时

普通观看不用运行命令。制作脚本使用 **Blender 5.2** 的 Python API；已在 **5.2.1 LTS** 验证。没有额外插件、外部贴图或流体缓存。

在项目根目录运行这一条，会重新生成动画模型、5 张预览和完整视频，覆盖本次动画的派生文件：

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python starship/separable/build_animation.py -- --render all
```

只想快速生成模型和图片，把最后的 `all` 改成 `previews`。只生成模型可用 `none`。如果改过模型，先另存为其他文件再运行。

重新打开文件并检查结构、480 帧动作、喷焰跟随和原文件哈希：

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python starship/separable/build_animation.py -- --verify-only
```

[验证记录](animation_validation.json) 保留了原来 16 个模型/打印文件的校验值、4 个储箱的闭合检查和动画时序检查。它不代表做过工程或实物验证。

视频、图片和 `.blend` 都交给 B2，Git 只收脚本、说明和引用清单。**本次新增资产已上传 B2**，换电脑后按项目说明运行 `assets.py pull` 即可取回。以后修改资产，照常先 `assets.py push`，成功后再提交 Git。
