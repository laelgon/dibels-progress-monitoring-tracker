"""Loads demo/demo_config.yaml and makes the pipeline package (apm_metrics) importable from the project folder."""
import os
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CFG = yaml.safe_load((HERE / "demo_config.yaml").read_text(encoding="utf-8")) or {}


def resolve(value) -> Path:
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


OUT_DIR = resolve(CFG["output_dir"])


def real_data_folders() -> dict:
    """Folders holding REAL data, used only to prove nothing real got into the fake files (read-only, never printed).
    Set in demo_config.yaml or with the environment variables DEMO_REAL_CC_FOLDER and DEMO_REAL_TABLEAU_FOLDER."""
    cfg = CFG.get("real_data") or {}
    out = {"cc_folder": os.environ.get("DEMO_REAL_CC_FOLDER") or cfg.get("cc_folder") or "",
           "tableau_folder": os.environ.get("DEMO_REAL_TABLEAU_FOLDER") or cfg.get("tableau_folder") or ""}
    return {k: v for k, v in out.items() if v}


def use_pipeline_code():
    """Puts the project folder on the import path so `import apm_metrics` finds the pipeline in this repository."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
