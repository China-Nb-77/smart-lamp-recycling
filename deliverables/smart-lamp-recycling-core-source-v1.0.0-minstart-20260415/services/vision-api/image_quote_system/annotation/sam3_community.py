from __future__ import annotations

import shutil
from pathlib import Path
from urllib.request import Request, urlopen


def build_huggingface_resolve_url(repo_id: str, filename: str, revision: str = "main") -> str:
    clean_repo_id = repo_id.strip("/")
    clean_filename = filename.lstrip("/")
    return f"https://huggingface.co/{clean_repo_id}/resolve/{revision}/{clean_filename}?download=1"


def download_community_checkpoint(
    *,
    repo_id: str,
    filename: str,
    output_path: str | Path,
    revision: str = "main",
    force: bool = False,
) -> dict[str, str | int]:
    destination = Path(output_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and not force:
        return {
            "status": "exists",
            "repo_id": repo_id,
            "filename": filename,
            "revision": revision,
            "output_path": str(destination),
            "size_bytes": destination.stat().st_size,
        }

    download_url = build_huggingface_resolve_url(repo_id, filename, revision)
    temporary_path = destination.with_suffix(destination.suffix + ".part")
    request = Request(
        download_url,
        headers={"User-Agent": "image-quote-system/0.1 community-sam3-downloader"},
    )

    try:
        with urlopen(request) as response, temporary_path.open("wb") as handle:
            shutil.copyfileobj(response, handle, length=1024 * 1024)
        temporary_path.replace(destination)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return {
        "status": "downloaded",
        "repo_id": repo_id,
        "filename": filename,
        "revision": revision,
        "output_path": str(destination),
        "size_bytes": destination.stat().st_size,
        "download_url": download_url,
    }
