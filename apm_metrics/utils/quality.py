"""Collects data-quality issues while the pipeline runs; written to data_quality.xlsx at the end."""

import pandas as pd

_issues: list[dict] = []


def add(issue: str, detail: str, source: str = "", count: int | None = None) -> None:
    _issues.append({"issue": issue, "source": source, "count": count, "detail": detail})


def sample_ids(ids, n: int = 8) -> str:
    ids = sorted({str(i) for i in ids})
    return ", ".join(ids[:n]) + (f" ... (+{len(ids) - n} more)" if len(ids) > n else "")


def frame() -> pd.DataFrame:
    return pd.DataFrame(_issues, columns=["issue", "source", "count", "detail"])
