#!/usr/bin/env python3
"""
rank.py - RecruiterAI entry point
=================================

Produces the top-100 submission CSV for the Redrob "Senior AI Engineer" JD from
the candidate pool, end-to-end, in a single CPU-only pass with no network.

Reproduce command (Stage-3 compatible):

    python rank.py --candidates ./data/raw/candidates.jsonl --out ./data/output/submission.csv

Both arguments default to the in-repo paths, so a bare `python rank.py` works.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# allow `python rank.py` from the repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import io_utils
from src.ranker import rank_pool

DEFAULT_CANDIDATES = os.path.join("data", "raw", "candidates.jsonl")
DEFAULT_OUT = os.path.join("data", "output", "submission.csv")
DEFAULT_CONFIG = os.path.join("configs", "scoring_config.yaml")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Rank top-100 candidates for the JD.")
    p.add_argument("--candidates", default=DEFAULT_CANDIDATES,
                   help="Path to candidates.jsonl or candidates.jsonl.gz")
    p.add_argument("--out", default=DEFAULT_OUT,
                   help="Output submission CSV path")
    p.add_argument("--config", default=DEFAULT_CONFIG,
                   help="Scoring config YAML (optional)")
    p.add_argument("--limit", type=int, default=0,
                   help="Score only the first N candidates (debug/smoke runs)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    if not os.path.exists(args.candidates):
        print(f"ERROR: candidates file not found: {args.candidates}", file=sys.stderr)
        return 2

    config = io_utils.load_yaml_config(args.config)
    print(f"RecruiterAI ranker")
    print(f"  candidates : {args.candidates}")
    print(f"  output     : {args.out}")
    print(f"  config     : {args.config if os.path.exists(args.config) else '(defaults)'}")
    print("-" * 60)

    t0 = time.time()
    candidates_path = args.candidates
    if args.limit:
        candidates_path = _make_limited(args.candidates, args.limit)

    rows = rank_pool(candidates_path, config)
    io_utils.write_submission(rows, args.out)

    print("-" * 60)
    print(f"Wrote {len(rows)} ranked candidates -> {args.out}")
    print(f"Total wall-clock: {time.time() - t0:.1f}s")
    print("\nTop 5 preview:")
    for cid, rank, score, reasoning in rows[:5]:
        snippet = reasoning if len(reasoning) <= 110 else reasoning[:107] + "..."
        print(f"  {rank:>3}  {cid}  {score:.4f}  {snippet}")
    return 0


def _make_limited(path: str, n: int) -> str:
    """Write the first N lines to the scratch cache for quick smoke testing."""
    cache_dir = os.path.join("data", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    limited = os.path.join(cache_dir, f"candidates_first_{n}.jsonl")
    with io_utils.open_maybe_gzip(path) as src, \
            open(limited, "w", encoding="utf-8") as dst:
        for i, line in enumerate(src):
            if i >= n:
                break
            dst.write(line)
    print(f"  (smoke mode: using first {n} candidates -> {limited})")
    return limited


if __name__ == "__main__":
    raise SystemExit(main())
