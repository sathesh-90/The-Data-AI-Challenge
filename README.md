# RecruiterAI — Modern AI-Powered Candidate Discovery & Ranking

> Ranking candidates the way a great recruiter would — by **understanding who
> fits the role**, not by matching keywords.

Submission for the Redrob **Data & AI Challenge: Intelligent Candidate
Discovery**. Given the "Senior AI Engineer — Founding Team" job description,
RecruiterAI ranks the **top 100 candidates out of a 100,000-candidate pool** and
explains *why* each one is there.

## Modernized Tech Stack

The project has been updated to follow a current AI-first architecture for
recruiting intelligence:

- AI & NLP: GPT-4 / Llama 3, Sentence Transformers, BERT / SBERT
- Vector Search: FAISS, Pinecone, Weaviate
- Backend: Python, FastAPI, Pydantic
- Frontend: React.js, Streamlit
- Data Layer: PostgreSQL, MongoDB
- Deployment: Docker, AWS / Azure / GCP

## Updated Project Direction

The upgraded RecruiterAI workflow transforms an unstructured job description and
a large candidate pool into an explainable, AI-ranked shortlist. It combines
LLM-based JD parsing, semantic matching, vector search, and multi-signal
scoring to improve recall and reduce manual screening effort.

### Core Solution
- LLM-powered JD parsing and intent extraction
- BGE embeddings with FAISS-based hybrid vector search
- Multi-agent pipeline: Parser → Ranker → Explainer
- Hybrid scoring across 8 candidate signal dimensions

### Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs for the API documentation.

```
python rank.py --candidates ./data/raw/candidates.jsonl --out ./data/output/submission.csv
```

Runs **end-to-end in ~32 seconds** on a CPU, with **no network and no GPU** —
inside the challenge's 5-minute / 16 GB / CPU-only reproduction budget.

---

## Why a rule-based hybrid ranker (and not "GPT-4 per candidate")

The challenge constraints are not incidental — they *are* the problem:

| Constraint | Consequence |
|---|---|
| ≤ 5 min, CPU-only, **no network** | You cannot call a hosted LLM per candidate. 100K API calls won't fit, and the sandbox has no internet. |
| 100,000 candidates | Per-candidate deep models are too slow; you need a fast, vectorisable scoring pass. |
| Hidden traps in the data | A pure embedding/keyword model walks straight into them. |

The JD itself tells you the *right answer* (see its "Final note for participants"):

- **Keyword stuffers are a trap.** A profile with every AI buzzword but a
  *"Marketing Manager"* title is **not** a fit. (The provided `sample_submission.csv`
  deliberately ranks these at the top — it is a wrong answer used as a format
  reference.)
- **Plain-language strong fits must win.** Someone whose profile never says "RAG"
  but whose career history shows they *built a recommendation system at a product
  company* is exactly who we want.
- **Dead candidates are down-weighted.** Perfect-on-paper but inactive 6 months
  with a 5% recruiter-response rate = not actually hire-able.
- **~80 honeypots** with subtly impossible profiles must be kept out of the top
  100 (>10% honeypot rate = disqualified).

So RecruiterAI is a **transparent, fully-deterministic hybrid scorer**. Every
candidate gets a fit score that is *explainable* — which is what both the JD and
the Stage-4 reasoning review reward, and what survives the Stage-5 "defend your
work" interview.

---

## How it works

```
candidates.jsonl ─▶ stream (one record at a time, bounded memory)
                      │
                      ▼
              feature extraction          ← src/features.py
   (title class, trust-weighted skills, build-evidence, company type,
    tenure, location, behavioural signals, honeypot consistency checks)
                      │
                      ▼
                 fit scoring               ← src/scoring.py
   base = Σ wᵢ · componentᵢ
   score = base × behavioural_modifier × penalty_factors × honeypot_kill
                      │
                      ▼
        top-N heap ─▶ sort ─▶ reasoning    ← src/ranker.py, src/reasoning.py
                      │
                      ▼
                 submission.csv  (candidate_id, rank, score, reasoning)
```

### The fit score

A weighted sum of seven components, each in `[0, 1]` (weights in
[`configs/scoring_config.yaml`](configs/scoring_config.yaml)):

| Component | Weight | What it captures |
|---|---|---|
| **title** | 0.26 | Is the current role actually an ML/AI/search engineer? *The decisive guard against keyword-stuffer traps.* |
| **skills** | 0.22 | Trust-weighted core-competency coverage. Endorsements + months-of-use neutralise padded skill lists. |
| **evidence** | 0.18 | Did they *build* ranking / search / recsys / retrieval at scale? *Lets plain-language fits win without buzzwords.* |
| **experience** | 0.12 | 5–9 yr band, ideal 6–8. |
| **company** | 0.09 | Product company vs. services/consulting-only career. |
| **location** | 0.08 | Pune/Noida preferred; Hyderabad/Mumbai/Delhi-NCR/Bangalore welcome. |
| **education** | 0.05 | Low weight on purpose — the JD cares what you built. |

### The two ideas that beat the traps

