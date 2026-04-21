# Data Layout

`prepare-data` 会自动生成以下内容：

- `data/raw/*.png`: 原始示例图片
- `data/queries/*.png`: 单张推理查询图
- `data/catalog/images/*.png`: 检索库图片
- `data/annotations/records/*.json`: 预标注记录
- `data/annotations/masks/*.png`: 预标注 mask
- `data/annotation_exports/bboxes.jsonl`: bbox 导出
- `data/detection_dataset/`: RT-DETR 训练数据

仓库内只提交 `catalog.csv` 和配置，二进制图片由脚本生成，避免把示例素材硬编码进版本库。

