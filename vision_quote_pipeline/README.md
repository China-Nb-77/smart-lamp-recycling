# Vision Quote Pipeline Skeleton

一个可直接改造的 Python 项目骨架，覆盖这条链路：

**SAM3 标注导出 YOLO -> OpenCLIP embedding -> FAISS 检索 -> 规则报价**

这版已经对接了你上传的 `sam3-main.zip` 所对应的调用方式，支持：

1. 通过本地 `sam3-main/` 源码直接加载 `build_sam3_image_model`
2. 用 `Sam3Processor` 对单张图片做文字提示分割
3. 从分割结果中选出最佳 mask 并转成 YOLO bbox
4. 若本机没有装好 SAM3 依赖或没有 checkpoint，则自动回退为读取本地 mask 文件

## 目录

```text
vision_quote_pipeline/
  data/
    raw/                  # 原始图片与元数据
    annotations_yolo/     # 导出的 YOLO 标签
    vector_store/         # FAISS 索引与 metadata
  src/
    adapters/
      sam3_adapter.py     # 对接 sam3-main 的适配层
    cli/
      main.py             # 命令行入口
    embedding/
      openclip_embedder.py
    indexing/
      faiss_store.py
    pricing/
      rule_engine.py
    utils/
      io.py
      yolo.py
      crop.py
      metadata.py
  config.py
  requirements.txt
  .env.example
```

## 安装

```bash
cd vision_quote_pipeline
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

如果你要真正调用 SAM3，还需要准备两样东西：

1. 你的 `sam3-main` 源码目录
2. 可用的 SAM3 checkpoint，或者已经通过 Hugging Face 登录并获权下载

## 一、从 SAM3 结果导出 YOLO 标签

### 方案 A：直接读取已有 mask

```bash
python -m src.cli.main prepare-yolo \
  --images-dir data/raw/images \
  --masks-dir data/raw/masks \
  --output-dir data/annotations_yolo \
  --class-id 0
```

### 方案 B：直接调用 sam3-main 做推理

```bash
python -m src.cli.main prepare-yolo \
  --images-dir data/raw/images \
  --output-dir data/annotations_yolo \
  --class-id 0 \
  --sam3-root /absolute/path/to/sam3-main \
  --sam3-checkpoint /absolute/path/to/sam3.pt \
  --text-prompt "lamp" \
  --device cuda
```

说明：

- `--sam3-root` 指向你解压后的 `sam3-main/`
- `--sam3-checkpoint` 可选；不传时会尝试走 SAM3 仓库里的 Hugging Face 下载逻辑
- `--text-prompt` 是 SAM3 文字提示，比如 `lamp`、`chandelier`、`package box`
- `--device` 可设为 `cpu` 或 `cuda`

输出：

- `labels/*.txt`
- `images/*.jpg`
- `dataset.yaml`

## 二、构建 OpenCLIP 向量库

假设你已有商品元数据 CSV：

```csv
id,image_path,material,size_mm,process,base_price
SKU001,data/raw/images/0001.jpg,metal+glass,600,paint,399
SKU002,data/raw/images/0002.jpg,metal,450,plating,259
```

运行：

```bash
python -m src.cli.main build-index \
  --csv data/raw/products.csv \
  --index-dir data/vector_store
```

输出：

- `data/vector_store/faiss.index`
- `data/vector_store/metadata.parquet`

## 三、检索 + 规则报价

```bash
python -m src.cli.main quote \
  --query-image data/raw/images/0001.jpg \
  --index-dir data/vector_store \
  --top-k 5 \
  --material metal+glass \
  --size-mm 600 \
  --process paint
```

输出内容：

- topK 相似样本
- 相似度
- 规则调整项
- 最终建议报价
- `last_quote.json`

## 四、SAM3 真实适配器说明

`src/adapters/sam3_adapter.py` 现已按你上传仓库的 API 对接：

- `from sam3.model_builder import build_sam3_image_model`
- `from sam3.model.sam3_image_processor import Sam3Processor`
- `processor.set_image(image)`
- `processor.set_text_prompt(prompt=..., state=...)`

适配器当前策略：

1. 如果 `sam3-root` 可用，则优先走真实 SAM3 推理
2. 取分数最高的 mask 作为当前目标前景
3. 若推理失败，则自动尝试读取已有 mask 文件
4. 读取顺序支持：
   - 同名 `.png/.jpg`
   - `xxx.mask.png`
   - `xxx_mask.png`
   - `../masks/xxx.png`
   - `../annotations/xxx.png`

## 五、建议的数据规范

### 图片商品表 `products.csv`

必备字段：

- `id`
- `image_path`
- `material`
- `size_mm`
- `process`
- `base_price`

可选字段：

- `style`
- `category`
- `quantity`
- `urgent`
- `region`

## 六、当前骨架默认规则

- 基于相似样本加权平均价
- 材质修正
- 尺寸修正
- 工艺修正
- 加急修正

后续你可以把 `src/pricing/rule_engine.py` 换成你自己的真实报价规则。

## 七、注意事项

1. SAM3 官方仓库依赖较重，通常需要较新的 PyTorch、Python 与 CUDA。
2. 这个骨架项目没有把 SAM3 强行写进 `requirements.txt`，因为很多环境会单独装 SAM3。
3. 若你本机只是想先跑通流程，可以直接先准备 mask 文件，不一定要先把 SAM3 模型跑起来。
