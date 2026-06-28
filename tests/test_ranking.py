"""
Behavioural tests for the ranker - these encode the JD's "right answers".

Run with:  pytest -q     (or: python -m pytest tests/ -q)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.features import extract
from src.scoring import resolve_weights, score_candidate

WEIGHTS = resolve_weights({})


def _score(record):
    f = extract(record)
    return f, score_candidate(f, WEIGHTS).final


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
def _signals(**over):
    base = dict(
        profile_completeness_score=90, signup_date="2021-01-01",
        last_active_date="2026-06-10", open_to_work_flag=True,
        profile_views_received_30d=20, applications_submitted_30d=3,
        recruiter_response_rate=0.8, avg_response_time_hours=4,
        skill_assessment_scores={}, connection_count=300,
        endorsements_received=100, notice_period_days=20,
        expected_salary_range_inr_lpa={"min": 30, "max": 45},
        preferred_work_mode="hybrid", willing_to_relocate=True,
        github_activity_score=70, search_appearance_30d=40,
        saved_by_recruiters_30d=8, interview_completion_rate=0.9,
        offer_acceptance_rate=0.5, verified_email=True, verified_phone=True,
        linkedin_connected=True,
    )
    base.update(over)
    return base


def strong_fit():
    """Plain-language builder: AI/ML engineer who shipped a ranking system at a
    product company, right experience band, Pune-based, responsive."""
    return {
        "candidate_id": "CAND_0000001",
        "profile": {
            "anonymized_name": "A B", "headline": "ML Engineer | Search & Ranking",
            "summary": "Built retrieval and ranking systems for real users at scale.",
            "location": "Pune", "country": "India", "years_of_experience": 7.0,
            "current_title": "Machine Learning Engineer", "current_company": "Flipkart",
            "current_company_size": "10001+", "current_industry": "E-commerce",
        },
        "career_history": [{
            "company": "Flipkart", "title": "ML Engineer",
            "start_date": "2020-06-01", "end_date": None, "duration_months": 72,
            "is_current": True, "industry": "E-commerce", "company_size": "10001+",
            "description": ("Built and deployed a recommendation system and search "
                            "ranking model serving real users in production at scale; "
                            "owned embeddings, retrieval, and A/B testing with NDCG."),
        }],
        "education": [{"institution": "IIT", "degree": "B.Tech",
                       "field_of_study": "CS", "start_year": 2013, "end_year": 2017,
                       "grade": "8.5", "tier": "tier_1"}],
        "skills": [
            {"name": "Embeddings", "proficiency": "expert", "endorsements": 40, "duration_months": 48},
            {"name": "FAISS", "proficiency": "advanced", "endorsements": 25, "duration_months": 36},
            {"name": "Learning to Rank", "proficiency": "advanced", "endorsements": 18, "duration_months": 30},
            {"name": "NLP", "proficiency": "advanced", "endorsements": 30, "duration_months": 40},
        ],
        "redrob_signals": _signals(),
    }


def keyword_stuffer():
    """The trap: every AI keyword listed, but current title is Marketing Manager
    and there is zero build evidence. Skills are padded (0 endorsements/duration)."""
    skills = [{"name": n, "proficiency": "expert", "endorsements": 0, "duration_months": 0}
              for n in ["Embeddings", "FAISS", "Pinecone", "RAG", "LLM",
                        "Vector Search", "NLP", "Ranking", "Retrieval"]]
    return {
        "candidate_id": "CAND_0000002",
        "profile": {
            "anonymized_name": "C D", "headline": "Marketing Manager",
            "summary": "Marketing professional.", "location": "Pune",
            "country": "India", "years_of_experience": 7.0,
            "current_title": "Marketing Manager", "current_company": "SomeCo",
            "current_company_size": "201-500", "current_industry": "Marketing",
        },
        "career_history": [{
            "company": "SomeCo", "title": "Marketing Manager",
            "start_date": "2019-06-01", "end_date": None, "duration_months": 84,
            "is_current": True, "industry": "Marketing", "company_size": "201-500",
            "description": "Ran marketing campaigns and managed brand strategy.",
        }],
        "education": [], "skills": skills,
        "redrob_signals": _signals(recruiter_response_rate=0.9),
    }


def honeypot():
    """Subtly impossible: many expert skills with 0 months use, and a role whose
    duration_months far exceeds its date span."""
    skills = [{"name": n, "proficiency": "expert", "endorsements": 0, "duration_months": 0}
              for n in ["Embeddings", "Ranking", "Retrieval", "NLP"]]
    return {
        "candidate_id": "CAND_0000003",
        "profile": {
            "anonymized_name": "E F", "headline": "ML Engineer",
            "summary": "ML engineer.", "location": "Noida", "country": "India",
            "years_of_experience": 8.0, "current_title": "ML Engineer",
            "current_company": "NewCo", "current_company_size": "11-50",
            "current_industry": "Software",
        },
        "career_history": [{
            "company": "NewCo", "title": "ML Engineer",
            "start_date": "2024-01-01", "end_date": None, "duration_months": 96,
            "is_current": True, "industry": "Software", "company_size": "11-50",
            "description": "Worked on ML.",
        }],
        "education": [], "skills": skills,
        "redrob_signals": _signals(),
    }


# --------------------------------------------------------------------------- #
# tests
# --------------------------------------------------------------------------- #
def test_strong_fit_beats_keyword_stuffer():
    _, s_strong = _score(strong_fit())
    _, s_stuffer = _score(keyword_stuffer())
    assert s_strong > s_stuffer, (s_strong, s_stuffer)
    # the keyword stuffer should be firmly low despite a perfect skill list
    assert s_stuffer < 0.25


def test_honeypot_is_floored():
    f, s = _score(honeypot())
    assert f.honeypot is True
    assert f.honeypot_reasons
    assert s < 0.05, s


def test_strong_fit_is_high():
    _, s = _score(strong_fit())
    assert s > 0.6, s


def test_inactive_lowballs_availability():
    rec = strong_fit()
    rec["redrob_signals"] = _signals(last_active_date="2025-10-01",
                                     recruiter_response_rate=0.05)
    f, s_dead = _score(rec)
    _, s_live = _score(strong_fit())
    assert s_dead < s_live


if __name__ == "__main__":
    test_strong_fit_beats_keyword_stuffer()
    test_honeypot_is_floored()
    test_strong_fit_is_high()
    test_inactive_lowballs_availability()
    print("All assertions passed.")
