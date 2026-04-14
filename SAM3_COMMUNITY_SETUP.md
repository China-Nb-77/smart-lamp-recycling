# SAM3 Community Checkpoint Setup

本仓库现在可以直接加载社区镜像的 `SAM3` checkpoint，包括 `.safetensors`。

推荐权重来源：

- `AEmotionStudio/sam3`
- 默认文件名：`sam3.safetensors`
- 默认下载位置：`artifacts/models/sam3-community/sam3.safetensors`

## 1. 下载社区权重

```bash
python -m image_quote_system.cli download-sam3-community --config-dir configs
```

或使用安装后的脚本入口：

```bash
download-sam3-community --config-dir configs
```

如果需要覆盖已有文件：

```bash
python -m image_quote_system.cli download-sam3-community --config-dir configs --force
```

## 2. 准备 bridge Python

bridge runtime 至少需要：

- `torch`
- `numpy`
- `Pillow`
- `safetensors`
- `sam3` 代码

现在 bridge worker 会把 `SAM3_BRIDGE_WORKDIR` 加入 `sys.path`。这意味着你有两种方式：

1. 在独立环境里 `pip install -e <sam3-main>`
2. 直接把 `SAM3_BRIDGE_WORKDIR` 指到本地 `sam3-main` 源码目录

推荐：

```bash
set SAM3_BRIDGE_PYTHON=C:\venvs\sam3\python.exe
set SAM3_BRIDGE_WORKDIR=C:\Users\LEGION\Desktop\灯泡\sam3-main
set SAM3_CHECKPOINT=C:\Users\LEGION\Desktop\灯泡\artifacts\models\sam3-community\sam3.safetensors
set SAM3_DEVICE=cuda
```

## 3. 运行预标注

```bash
python -m image_quote_system.cli prelabel-sam3 --config-dir configs --raw-dir data/raw --annotation-dir data/annotations --auto-approve --reviewer bridge_smoke
```

## 4. 关于 `SAM3_MODEL_CFG`

本仓库当前使用的 `sam3-main` 代码路径下，`build_sam3_image_model(...)` 不强依赖 `model_cfg`。

- 如果你使用当前仓库里的 `sam3-main`，通常可以不设置 `SAM3_MODEL_CFG`
- 如果你切换到另一个 `sam3` fork，而它仍然要求 `config_path` / `model_cfg`，本仓库依然会把 `SAM3_MODEL_CFG` 透传过去

## 5. 默认配置

`configs/system.yaml` 已经把默认 checkpoint 指向：

```text
artifacts/models/sam3-community/sam3.safetensors
```

下载完成后，如果你不额外覆盖 `SAM3_CHECKPOINT`，系统会优先尝试这一路径。
