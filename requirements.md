# Requirements

RecruiterAI ranks the top 100 candidates out of a ~100,000-candidate pool for the
"Senior AI Engineer — Founding Team" role, and explains why each was picked.

## Goal

Pick the candidates a good recruiter would pick — people who *fit the role* — not
the ones who stuffed the most keywords into their profile.

## Technology stack

The project is implemented using:

- Python
- FastAPI
- Pydantic
- Uvicorn
- Sentence Transformers
- FAISS
- OpenAI
- PyYAML
- pytest
- JSONL / CSV / YAML
- Docker

## Must have

- Read `candidates.jsonl` (one record per line) and write a ranked
  `submission.csv` with `candidate_id, rank, score, reasoning`.
- Output passes the official `validate_submission.py` checker.
- Each candidate gets a fit score that we can explain in plain words.
- Keep keyword-stuffers out of the top 100 (e.g. "Marketing Manager" with every
  AI buzzword should sink).
- Let plain-language strong fits win — someone who *built* a recsys counts even
  if they never wrote "RAG".
- Down-weight unreachable/inactive candidates.
- Keep honeypot profiles (subtly impossible data) out of the top 100; staying
  under 10% honeypots is required to not be disqualified.

## Constraints

- Finish within 5 minutes on CPU only, no GPU.
- No network calls during ranking (the sandbox has no internet).
- Stay within 16 GB RAM — stream the input, don't load it all.
- The ranking step sends no candidate data to any LLM.
- Reproducible: same input gives the same output (deterministic).

## Nice to have (not required)

- Offline TF-IDF cosine re-rank as a future step.
- Weights tunable from one config file.

## Done when

- `python rank.py --candidates ./data/raw/candidates.jsonl --out ./data/output/submission.csv`
  produces a valid submission in under 5 minutes.
- Top 100 has 0% honeypots and no keyword-stuffer titles.
- Behavioural tests pass (strong fit beats keyword stuffer; honeypot floored).