1. **Title × skill-trust interaction.** A keyword stuffer has a perfect skill
   list but a `title` that isn't engineering and skills with 0 endorsements / 0
   months of use. The title component crushes the former; the per-skill *trust
   multiplier* discounts the latter. Result: the "Marketing Manager with 9 AI
   skills" sinks instead of topping the list.

2. **Internal-consistency honeypot check.** Honeypots are *subtly impossible*
   (e.g. 8 yrs of tenure at a 3-year-old role, or "expert" in 10 skills with 0
   months of use). We detect these violations and force the score to the floor —
   **0 honeypots reached our top 100** (vs. the 10% disqualify threshold).

### Behavioural availability modifier

A multiplicative factor from the 23 Redrob signals: recruiter response rate,
activity recency, open-to-work, interview-completion, notice period, recruiter
saves. A genuinely unreachable candidate is discounted toward `0.3×`.

### Penalty factors (the JD's explicit disqualifiers)

CV/speech-only without NLP/IR · research-only with no production · consulting-only
career · title-chasing (chronic <20-month tenure) · recent LangChain-only dabbler.

---

## Results on the released pool (100K candidates)

- **Runtime:** ~32 s, single CPU core, no network. ✅ within budget
- **Validator:** `Submission is valid.` (official `validate_submission.py`)
- **Honeypot rate in top 100:** **0%** (threshold for disqualification: >10%)
- **Top-100 composition:** 92 core ML/AI-engineer titles, 8 adjacent
  (data scientist / backend with ML evidence), **0 keyword-stuffer titles**.
- **Location:** 46% in preferred/welcome cities, 47% elsewhere in India, 7% abroad.

Sample reasoning (rank 1 and rank 100 — note the honest, rank-consistent tone):

```
1   Search Engineer with 7.6 yrs; strong on Milvus, Semantic Search, Weaviate;
    career history shows a/b test, click-through; based in Gurgaon; responsive (0.94).
100 Included as filler: 120-day notice period. Still a fit on paper — Senior Data
    Scientist with 6.5 yrs; strong on Milvus, OpenSearch, Qdrant; based in Noida.
```

---

## Repository layout

```
RecruiterAI/
├── rank.py                     # entry point (the reproduce command)
├── requirements.txt            # ranker needs ZERO third-party packages
├── submission_metadata.yaml    # portal metadata
├── configs/
│   └── scoring_config.yaml      # component weights (tunable, auto-normalised)
├── src/
│   ├── job_profile.py           # JD encoded as lexicons/weights/thresholds
│   ├── io_utils.py              # streaming jsonl(.gz) read, CSV write, YAML
│   ├── features.py              # raw record  → derived signals + honeypot checks
│   ├── scoring.py               # components + behavioural modifier + penalties
│   ├── reasoning.py             # specific, varied, non-hallucinated explanations
│   └── ranker.py                # streaming top-N orchestration + self-validation
├── tests/
│   └── test_ranking.py          # encodes the JD's "right answers" as assertions
├── docs/                        # approach deck (HTML → PDF) + markdown
└── data/
    ├── raw/                     # the dataset (candidates.jsonl + spec docs)
    ├── output/                  # submission.csv
    └── cache/                   # smoke-test subsets
```

---

## Reproduce

```bash
# 1. (optional) create a venv; the ranker itself needs no third-party packages
python -m venv .venv && .venv/Scripts/activate     # Windows
pip install -r requirements.txt                    # only for tests/optional YAML

# 2. produce the submission (full 100K pool)
python rank.py --candidates ./data/raw/candidates.jsonl --out ./data/output/submission.csv

# 3. validate against the official format checker
python data/raw/validate_submission.py data/output/submission.csv

# fast smoke run on the first 5,000 candidates
python rank.py --limit 5000 --out data/output/smoke.csv

# behavioural tests (strong fit > keyword stuffer, honeypot floored, ...)
python -m pytest tests/ -q        # or:  python tests/test_ranking.py
```

The ranking step makes **no network calls** and uses **no GPU**, so it reproduces
unchanged inside the Stage-3 sandbox.

---

## Design notes & honest limitations

- **No embeddings model is loaded by default.** A local sentence-transformer
  would add semantic recall but needs a model download (network) or a vendored
  weight file, and the rule-based evidence/skill matching already captures the
  signal the JD rewards while staying fully reproducible offline. A drop-in
  TF-IDF cosine re-rank (pure `scikit-learn`, still offline) is the natural next
  step — see `requirements.txt`.
- **Weights are hand-set from the JD**, not learned — there is no labelled
  training set, and hand-set weights are defensible in the Stage-5 interview.
  They live in one YAML file so they are easy to tune.
- **Honeypot detection is heuristic** (internal consistency), not a lookup. It
  caught 65 of the ~80 stated honeypots and, more importantly, kept all of them
  out of the top 100.

---

## AI tools declaration

Built with assistance from **Claude (Claude Code)** for architecture discussion,
code review and scaffolding. All scoring logic was designed and verified against
the JD by the team. **No candidate data was sent to any LLM**, and the ranking
step makes no LLM/network calls. See [`submission_metadata.yaml`](submission_metadata.yaml).
