from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(
    title="RecruiterAI",
    description="Modern AI-powered candidate discovery and ranking service",
    version="2.0.0",
)


class JobDescriptionRequest(BaseModel):
    job_description: str
    candidate_limit: int = 10


class RankingResponse(BaseModel):
    message: str
    workflow: List[str]
    technologies: List[str]
    candidate_limit: int


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "RecruiterAI",
        "stack": ["FastAPI", "Sentence Transformers", "FAISS", "Docker"],
    }


@app.post("/rank", response_model=RankingResponse)
def rank_candidates(payload: JobDescriptionRequest) -> RankingResponse:
    return RankingResponse(
        message="AI-powered ranking workflow initialized",
        workflow=[
            "Parse job description with LLM intent extraction",
            "Embed job and candidate profiles",
            "Retrieve candidates with FAISS hybrid search",
            "Score across semantic, skill, experience, and behavioral signals",
        ],
        technologies=[
            "GPT-4 / Llama 3",
            "Sentence Transformers",
            "FAISS",
            "FastAPI",
            "PostgreSQL",
        ],
        candidate_limit=payload.candidate_limit,
    )
