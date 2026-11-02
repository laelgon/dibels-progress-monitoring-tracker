"""Loads config/*.yaml. Relative paths in paths.yaml are relative to the project folder."""

from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


@lru_cache
def _load(name: str) -> dict:
    with open(ROOT / "config" / f"{name}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def paths() -> dict:
    return _load("paths")


def rules() -> dict:
    return _load("rules")


def verified_transfers() -> set[str]:
    return {str(i) for i in _load("verified_transfers").get("student_ids", []) or []}


def _resolve(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


def source_dir(name: str) -> Path:
    return _resolve(paths()["source_dirs"][name])


def output_dir() -> Path:
    return _resolve(paths()["output_dir"])


def school_name() -> str:
    return str(paths().get("school_name") or "Your School")
