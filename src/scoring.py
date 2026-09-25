"""
Scoring engine: combines the matcher's raw layer scores into a transparent
Overall Match Score, plus a separate Estimated ATS Compatibility score.

SCORING FORMULA (documented, not a black box)
------------------------------------------------
Overall Match Score =
      35% Skill Match          (normalized keyword/taxonomy coverage)
    + 20% Experience Match     (years required vs. years detected)
    + 15% Responsibility Match (TF-IDF overlap of experience vs. JD duties)
    + 10% Education Match      (degree level alignment)
    + 10% Keyword Coverage     (exact keyword overlap)
    + 10% Semantic Similarity  (spaCy vectors, or TF-IDF if unavailable)

These weights emphasise concrete, verifiable skill and experience overlap
over generic textual similarity, since two very differently-worded resumes
can be an excellent fit and two similar-sounding ones a poor one.

Estimated ATS Compatibility (0-100) is a SEPARATE score from Overall Match.
It reflects resume structure/formatting quality, independent of any single
job description, and is explicitly labelled "estimated" because no vendor
ATS algorithm is being replicated here.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from src.matcher import MatchResult
from src.resume_analyzer import StructureReport
from src.utils import clip

WEIGHTS = {
    "skill_match": 0.35,
    "experience_match": 0.20,
    "responsibility_match": 0.15,
    "education_match": 0.10,
    "keyword_coverage": 0.10,
    "semantic_similarity": 0.10,
}

ATS_WEIGHTS = {
    "sections": 0.30,
    "keywords": 0.20,
    "action_verbs": 0.15,
    "metrics": 0.15,
    "formatting": 0.10,
    "contact_info": 0.10,
}


@dataclass
class ScoreBreakdown:
    overall_match: float = 0.0
    component_scores: Dict[str, float] = field(default_factory=dict)
    component_weights: Dict[str, float] = field(default_factory=dict)
    ats_score: float = 0.0
    ats_components: Dict[str, float] = field(default_factory=dict)
    ats_strengths: List[str] = field(default_factory=list)
    ats_warnings: List[str] = field(default_factory=list)


def compute_overall_match(match: MatchResult) -> (float, Dict[str, float]):
    components = {
        "skill_match": match.normalized_keyword_score,
        "experience_match": match.experience_score,
        "responsibility_match": match.responsibility_score,
        "education_match": match.education_score,
        "keyword_coverage": match.exact_keyword_score,
        "semantic_similarity": match.semantic_score,
    }
    overall = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
    return round(clip(overall), 2), {k: round(v, 2) for k, v in components.items()}


def compute_ats_score(structure: StructureReport, has_contact_info: bool, keyword_coverage: float) -> ScoreBreakdown:
    important_total = 5
    section_score = clip((len(structure.detected_sections) / important_total) * 100)

    keyword_score = clip(keyword_coverage)

    verb_score = clip(structure.bullets_with_action_verbs_pct)
    metric_score = clip(structure.bullets_with_metrics_pct)

    formatting_penalty = min(len(structure.formatting_issues) * 15, 100)
    formatting_score = clip(100 - formatting_penalty)

    contact_score = 100.0 if has_contact_info else 40.0

    components = {
        "sections": section_score,
        "keywords": keyword_score,
        "action_verbs": verb_score,
        "metrics": metric_score,
        "formatting": formatting_score,
        "contact_info": contact_score,
    }
    ats_total = sum(components[k] * ATS_WEIGHTS[k] for k in ATS_WEIGHTS)

    strengths, warnings = [], []
    if section_score >= 80:
        strengths.append("Standard, ATS-friendly section headings detected.")
    else:
        warnings.append(f"Missing sections: {', '.join(structure.missing_sections) or 'none'}.")

    if keyword_score >= 60:
        strengths.append("Strong keyword coverage against the job description.")
    else:
        warnings.append("Keyword coverage against the job description is low.")

    if verb_score >= 60:
        strengths.append("Most bullet points start with strong action verbs.")
    else:
        warnings.append("Many bullets don't open with a strong action verb.")

    if metric_score >= 40:
        strengths.append("A good share of bullets include measurable outcomes.")
    else:
        warnings.append("Few bullets include quantified/measurable outcomes.")

    if structure.formatting_issues:
        warnings.extend(structure.formatting_issues)
    else:
        strengths.append("No major formatting red flags detected.")

    if not has_contact_info:
        warnings.append("Contact information (email/phone) could not be clearly detected.")
    else:
        strengths.append("Contact information is clearly present.")

    return ScoreBreakdown(
        ats_score=round(clip(ats_total), 2),
        ats_components={k: round(v, 2) for k, v in components.items()},
        ats_strengths=strengths,
        ats_warnings=warnings,
    )


def build_score_breakdown(match: MatchResult, structure: StructureReport, has_contact_info: bool) -> ScoreBreakdown:
    overall, components = compute_overall_match(match)
    ats = compute_ats_score(structure, has_contact_info, match.exact_keyword_score)
    ats.overall_match = overall
    ats.component_scores = components
    ats.component_weights = {k: round(v * 100) for k, v in WEIGHTS.items()}
    return ats
