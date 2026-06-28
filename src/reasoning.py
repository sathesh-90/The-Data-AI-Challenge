"""
reasoning.py
============

Generate the per-candidate `reasoning` string. Stage-4 manual review checks
that reasoning is (1) specific to real profile facts, (2) connected to JD
requirements, (3) honest about concerns, (4) free of hallucination, (5) varied,
and (6) consistent with the rank.

So every clause below is built ONLY from values actually present in the
candidate's features - we never invent a skill or employer.
"""

from __future__ import annotations

from .features import CandidateFeatures
from .scoring import ScoreBreakdown


def _fmt_years(y: float) -> str:
    return f"{y:.1f} yrs"


def _strengths(f: CandidateFeatures, bd: ScoreBreakdown) -> str:
    parts = []

    # title / role framing
    title = f.current_title.strip() or "engineer"
    parts.append(f"{title} with {_fmt_years(f.years_experience)} experience")

    # named, trusted core skills (only ones they genuinely have)
    skills = f.trusted_core_skills[:3]
    if skills:
        parts.append("strong on " + ", ".join(skills))
    elif f.matched_core_skills[:2]:
        parts.append("lists " + ", ".join(f.matched_core_skills[:2]))

    # concrete build evidence connects to the JD's core ask
    if f.evidence_hits >= 1:
        ev = ", ".join(f.evidence_terms[:2])
        parts.append(f"career history shows {ev}")

    # location relevance (JD names Pune/Noida + welcome cities)
    if f.location_class in ("preferred", "welcome") and f.location:
        parts.append(f"based in {f.location}")
    elif f.location_class == "india" and f.willing_to_relocate:
        parts.append(f"in {f.location} and open to relocate")

    # availability signal
    if f.response_rate >= 0.5:
        parts.append(f"responsive to recruiters ({f.response_rate:.2f})")

    return "; ".join(parts)


def _concern_list(f: CandidateFeatures) -> list:
    c = []
    if f.title_class == "non_eng":
        c.append(f"title '{f.current_title}' is non-engineering despite AI skills listed")
    if f.years_experience and f.years_experience < 5:
        c.append("below the 5-9 yr band")
    elif f.years_experience > 12:
        c.append("more senior than the target band")
    if f.consulting_only:
        c.append("career entirely at services/consulting firms")
    if f.location_class == "abroad":
        c.append("based outside India (no visa sponsorship)")
    if f.response_rate <= 0.15:
        c.append(f"low recruiter response rate ({f.response_rate:.2f})")
    if f.days_inactive is not None and f.days_inactive >= 180:
        c.append(f"inactive ~{f.days_inactive} days")
    if f.notice_period_days > 60:
        c.append(f"{f.notice_period_days}-day notice period")
    if f.off_domain_count >= 3 and not f.has_nlp_ir:
        c.append("primary expertise is CV/speech without NLP/IR")
    if f.evidence_hits == 0 and f.title_class in ("adjacent", "other"):
        c.append("no clear evidence of shipping ranking/search systems")
    return c


def build_reasoning(f: CandidateFeatures, bd: ScoreBreakdown, rank: int) -> str:
    """Compose a 1-2 sentence justification whose tone matches the rank."""
    strengths = _strengths(f, bd)
    concerns = _concern_list(f)

    # Tone matches rank bucket so reasoning never contradicts placement.
    if rank <= 10:
        lead = strengths
        tail = ""
        if concerns:
            tail = f" Minor concern: {concerns[0]}."
        text = f"{lead}." + tail
    elif rank <= 50:
        lead = strengths
        tail = f" Concern: {concerns[0]}." if concerns else ""
        text = f"{lead}." + tail
    else:
        # lower ranks: lead with the limiting factor, stay honest
        lead_label = "Included as filler" if rank > 85 else "Ranked lower"
        if concerns:
            text = (f"{lead_label}: {concerns[0]}"
                    + (f"; also {concerns[1]}" if len(concerns) > 1 else "")
                    + f". Still a fit on paper - {strengths}.")
        else:
            text = f"Borderline fit. {strengths}."

    # keep it tidy and CSV-safe (csv writer quotes commas; we just trim length)
    text = " ".join(text.split())
    if len(text) > 320:
        text = text[:317].rstrip(" ,;") + "..."
    return text
