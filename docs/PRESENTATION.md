---
marp: true
theme: default
paginate: true
size: 16:9
---

<!--
Editable source for the approach deck.
Two ways to get a PDF:
  A) Open docs/deck.html in any browser → Ctrl/Cmd+P → "Save as PDF"
     → Layout: Landscape, Margins: None, "Background graphics": ON.
  B) With Marp (npm i -g @marp-team/marp-cli):  marp docs/PRESENTATION.md --pdf
-->

# RecruiterAI
## Finding Talent **Beyond Keywords**

Ranking 100,000 candidates the way a great recruiter would —
by understanding who actually fits the role.

*Data & AI Challenge · Intelligent Candidate Discovery*

---

## The Problem: keyword filters can't see what matters

Recruiters scan hundreds of profiles and still miss the right person — not
because the talent isn't there, but because keyword matching is blind to
**context, trajectory, and intent**.

The job needs someone who **built** retrieval & ranking systems — not someone
who merely **lists** the words.

**The dataset is adversarial on purpose:** 100K candidates seeded with keyword
stuffers, plain-language strong fits, behavioural twins, and **~80 honeypots**
with subtly impossible profiles.

---

## Reading the constraints — the limits *are* the design brief

| Constraint | What it rules out |
|---|---|
| **≤ 5 min · CPU · no network** | No hosted-LLM call per candidate; sandbox has no internet/GPU |
| **100,000 candidates** | Per-candidate deep inference is too slow → streaming pass |
| **Honeypot rate > 10% = DQ** | Model must *read profiles*, not embed keywords |
| **Stage 4–5: defend your work** | Every score must be explainable by a human |

➡ A per-candidate GPT-4 pipeline is disqualified before it scores a point.
The winning shape is a **fast, transparent, deterministic ranker.**

---

## Our approach: a transparent hybrid ranker

- **Read the role, not the words** — the JD is encoded as competency lexicons,
  weights, and disqualifiers (what it *means*, not just what it says).
- **Score the whole picture** — seven fit components × behavioural-availability
  modifier × penalty factors.
- **Explain every pick** — specific, non-templated reasoning grounded only in
  facts from the candidate's profile.

```
score = Σ wᵢ·componentᵢ × behavioural_modifier × penalty_factors × honeypot_kill
```

---

## Architecture: one streaming pass, bounded memory

```
candidates.jsonl → stream record → feature extraction → fit scoring
   → behavioural modifier → penalty/honeypot → top-N heap → reasoning → submission.csv
```

- **Streaming:** never hold all 100K parsed records in RAM — only a heap of the
  strongest candidates. Peak memory far under 16 GB.
- **Deterministic:** same input → same output. Reproduces unchanged in the
  Stage-3 sandbox; defensible line-by-line at the interview.

---

## The fit score — seven explainable components

| Component | Weight | Captures |
|---|---|---|
| **Title** | 0.26 | Is the current role an ML/AI/search engineer? *Guard against stuffers.* |
| **Skills** | 0.22 | Trust-weighted coverage (endorsements + months neutralise padding) |
| **Evidence** | 0.18 | Did they *build* ranking/search/recsys at scale? |
| **Experience** | 0.12 | 5–9 yr band, ideal 6–8 |
| **Company** | 0.09 | Product vs. consulting-only career |
| **Location** | 0.08 | Pune/Noida preferred; Hyderabad/Mumbai/Delhi-NCR/Bangalore welcome |
| **Education** | 0.05 | Low on purpose — the JD cares what you built |

Weights live in `configs/scoring_config.yaml` — auto-normalised and tunable.

---

## Two ideas that defeat the dataset

**① Title × skill-trust.** A keyword stuffer has a perfect skill list but a
non-engineering title and skills with 0 endorsements / 0 months of use. Title
crushes the first; a per-skill trust multiplier discounts the second.
→ *"Marketing Manager + 9 AI skills"* sinks; the plain-language builder rises.

**② Consistency honeypot check.** Honeypots are subtly impossible (8 yrs tenure
in a 3-year-old role; "expert" in 10 skills with 0 months used). We detect the
violations and floor the score → **0 honeypots in our top 100.**

> The provided `sample_submission.csv` ranks stuffers at the top — a deliberately
> wrong format reference. We rank the opposite way.

---

## Signal integration — is the candidate actually hire-able?

A perfect-on-paper profile inactive 6 months with a 5% response rate is, for
hiring, **not available.** The 23 Redrob behavioural signals become a
multiplicative availability modifier (down to ~0.3×).

- **Availability:** response rate · activity recency · open-to-work · notice period
- **Demand:** saved by recruiters · search appearances · interview completion
- **Trust:** verified email/phone · profile completeness · LinkedIn

**Penalty factors (JD's "do-not-want"):** CV/speech-only without NLP/IR ·
research-only without production · consulting-only · title-chasing · LangChain-only dabbler.

---

## Technologies used — lean by design, honest by necessity

**In the ranking step (scores the CSV):** Python 3.11 **standard library only** ·
streaming JSONL · heap top-N · rule-based hybrid scoring · deterministic · CPU ·
offline. *Zero third-party packages → reproduces unchanged.*

**Optional / future work:** scikit-learn TF-IDF re-rank · sentence-transformers /
SBERT · FAISS · Streamlit sandbox · pytest. *(Offline embeddings are the natural
next step — never a per-candidate API call.)*

No GPT-4/Pinecone/hosted-LLM calls during ranking — the constraints forbid it,
and the transparent model is what survives Stages 3–5.

---

## Results · 100K pool

| Metric | Result |
|---|---|
| Full run | **~32 s**, 1 CPU core, no network *(budget: 5 min)* |
| Honeypots in top 100 | **0%** *(DQ threshold: > 10%)* |
| Format validation | **valid ✓** (official `validate_submission.py`) |
| Top-100 titles | **92** core ML/AI-engineer, 8 adjacent, **0 stuffers** |
| Location | 46% preferred/welcome cities, 47% elsewhere in India |

```
1   Search Engineer · 7.6 yrs · Milvus, Semantic Search, Weaviate · a/b test · Gurgaon · responsive 0.94
100 Filler: 120-day notice. Still a fit — Senior Data Scientist · 6.5 yrs · Milvus, OpenSearch, Qdrant · Noida
```

---

# Thank You

## RecruiterAI — finding talent beyond keywords

`python rank.py --candidates ./data/raw/candidates.jsonl --out ./data/output/submission.csv`

**Questions & Discussion 🚀**
