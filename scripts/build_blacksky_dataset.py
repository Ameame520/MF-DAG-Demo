#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mfdag.config import load_config
from mfdag.data.dataset_builder import build_blacksky_dataset
from mfdag.utils.logging import setup_logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Blacksky processed dataset for MF-DAG")
    parser.add_argument("--config", default="configs/mfdag_blacksky.yaml")
    args = parser.parse_args()
    cfg = load_config(ROOT / args.config)
    logger = setup_logger("build_blacksky_dataset")
    logger.info("开始构建 Blacksky processed dataset ...")
    summary = build_blacksky_dataset(cfg)
    logger.info("构建完成: %s", summary)


if __name__ == "__main__":
    main()
