import json
from pathlib import Path
from scraper.config import OUTPUT_DIR


def save(data: dict, name: str, *, output_dir: str | None = None) -> str:
    base = Path(output_dir) if output_dir else OUTPUT_DIR
    base.mkdir(parents=True, exist_ok=True)
    out_file = base / f"{name}.json"
    out_file.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return str(out_file)
