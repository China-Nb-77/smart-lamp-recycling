from __future__ import annotations

import shutil
from pathlib import Path

import click
import pandas as pd
from PIL import Image
from tqdm import tqdm

from config import settings
from src.adapters.sam3_adapter import SAM3Adapter
from src.embedding.openclip_embedder import OpenCLIPEmbedder
from src.indexing.faiss_store import FaissStore
from src.pricing.rule_engine import RuleQuoteEngine
from src.utils.io import ensure_dir, write_json, write_yaml
from src.utils.yolo import bbox_to_yolo, mask_to_bbox, read_mask, save_yolo_label


@click.group()
def cli() -> None:
    """Vision Quote Pipeline CLI."""


@cli.command("prepare-yolo")
@click.option("--images-dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--masks-dir", type=click.Path(exists=False, file_okay=False), required=False)
@click.option("--output-dir", type=click.Path(file_okay=False), required=True)
@click.option("--class-id", type=int, required=True)
@click.option("--sam3-root", type=click.Path(exists=False), required=False)
@click.option("--sam3-checkpoint", type=click.Path(exists=False), required=False)
@click.option("--text-prompt", type=str, default="lamp", show_default=True)
@click.option("--device", type=str, default=settings.device, show_default=True)
def prepare_yolo(
    images_dir: str,
    masks_dir: str | None,
    output_dir: str,
    class_id: int,
    sam3_root: str | None,
    sam3_checkpoint: str | None,
    text_prompt: str,
    device: str,
) -> None:
    images_dir_p = Path(images_dir)
    output_dir_p = Path(output_dir)
    out_images = ensure_dir(output_dir_p / "images")
    out_labels = ensure_dir(output_dir_p / "labels")

    adapter = SAM3Adapter(
        sam3_root=sam3_root,
        checkpoint_path=sam3_checkpoint,
        device=device,
        text_prompt=text_prompt,
    )
    image_files = sorted([p for p in images_dir_p.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}])

    for image_path in tqdm(image_files, desc="prepare-yolo"):
        if masks_dir:
            mask_path = Path(masks_dir) / f"{image_path.stem}.png"
            mask = read_mask(mask_path)
        else:
            mask = adapter.predict_mask(image_path, text_prompt=text_prompt)

        bbox = mask_to_bbox(mask)
        if bbox is None:
            click.echo(f"跳过空 mask: {image_path.name}")
            continue

        with Image.open(image_path) as img:
            width, height = img.size

        label = bbox_to_yolo(class_id, bbox, width, height)
        save_yolo_label(out_labels / f"{image_path.stem}.txt", [label])
        shutil.copy2(image_path, out_images / image_path.name)

    dataset_yaml = {
        "path": str(output_dir_p.resolve()),
        "train": "images",
        "val": "images",
        "names": {class_id: f"class_{class_id}"},
    }
    write_yaml(output_dir_p / "dataset.yaml", dataset_yaml)
    click.echo(f"已生成 YOLO 数据集: {output_dir_p}")


@cli.command("build-index")
@click.option("--csv", "csv_path", type=click.Path(exists=True, dir_okay=False), required=True)
@click.option("--index-dir", type=click.Path(file_okay=False), required=True)
def build_index(csv_path: str, index_dir: str) -> None:
    df = pd.read_csv(csv_path)
    required = {"id", "image_path", "material", "size_mm", "process", "base_price"}
    missing = required - set(df.columns)
    if missing:
        raise click.ClickException(f"products.csv 缺少字段: {sorted(missing)}")

    embedder = OpenCLIPEmbedder()
    vectors = []
    rows = []

    for row in tqdm(df.to_dict(orient="records"), desc="build-index"):
        image_path = str(row["image_path"])
        vec = embedder.encode_image(image_path)
        vectors.append(vec)
        rows.append(row)

    store = FaissStore(dim=len(vectors[0]))
    store.add(vectors=pd.DataFrame(vectors).to_numpy(dtype="float32"), metadata=pd.DataFrame(rows))
    store.save(index_dir)
    click.echo(f"已写入索引: {index_dir}")


@cli.command("quote")
@click.option("--query-image", type=click.Path(exists=True, dir_okay=False), required=True)
@click.option("--index-dir", type=click.Path(exists=True, file_okay=False), required=True)
@click.option("--top-k", type=int, default=settings.top_k, show_default=True)
@click.option("--material", type=str, required=False)
@click.option("--size-mm", type=float, required=False)
@click.option("--process", "process_name", type=str, required=False)
@click.option("--urgent", is_flag=True, default=False)
def quote(query_image: str, index_dir: str, top_k: int, material: str | None, size_mm: float | None, process_name: str | None, urgent: bool) -> None:
    embedder = OpenCLIPEmbedder()
    store = FaissStore.load(index_dir)
    engine = RuleQuoteEngine()

    vec = embedder.encode_image(query_image)
    neighbors = store.search(vec, top_k=top_k)

    result = engine.quote_from_neighbors(
        neighbors,
        query_meta={
            "material": material,
            "size_mm": size_mm,
            "process": process_name,
            "urgent": urgent,
        },
    )

    click.echo("\n=== TopK 相似样本 ===")
    click.echo(neighbors.to_string(index=False))
    click.echo("\n=== 报价结果 ===")
    click.echo(f"相似样本基准价: {result.base_similarity_price}")
    click.echo(f"材质修正: {result.material_adjustment}")
    click.echo(f"尺寸修正: {result.size_adjustment}")
    click.echo(f"工艺修正: {result.process_adjustment}")
    click.echo(f"加急修正: {result.urgent_adjustment}")
    click.echo(f"最终报价: {result.final_price}")

    output = {
        "neighbors": neighbors.to_dict(orient="records"),
        "quote": {
            "base_similarity_price": result.base_similarity_price,
            "material_adjustment": result.material_adjustment,
            "size_adjustment": result.size_adjustment,
            "process_adjustment": result.process_adjustment,
            "urgent_adjustment": result.urgent_adjustment,
            "final_price": result.final_price,
            "explanation": result.explanation,
        },
    }
    out_path = Path(index_dir) / "last_quote.json"
    write_json(out_path, output)
    click.echo(f"\n已写出: {out_path}")


if __name__ == "__main__":
    cli()
