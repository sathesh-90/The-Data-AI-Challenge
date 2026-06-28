# Design Document

How RecruiterAI turns 100K raw candidate records into a ranked, explained top 100.

## Approach in one line

A transparent, AI-assisted candidate ranking system that combines deterministic
scoring with modern NLP and retrieval technologies. The project uses Python,
FastAPI, Pydantic, Uvicorn, Sentence Transformers, FAISS, OpenAI, PyYAML,
pytest, JSONL/CSV/YAML data formats, and Docker to build an explainable
recruiting workflow.

## Technology stack

- **Backend:** Python, FastAPI, Pydantic, Uvicorn
- **AI / NLP:** Sentence Transformers, OpenAI, FAISS
- **Data & Config:** JSONL, CSV, YAML, PyYAML
- **Testing & Packaging:** pytest, Docker

## Pipeline

```
candidates.jsonl
   │  stream one record at a time (bounded memory)
   ▼
feature extraction      (src/features.py)
   │  title class, trust-weighted skills, build-evidence, company type,
   │  tenure, location, behavioural signals, honeypot consistency checks
   ▼
fit scoring             (src/scoring.py)
   │  base  = Σ wᵢ · componentᵢ
   │  score = base × behavioural_modifier × penalties × honeypot_kill
   ▼
keep top-N shortlist    (src/ranker.py)
   │  sort → reasoning   (src/reasoning.py)
   ▼
submission.csv  (candidate_id, rank, score, reasoning)
```

## The fit score

Weighted sum of seven components, each in `[0, 1]`. Weights live in
`configs/scoring_config.yaml` and are renormalised to sum to 1 at load.

| Component | Weight | Captures |
|---|---|---|
| title | 0.26 | Is the current role actually an ML/AI/search engineer? Main guard against keyword stuffers. |
| skills | 0.22 | Trust-weighted skill coverage (endorsements + months-of-use beat padded lists). |
| evidence | 0.18 | Did they *build* ranking / search / recsys / retrieval at scale? |
| experience | 0.12 | 5–9 yr band, ideal 6–8. |
| company | 0.09 | Product company vs. consulting-only career. |
| location | 0.08 | Pune/Noida preferred; other major India cities welcome. |
| education | 0.05 | Low on purpose — what you built matters more. |

Then multiplied by:

- **Behavioural modifier** — recruiter response rate, activity recency,
  open-to-work, notice period, etc. Unreachable candidates discount toward 0.3×.
- **Penalties** — the task's explicit disqualifiers: CV/speech-only without
  NLP/IR, research-only with no production, consulting-only, title-chasing
  (chronic <20-month tenure), LangChain-only dabbler.
- **Honeypot kill** — internal-consistency violations force the score to the
  floor.

## The two ideas that beat the traps

1. **Title × skill-trust.** A keyword stuffer has a perfect skill list but a
   non-engineering title and skills with 0 endorsements / 0 months of use. The
   title component crushes the title; the per-skill trust multiplier discounts
   the skills. The "Marketing Manager with 9 AI skills" sinks.
2. **Internal-consistency honeypot check.** Honeypots are subtly impossible
   (e.g. 8 yrs tenure in a 3-year-old role). We detect the contradiction and
   floor the score, keeping them out of the top 100.

## Modules

| File | Responsibility |
|---|---|
| `rank.py` | Entry point / the reproduce command. |
| `src/job_profile.py` | The JD encoded as lexicons, weights, thresholds. |
| `src/io_utils.py` | Streaming jsonl(.gz) read, CSV write, YAML load. |
| `src/features.py` | Raw record → derived signals + honeypot checks. |
| `src/scoring.py` | Components + behavioural modifier + penalties. |
| `src/reasoning.py` | Specific, varied, non-hallucinated explanations. |
| `src/ranker.py` | Streaming top-N orchestration + self-validation. |
| `tests/test_ranking.py` | The JD's "right answers" as assertions. |

## Why these choices

- **Stream, don't load.** 100K records at ~16 GB cap → process one line at a
  time and keep only a ~400-candidate shortlist heap. Memory stays tiny.
- **No embeddings model by default.** Loading one needs a download (network) or
  a vendored weight file; rule-based evidence matching already captures the
  signal while staying reproducible offline. TF-IDF cosine is the natural next
  step.
- **Hand-set weights, not learned.** No labelled training set exists, and
  hand-set weights are defensible and live in one YAML for easy tuning.
- **Deterministic.** No randomness, no network → same input, same output, every
  run, inside the sandbox.

## Known limitations

- Honeypot detection is heuristic (internal consistency), not a lookup; it
  caught ~65 of ~80 stated honeypots but kept all of them out of the top 100.
- No semantic embedding recall yet — some plain-language fits may be missed.
- Weights are reasoned from the JD, not validated against ground-truth labels.
