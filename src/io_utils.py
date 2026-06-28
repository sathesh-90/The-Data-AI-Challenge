"""
io_utils.py
===========

Streaming I/O helpers. We never hold all 100K parsed records in memory at once
during scoring - we stream the JSONL line-by-line and keep only a small heap of
the best candidates. This keeps peak RAM well under the 16 GB budget.
"""

from __future__ import annotations

import csv
import gzip
import json
import os
from typing import Dict, Iterator


def open_maybe_gzip(path: str):
    """Open a .jsonl or .jsonl.gz file transparently as UTF-8 text."""
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def iter_candidates(path: str) -> Iterator[Dict]:
    """Yield one parsed candidate dict per non-empty line.

    Malformed lines are skipped rather than aborting the whole run - a single
    bad row should never cost us a submission.
    """
    with open_maybe_gzip(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def load_yaml_config(path: str) -> Dict:
    """Load scoring_config.yaml. Falls back to PyYAML if available, otherwise a
    tiny built-in parser for the flat/nested float config we ship, so the
    ranker has zero hard third-party dependencies."""
    if not os.path.exists(path):
        return {}
    try:
        import yaml  # type: ignore
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return _minimal_yaml(path)


def _minimal_yaml(path: str) -> Dict:
    """Very small YAML subset parser: 2-level nesting, scalar floats/ints/bools.
    Sufficient for scoring_config.yaml; avoids requiring PyYAML at runtime."""
    root: Dict = {}
    stack = [(-1, root)]
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.strip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            key, _, val = line.strip().partition(":")
            key = key.strip()
            val = val.split("#", 1)[0].strip()
            while stack and stack[-1][0] >= indent:
                stack.pop()
            parent = stack[-1][1]
            if val == "":
                child: Dict = {}
                parent[key] = child
                stack.append((indent, child))
            else:
                parent[key] = _coerce(val)
    return root


def _coerce(val: str):
    low = val.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        if "." in val or "e" in low:
            return float(val)
        return int(val)
    except ValueError:
        return val.strip('"').strip("'")


def write_submission(rows, out_path: str) -> None:
    """Write the top-100 rows to a UTF-8 CSV matching the required header.

    rows: iterable of (candidate_id, rank, score, reasoning).
    score is written with 4 decimals so the file is stable and non-increasing.
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for cid, rank, score, reasoning in rows:
            writer.writerow([cid, rank, f"{score:.4f}", reasoning])
