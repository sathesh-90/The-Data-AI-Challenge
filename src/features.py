"""
features.py
===========

Turn one raw candidate record into a flat `CandidateFeatures` object holding
every derived signal the scorer and the reasoning generator need. All parsing
is defensive: missing / malformed fields degrade gracefully to neutral values.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import job_profile as JP

_REF = _dt.date(*JP.REFERENCE_DATE)


# --------------------------------------------------------------------------- #
# small parsing helpers
# --------------------------------------------------------------------------- #
def _parse_date(s: Optional[str]) -> Optional[_dt.date]:
    if not s or not isinstance(s, str):
        return None
    try:
        return _dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


def _days_since(d: Optional[_dt.date]) -> Optional[int]:
    if d is None:
        return None
    return (_REF - d).days


def _norm(text: str) -> str:
    return (text or "").lower().strip()


def _contains_any(text: str, vocab) -> bool:
    return any(term in text for term in vocab)


def _count_matches(text: str, vocab) -> int:
    return sum(1 for term in vocab if term in text)


@dataclass
class CandidateFeatures:
    candidate_id: str = ""
    name: str = ""
    current_title: str = ""
    current_title_norm: str = ""
    headline: str = ""
    summary: str = ""
    location: str = ""
    country: str = ""
    years_experience: float = 0.0

    # title classification
    title_class: str = "other"            # core | adjacent | non_eng | other

    # skill signals
    matched_core_skills: List[str] = field(default_factory=list)
    trusted_core_skills: List[str] = field(default_factory=list)
    core_skill_trust_sum: float = 0.0
    adjacent_skill_count: int = 0
    off_domain_count: int = 0
    has_nlp_ir: bool = False
    n_skills: int = 0

    # career evidence
    evidence_hits: int = 0
    evidence_terms: List[str] = field(default_factory=list)
    product_company: bool = False
    consulting_only: bool = False
    avg_tenure_months: float = 0.0
    n_roles: int = 0
    research_only: bool = False
    langchain_only_recent: bool = False

    # location
    location_class: str = "other"         # preferred | welcome | india | abroad
    willing_to_relocate: bool = False

    # behavioural signals
    response_rate: float = 0.0
    days_inactive: Optional[int] = None
    open_to_work: bool = False
    interview_completion: float = 0.0
    profile_completeness: float = 0.0
    saved_by_recruiters: int = 0
    notice_period_days: int = 0
    github_score: float = -1.0

    # honeypot / consistency
    honeypot: bool = False
    honeypot_reasons: List[str] = field(default_factory=list)


def extract(record: Dict) -> CandidateFeatures:
    f = CandidateFeatures()
    f.candidate_id = record.get("candidate_id", "")

    profile = record.get("profile") or {}
    f.name = profile.get("anonymized_name", "")
    f.current_title = profile.get("current_title", "") or ""
    f.current_title_norm = _norm(f.current_title)
    f.headline = profile.get("headline", "") or ""
    f.summary = profile.get("summary", "") or ""
    f.location = profile.get("location", "") or ""
    f.country = profile.get("country", "") or ""
    try:
        f.years_experience = float(profile.get("years_of_experience") or 0.0)
    except (TypeError, ValueError):
        f.years_experience = 0.0

    _classify_title(f)
    _analyse_skills(f, record)
    _analyse_career(f, record)
    _classify_location(f, record)
    _behavioural(f, record)
    _honeypot_checks(f, record)
    return f


# --------------------------------------------------------------------------- #
def _classify_title(f: CandidateFeatures) -> None:
    t = f.current_title_norm
    if _contains_any(t, JP.CORE_ENGINEER_TITLES):
        f.title_class = "core"
    elif _contains_any(t, JP.NON_ENGINEERING_TITLES):
        f.title_class = "non_eng"
    elif _contains_any(t, JP.ADJACENT_ENGINEER_TITLES):
        f.title_class = "adjacent"
    else:
        # fall back on headline keywords (e.g. "AI/ML" in headline)
        h = _norm(f.headline)
        if _contains_any(h, JP.CORE_ENGINEER_TITLES) or "machine learning" in h:
            f.title_class = "core"
        else:
            f.title_class = "other"


def _skill_trust(skill: Dict) -> float:
    """How much we believe a listed skill is real rather than keyword padding.

    Lazy keyword stuffing shows up as skills with 0 endorsements and ~0 months
    of use. Genuine skills carry endorsements and duration. Capped at 1.0.
    """
    endorsements = skill.get("endorsements") or 0
    duration = skill.get("duration_months") or 0
    prof = _norm(skill.get("proficiency", ""))

    trust = 0.25
    if duration >= 24:
        trust += 0.45
    elif duration >= 12:
        trust += 0.30
    elif duration >= 6:
        trust += 0.15
    if endorsements >= 20:
        trust += 0.30
    elif endorsements >= 5:
        trust += 0.18
    elif endorsements >= 1:
        trust += 0.08
    # claimed expert/advanced with zero real usage = not trustworthy
    if prof in ("expert", "advanced") and duration == 0 and endorsements == 0:
        trust = 0.0
    return min(trust, 1.0)


def _analyse_skills(f: CandidateFeatures, record: Dict) -> None:
    skills = record.get("skills") or []
    f.n_skills = len(skills)
    assessed = (record.get("redrob_signals") or {}).get("skill_assessment_scores") or {}

    for sk in skills:
        name = _norm(sk.get("name", ""))
        if not name:
            continue
        if name in JP.CORE_COMPETENCIES or _contains_any(name, JP.CORE_COMPETENCIES):
            f.matched_core_skills.append(sk.get("name", ""))
            trust = _skill_trust(sk)
            # a real assessment score on this skill reinforces trust
            if any(_norm(k) == name for k in assessed):
                trust = min(1.0, trust + 0.15)
            f.core_skill_trust_sum += trust
            if trust >= 0.5:
                f.trusted_core_skills.append(sk.get("name", ""))
            if name in ("nlp", "natural language processing", "information retrieval",
                        "retrieval", "semantic search", "ranking", "bert"):
                f.has_nlp_ir = True
        elif name in JP.ADJACENT_COMPETENCIES or _contains_any(name, JP.ADJACENT_COMPETENCIES):
            f.adjacent_skill_count += 1
        if name in JP.OFF_DOMAIN_SKILLS or _contains_any(name, JP.OFF_DOMAIN_SKILLS):
            f.off_domain_count += 1


def _analyse_career(f: CandidateFeatures, record: Dict) -> None:
    history = record.get("career_history") or []
    f.n_roles = len(history)

    blob = " ".join(
        _norm(r.get("description", "")) + " " + _norm(r.get("title", ""))
        for r in history
    )
    blob += " " + _norm(f.summary) + " " + _norm(f.headline)

    seen = set()
    for term in JP.EVIDENCE_PHRASES:
        if term in blob and term not in seen:
            seen.add(term)
    f.evidence_terms = sorted(seen)
    f.evidence_hits = len(seen)

    # NLP/IR exposure can also come from career text, not just the skills list
    if any(t in blob for t in ("nlp", "information retrieval", "retrieval",
                               "ranking", "search relevance", "semantic search")):
        f.has_nlp_ir = True

    # company type
    durations = []
    consulting_hits = 0
    industries = []
    for r in history:
        company = _norm(r.get("company", ""))
        industry = _norm(r.get("industry", ""))
        industries.append(industry)
        if _contains_any(company, JP.CONSULTING_COMPANIES):
            consulting_hits += 1
        d = r.get("duration_months")
        if isinstance(d, (int, float)) and d > 0:
            durations.append(float(d))

    f.avg_tenure_months = (sum(durations) / len(durations)) if durations else 0.0
    f.consulting_only = (f.n_roles > 0 and consulting_hits == f.n_roles)
    f.product_company = any(
        ind for ind in industries
        if ind and not _contains_any(ind, {"consulting", "services", "outsourc"})
    ) and not f.consulting_only

    # research-only: academic/research signals with no production evidence
    research_terms = ("research", "phd", "postdoc", "academic", "university",
                      "laboratory", "publication", "paper")
    prod_terms = ("production", "deployed", "real users", "at scale", "served",
                  "shipped", "launched")
    has_research = any(t in blob for t in research_terms)
    has_prod = any(t in blob for t in prod_terms)
    f.research_only = has_research and not has_prod and f.evidence_hits == 0

    # recent LangChain-only dabbler with no pre-LLM ML depth
    has_langchain = "langchain" in blob
    f.langchain_only_recent = (
        has_langchain and f.evidence_hits == 0 and f.core_skill_trust_sum < 1.0
    )


def _classify_location(f: CandidateFeatures, record: Dict) -> None:
    loc = _norm(f.location)
    country = _norm(f.country)
    signals = record.get("redrob_signals") or {}
    f.willing_to_relocate = bool(signals.get("willing_to_relocate"))

    if _contains_any(loc, JP.PREFERRED_CITIES):
        f.location_class = "preferred"
    elif _contains_any(loc, JP.WELCOME_CITIES):
        f.location_class = "welcome"
    elif country in ("india", "in") or "india" in country:
        f.location_class = "india"
    else:
        f.location_class = "abroad"


def _behavioural(f: CandidateFeatures, record: Dict) -> None:
    s = record.get("redrob_signals") or {}
    try:
        f.response_rate = float(s.get("recruiter_response_rate") or 0.0)
    except (TypeError, ValueError):
        f.response_rate = 0.0
    f.days_inactive = _days_since(_parse_date(s.get("last_active_date")))
    f.open_to_work = bool(s.get("open_to_work_flag"))
    try:
        f.interview_completion = float(s.get("interview_completion_rate") or 0.0)
    except (TypeError, ValueError):
        f.interview_completion = 0.0
    try:
        f.profile_completeness = float(s.get("profile_completeness_score") or 0.0)
    except (TypeError, ValueError):
        f.profile_completeness = 0.0
    f.saved_by_recruiters = int(s.get("saved_by_recruiters_30d") or 0)
    f.notice_period_days = int(s.get("notice_period_days") or 0)
    try:
        f.github_score = float(s.get("github_activity_score"))
    except (TypeError, ValueError):
        f.github_score = -1.0


def _honeypot_checks(f: CandidateFeatures, record: Dict) -> None:
    """Detect the ~80 'subtly impossible' profiles. We don't need to catch all
    of them - just enough internal-consistency violations to keep honeypots out
    of the top 100 (the >10% honeypot rate is a Stage-3 disqualifier)."""
    reasons: List[str] = []

    # (a) "expert"/"advanced" in many skills with 0 months of real use
    skills = record.get("skills") or []
    zero_use_expert = sum(
        1 for sk in skills
        if _norm(sk.get("proficiency", "")) in ("expert", "advanced")
        and (sk.get("duration_months") or 0) == 0
    )
    if zero_use_expert >= 3:
        reasons.append("multiple expert skills with 0 months of use")

    # (b) role duration grossly exceeds the actual date span
    for r in record.get("career_history") or []:
        start = _parse_date(r.get("start_date"))
        end = _parse_date(r.get("end_date")) or _REF
        dur = r.get("duration_months")
        if start and isinstance(dur, (int, float)):
            span_months = (end.year - start.year) * 12 + (end.month - start.month)
            if dur - span_months > 9:   # > ~9 months of impossible tenure
                reasons.append("role tenure exceeds its own date range")
                break

    # (c) total career tenure wildly exceeds stated years of experience window
    history = record.get("career_history") or []
    starts = [_parse_date(r.get("start_date")) for r in history]
    starts = [d for d in starts if d]
    if starts and f.years_experience > 0:
        earliest = min(starts)
        career_span_years = (_REF - earliest).days / 365.25
        # claims far more experience than their earliest job allows
        if f.years_experience - career_span_years > 4.0:
            reasons.append("years_of_experience exceeds career span")

    # (d) sum of role durations far exceeds calendar career span
    durations = [r.get("duration_months") for r in history
                 if isinstance(r.get("duration_months"), (int, float))]
    if starts and durations:
        earliest = min(starts)
        span_months = max(1, (_REF - earliest).days / 30.4)
        if sum(durations) - span_months > 18:   # heavily overlapping/impossible
            reasons.append("overlapping role durations exceed timeline")

    if reasons:
        f.honeypot = True
        f.honeypot_reasons = reasons
