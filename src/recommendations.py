"""
Recommendation engine: bullet-wording suggestions, project relevance,
experience-vs-JD comparison, and interview question generation.

Guardrail followed throughout this module: suggestions only rearrange,
strengthen or ask the user to quantify wording that is ALREADY in their
resume. Nothing here invents tools, metrics or achievements the person
did not write themselves.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List

from src.keyword_engine import extract_skills
from src.resume_analyzer import BulletAnalysis, ACTION_VERBS
from src.utils import bullet_lines, tokenize

STRONG_VERB_SUGGESTIONS = {
    "worked on": "Built / Developed / Contributed to",
    "responsible for": "Owned / Managed / Led",
    "helped with": "Supported / Assisted in",
    "involved in": "Participated in / Contributed to",
    "assisted": "Supported / Collaborated on",
}


@dataclass
class BulletImprovement:
    current: str
    improved: str
    why: str


@dataclass
class ProjectRelevance:
    title: str
    text: str
    relevance_score: float
    matching_skills: List[str]
    missing_technologies: List[str]
    recommendation: str  # KEEP / REWRITE / REMOVE
    reasoning: str


@dataclass
class ExperienceComparison:
    entry_title: str
    text: str
    matching_skills: List[str]
    missing_requirements: List[str]


def improve_bullet(bullet: BulletAnalysis) -> BulletImprovement:
    text = bullet.text.strip()
    lower = text.lower()
    reasons = []
    improved = text

    for vague, suggestion in STRONG_VERB_SUGGESTIONS.items():
        if lower.startswith(vague):
            improved = suggestion.split(" / ")[0] + improved[len(vague):]
            reasons.append(f"replaced the passive opener \"{vague}\" with a stronger action verb")
            break
    else:
        if not bullet.has_action_verb:
            reasons.append("consider opening with a strong action verb (e.g. Built, Led, Designed, Automated)")

    if not bullet.has_metric:
        if not improved.endswith((".", "!")):
            improved = improved + "."
        improved += " (Add a measurable outcome here — e.g. a %, time saved, or scale, if available.)"
        reasons.append("no quantified outcome was detected — measurable impact strengthens ATS and recruiter scans")

    if not reasons:
        reasons.append("bullet already uses an action verb and includes a measurable detail")

    why = "; ".join(reasons).capitalize() + "."
    return BulletImprovement(current=text, improved=improved, why=why)


def weak_bullet_improvements(bullets: List[BulletAnalysis], limit: int = 12) -> List[BulletImprovement]:
    weak = [b for b in bullets if b.is_weak]
    return [improve_bullet(b) for b in weak[:limit]]


# ------------------------------------------------------------------
# Project relevance
# ------------------------------------------------------------------

def _split_projects(projects_text: str) -> List[str]:
    if not projects_text.strip():
        return []
    # split on blank-ish gaps or lines that look like a new project title
    blocks = re.split(r"\n\s*\n", projects_text)
    if len(blocks) <= 1:
        blocks = bullet_lines(projects_text)
    return [b.strip() for b in blocks if len(b.strip().split()) >= 3]


def analyze_project_relevance(projects_text: str, jd_skills: set) -> List[ProjectRelevance]:
    blocks = _split_projects(projects_text)
    results = []
    for block in blocks:
        title_line = block.split("\n")[0][:80]
        block_skills = extract_skills(block)
        matching = sorted(block_skills & jd_skills)
        missing = sorted(jd_skills - block_skills)[:5]
        relevance = round((len(matching) / len(jd_skills)) * 100, 1) if jd_skills else 0.0

        if relevance >= 40:
            rec = "KEEP"
            reasoning = "Strong overlap with the target job's required skills."
        elif relevance >= 15:
            rec = "REWRITE"
            reasoning = "Some overlap exists — reframe the description to foreground the matching skills and add quantified results."
        else:
            rec = "REWRITE"
            reasoning = "Limited overlap with this specific job, but the project may still show relevant fundamentals — consider reframing rather than deleting unless resume length is a concern."

        results.append(ProjectRelevance(
            title=title_line, text=block, relevance_score=relevance,
            matching_skills=matching, missing_technologies=missing,
            recommendation=rec, reasoning=reasoning,
        ))
    results.sort(key=lambda p: p.relevance_score, reverse=True)
    return results


# ------------------------------------------------------------------
# Experience vs JD comparison
# ------------------------------------------------------------------

def analyze_experience_entries(experience_text: str, jd_skills: set, jd_responsibilities: List[str]) -> List[ExperienceComparison]:
    blocks = _split_projects(experience_text)
    results = []
    resp_tokens = set()
    for r in jd_responsibilities:
        resp_tokens |= set(tokenize(r))

    for block in blocks:
        title_line = block.split("\n")[0][:80]
        block_skills = extract_skills(block)
        matching = sorted(block_skills & jd_skills)
        missing = sorted(jd_skills - block_skills)[:6]
        results.append(ExperienceComparison(
            entry_title=title_line, text=block,
            matching_skills=matching, missing_requirements=missing,
        ))
    return results


# ------------------------------------------------------------------
# Interview question generation
# ------------------------------------------------------------------

def generate_interview_questions(resume_text: str, matched_skills: List[str], missing_skills: List[str],
                                  projects_text: str, jd_title: str) -> Dict[str, List[str]]:
    questions: Dict[str, List[str]] = {
        "Technical": [], "Project": [], "Behavioural": [], "Role-specific": [], "Resume-based": [],
    }

    for skill in matched_skills[:6]:
        questions["Technical"].append(
            f"Walk me through how you've used {skill} in a real project, including a challenge you ran into."
        )

    project_blocks = _split_projects(projects_text)
    for block in project_blocks[:5]:
        title = block.split("\n")[0][:70]
        skills_in_block = sorted(extract_skills(block))
        if skills_in_block:
            questions["Project"].append(
                f"In your \"{title}\" project, explain how {skills_in_block[0]} was applied and why you chose that approach."
            )
        else:
            questions["Project"].append(f"Describe the goal, your specific contribution, and the outcome of \"{title}\".")

    questions["Behavioural"] = [
        "Tell me about a time you had to learn a new tool or technology quickly to complete a task.",
        "Describe a project that didn't go as planned. What did you do, and what did you learn?",
        "Tell me about a time you disagreed with a teammate on a technical decision. How was it resolved?",
    ]

    if jd_title and jd_title != "Not specified":
        questions["Role-specific"].append(
            f"What about the {jd_title} role interests you, and how does your background prepare you for it?"
        )
    for skill in missing_skills[:3]:
        questions["Role-specific"].append(
            f"This role expects familiarity with {skill}, which wasn't clearly listed on your resume — "
            f"how would you approach getting up to speed on it?"
        )

    for line in resume_text.split("\n"):
        line_clean = line.strip()
        if "@" in line_clean or "linkedin.com" in line_clean.lower() or "github.com" in line_clean.lower():
            continue
        if len(line_clean.split()) >= 6 and not line_clean.isupper():
            questions["Resume-based"].append(f"Can you elaborate on: \"{line_clean[:100]}\"?")
        if len(questions["Resume-based"]) >= 4:
            break

    return {k: v for k, v in questions.items() if v}
