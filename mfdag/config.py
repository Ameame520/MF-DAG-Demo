from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["_config_path"] = str(Path(path).resolve())
    return cfg


def resolve_path(cfg: Dict[str, Any], *keys: str) -> Path:
    data = cfg
    for key in keys:
        data = data[key]
    root = Path(cfg["data"]["data_root"])
    return root / data if not Path(data).is_absolute() else Path(data)


def processed_dir(cfg: Dict[str, Any]) -> Path:
    rel = cfg["data"].get("processed_dir", "outputs/processed/blacksky")
    p = Path(rel)
    if not p.is_absolute():
        base = Path(cfg["_config_path"]).parent.parent
        p = base / p
    return p
