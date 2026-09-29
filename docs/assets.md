# 模型怎么保存、怎么拿回来？

把它想成两个盒子：

- **Git** 放“小纸条”，写着这个版本用了哪些模型。
- **B2** 放真正的模型和图片。

**做完先 `push`，换版本后 `pull`，不确定就 `status`。**

## 平时只用这三个动作

先在项目目录打开终端。下面的命令适用于 macOS 和 Linux；Windows 用户把 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。

### ① 看看哪些模型改过了

```bash
.venv/bin/python tools/assets.py status
```

它会列出新增、修改或缺少的文件。只是看看，不会上传。

### ② 模型做好、保存后，存到云端

```bash
.venv/bin/python tools/assets.py push
```

等它成功，再像平时一样提交 Git，把 `assets.lock.json` 这张“小纸条”和其他改动一起保存。

第一次上传现有模型，也用这条命令。

### ③ 换电脑或切换 Git 版本后，把模型拿回来

```bash
.venv/bin/python tools/assets.py pull
```

它会按照当前 Git 版本的“小纸条”，把模型放回原来的位置。

如果本地有没上传的修改，它会停下来提醒你。先把这些文件移到项目外保留，再取回；不要直接删掉自己的作品。

上传、下载时，先暂停保存 Blender 文件，等命令结束再继续制作。

## 第一次用这台电脑？先准备一次

已经配置过就跳过这一节。换电脑时需要重新准备。

**1. 安装 Python 3.11+ 和 Git，然后在项目目录运行：**

macOS / Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-assets.txt
```

Windows（PowerShell）：

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-assets.txt
```

**2. 填桶名。** 打开 `.assets.json`，在 `bucket` 中填入 B2 桶名；已经填好就不用改。

**3. 填钥匙。** 在项目里创建 `.assets-local` 文件夹，将 `tools/b2.example.json` 复制到里面并改名为 `b2.json`，填写 `application_key_id` 和 `application_key`。已有文件就不用重新复制。

这份钥匙文件已被 Git 忽略，只留在自己的电脑上，不要发给别人或写进模板。

准备好后：已有云端模型就运行 `pull`；要把本地模型第一次存进云端就运行 `push`。

需要改哪些文件上传、删除引用或排查问题时，再看 [进阶说明](assets-reference.md)。
