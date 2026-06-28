"""
ranker.py
=========

Orchestrates the full ranking pass:

    stream candidates -> extract features -> score -> keep best N -> rank ->
    generate reasoning -> rows for the submission CSV.

Memory stays tiny: we only retain a bounded list of the strongest candidates,
never the whole 100K parsed pool.
"""

from __future__ import annotations

import heapq
import time
from typing import Dict, List, Tuple

from . import io_utils
from .features import extract
from .reasoning import build_reasoning
from .scoring import resolve_weights, score_candidate

TOP_N = 100


def rank_pool(candidates_path: str, config: Dict, keep: int = 400,
              log=print) -> List[Tuple]:
    """Single streaming pass. Returns the final ordered list of submission rows.

    `keep` is the size of the working shortlist we retain before the final
    sort/reasoning step - a few hundred is plenty to guarantee a correct top-100
    while keeping memory and reasoning cost negligible.
    """
    weights = resolve_weights(config)
    t0 = time.time()

    # min-heap of (score, candidate_id, features) keyed on score so the smallest
    # is evicted first. candidate_id is the tie-break key for determinism.
    heap: List[Tuple[float, str, object]] = []
    n_total = 0
    n_honeypot = 0

    for record in io_utils.iter_candidates(candidates_path):
        n_total += 1
        f = extract(record)
        if f.honeypot:
            n_honeypot += 1
        bd = score_candidate(f, weights)
        f._score = bd.final          # stash for later (dynamic attr)
        f._breakdown = bd

        key = (bd.final, _id_sort_key(f.candidate_id))
        if len(heap) < keep:
            heapq.heappush(heap, (key, f))
        elif key > heap[0][0]:
            heapq.heapreplace(heap, (key, f))

        if n_total % 20000 == 0:
            log(f"  ...scored {n_total:,} candidates "
                f"({time.time() - t0:.1f}s, {n_honeypot} honeypots seen)")

    log(f"Scored {n_total:,} candidates in {time.time() - t0:.1f}s "
        f"({n_honeypot} honeypots detected and de-prioritised).")

    shortlist = [f for _, f in heap]
    # final sort: score desc, then candidate_id asc (validator tie-break rule)
    shortlist.sort(key=lambda f: (-_round4(f._score), f.candidate_id))

    top = shortlist[:TOP_N]
    rows: List[Tuple] = []
    for i, f in enumerate(top, start=1):
        score = _round4(f._score)
        reasoning = build_reasoning(f, f._breakdown, i)
        rows.append((f.candidate_id, i, score, reasoning))

    _assert_valid(rows, log)
    return rows


def _round4(x: float) -> float:
    return round(float(x), 4)


def _id_sort_key(cid: str) -> str:
    # Descending candidate_id would naturally win heap ties; we want ascending
    # ids to win at equal score, so invert by mapping to a comparable that makes
    # *smaller* id => *larger* key. Simple approach: numeric part negated.
    try:
        n = int(cid.split("_")[-1])
        return -n
    except (ValueError, IndexError):
        return 0


def _assert_valid(rows: List[Tuple], log) -> None:
    """Cheap internal guard mirroring validate_submission.py before we write."""
    assert len(rows) == TOP_N, f"expected {TOP_N} rows, got {len(rows)}"
    ranks = [r[1] for r in rows]
    assert ranks == list(range(1, TOP_N + 1)), "ranks must be 1..100 in order"
    ids = [r[0] for r in rows]
    assert len(set(ids)) == TOP_N, "duplicate candidate_id in output"
    scores = [r[2] for r in rows]
    for a, b in zip(scores, scores[1:]):
        assert a >= b, "scores must be non-increasing by rank"
    # equal-score tie-break must be candidate_id ascending
    for (id1, _, s1, _), (id2, _, s2, _) in zip(rows, rows[1:]):
        if s1 == s2:
            assert id1 < id2, "equal scores must tie-break by candidate_id asc"
    log("Internal validation passed (100 rows, unique ranks/ids, "
        "non-increasing scores, deterministic tie-break).")
