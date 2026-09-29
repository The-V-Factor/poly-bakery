# A1 mini 打印这套星舰

使用 **0.4 mm 喷嘴 + PETG**。装好仍约 **20 cm 高**，打印时分开放，每件都低于 A1 mini 的 18 cm 高度限制。

![取下前壳看内部](opened.png)

## 打开哪个文件

用 Bambu Studio 打开 **[四盘打印工程](Starship_A1mini_PETG_4plates.3mf)**。里面已经选好 A1 mini、0.4 mm 喷嘴和 Generic PETG。

1. **第 1 盘：先试松紧。** 小插销插进中间的孔，看看能不能轻轻拔出来。中间孔对应模型，另外两个孔用来比较松紧。
2. **第 2 盘：星舰。** 后壳、可拆前壳、储箱内芯、货舱件。
3. **第 3 盘：助推器。** 后壳、可拆前壳、储箱内芯。
4. **第 4 盘：底座。**

先看切片预览，再打印当前盘。**不要把整箭装配在一起后送去打印，也不要自动缩小整套零件。**

## 打好怎么装

等零件冷却后，小心去掉支撑和底边。喷口、插销和小翼片处慢慢拆。

- 内部件背面是平的，用少量适合 PETG 的胶粘到后壳里的平面支座上。
- 对准前壳的 4 个小插销，轻轻合上。**前壳不要上胶**，以后可以取下来查看内部。
- 星舰插到助推器上，再放到底座里。

插销太紧时先清掉支撑残留、轻微打磨，再试。不要硬压。太松时先停下，调整配合尺寸后重打试配件；不要直接批量打印整套。

## 和动画版有什么不同

这次打印版也有储箱、输送管路和货舱。为了适合 0.4 mm 喷嘴，外壳按 1.4 mm、管路按 1.2 mm 直径设计；内部件背面做平，便于放在热床上打印。颜色可在打印后自己涂，工程默认单色，不要求 AMS。

它是静态科普模型，尺寸和内部布局有简化。原来的展示版、动画版和旧打印件都保留着。

## 先试一小盘

**还没实物试打，先打印第 1 盘，确认插销能轻轻插拔。** 最细小的喷口细节用 0.4 mm 喷嘴打印会比渲染图粗糙，拆支撑时慢一点。

第 1 盘预计约 14 分钟；四盘合计约 5.5 小时、46 g PETG。这是切片器的估算。

需要自己改模型，可打开 [可编辑打印模型](Starship_Opening_Print.blend)。它是装配好的样子；打印时用上面的四盘 3MF。

<details>
<summary>查看打印参数、检查记录和重新生成命令</summary>

采用 Bambu Studio 自带的 Generic PETG 配置：喷嘴 255°C、纹理 PEI 板 70°C，0.16 mm 层高、3 层墙、15% 填充、树状支撑和 5 mm 外侧底边。实际温度请以耗材厂商建议和你自己的校准结果为准。这里没有向打印机发送任务。

[validation.json](validation.json) 记录网格、尺寸、接口和切片检查。

10 个 STL 已重新导入检查，四盘已用 Bambu Studio 2.8.2 实际切片，无自动网格修补。插销单边间隙采样为 0.148–0.151 mm，前后壳没有相交。切片仅保留“传统延时摄影不支持”的提示；工程不依赖延时摄影。

开发时，在项目根目录重新生成：

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python starship/separable/build_print_a1mini.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python starship/separable/verify_print_a1mini.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python starship/separable/preview_print_a1mini.py
python3 starship/separable/prepare_a1mini.py --slice
```

这会覆盖此目录里的派生模型和分盘工程，请先另存自己的修改。需要本机安装 Blender 5.2 和 Bambu Studio。

</details>
