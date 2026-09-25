"""
Job description analysis: pulls out title, requirements, experience and
education expectations, and classifies each requirement line.
"""

import re
from dataclasses import dataclass, field
from typing import List, Set

from src.keyword_engine import extract_skills
from src.utils import sentences, normalize_whitespace

MUST_HAVE_MARKERS = [
    "required", "must have", "must-have", "mandatory", "requirements",
    "you have", "you must", "minimum qualifications", "essential",
]
NICE_TO_HAVE_MARKERS = [
    "nice to have", "preferred", "bonus", "plus", "good to have",
    "desirable", "advantageous",
]
RESPONSIBILITY_MARKERS = [
    "responsibilities", "you will", "duties", "what you'll do",
    "role overview", "day to day", "you'll be",
]
EDUCATION_MARKERS = [
    "bachelor", "master", "phd", "degree", "b.tech", "m.tech", "b.e",
    "diploma", "university", "college",
]
EXPERIENCE_PATTERNS = [
    re.compile(r"(\d+)\s*\+?\s*-\s*(\d+)\s*years?", re.IGNORECASE),
    re.compile(r"(\d+)\s*\+\s*years?", re.IGNORECASE),
    re.compile(r"(\d+)\s*years?\s*(of)?\s*experience", re.IGNORECASE),
    re.compile(r"minimum\s*(\d+)\s*years?", re.IGNORECASE),
]

DOMAIN_HINTS = [
    "healthcare", "fintech", "finance", "banking", "e-commerce", "retail",
    "insurance", "logistics", "manufacturing", "telecom", "gaming",
    "education", "edtech", "saas", "b2b", "b2c", "cybersecurity",
    "biotech", "pharma", "automotive", "real estate", "supply chain",
]

TITLE_PATTERNS = [
    re.compile(r"^(job title|position|role)\s*[:\-]\s*(.+)$", re.IGNORECASE),
]


@dataclass
class Requirement:
    text: str
    category: str  # MUST_HAVE / NICE_TO_HAVE / RESPONSIBILITY / DOMAIN / EDUCATION / EXPERIENCE
    skills_mentioned: Set[str] = field(default_factory=set)


@dataclass
class JDAnalysis:
    job_title: str
    required_skills: Set[str] = field(default_factory=set)
    preferred_skills: Set[str] = field(default_factory=set)
    all_skills: Set[str] = field(default_factory=set)
    min_years_experience: int = 0
    experience_text: str = "Not specified"
    education_requirements: List[str] = field(default_factory=list)
    domain_hints: List[str] = field(default_factory=list)
    requirements: List[Requirement] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)
    soft_skills: List[str] = field(default_factory=list)


def _guess_title(text: str, lines: List[str]) -> str:
    for line in lines[:5]:
        for pattern in TITLE_PATTERNS:
            m = pattern.match(line.strip())
            if m:
                return normalize_whitespace(m.group(2))
    for line in lines[:3]:
        words = line.strip().split()
        if 1 < len(words) <= 7 and not line.strip().endswith("."):
            return normalize_whitespace(line)
    return "Not specified"


def _extract_min_experience(text: str) -> (int, str):
    text_lower = text.lower()
    best = 0
    best_str = "Not specified"
    for pattern in EXPERIENCE_PATTERNS:
        for m in pattern.finditer(text_lower):
            nums = [int(g) for g in m.groups() if g and g.isdigit()]
            if nums:
                val = min(nums)
                if val > best:
                    best = val
                    best_str = m.group().strip()
    return best, best_str


def _extract_education(text: str) -> List[str]:
    text_lower = text.lower()
    found = []
    degree_map = {
        "bachelor": "Bachelor's degree",
        "b.tech": "B.Tech",
        "b.e": "B.E.",
        "master": "Master's degree",
        "m.tech": "M.Tech",
        "phd": "PhD",
        "diploma": "Diploma",
    }
    for key, label in degree_map.items():
        if key in text_lower and label not in found:
            found.append(label)
    return found


def _extract_domains(text: str) -> List[str]:
    text_lower = text.lower()
    return [d.title() for d in DOMAIN_HINTS if d in text_lower]


def _classify_line(line: str) -> str:
    lower = line.lower()
    if any(m in lower for m in EDUCATION_MARKERS):
        return "EDUCATION"
    if any(re.search(p, lower) for p in [r"\d+\s*\+?\s*years?"]):
        return "EXPERIENCE"
    if any(m in lower for m in NICE_TO_HAVE_MARKERS):
        return "NICE_TO_HAVE"
    if any(m in lower for m in RESPONSIBILITY_MARKERS):
        return "RESPONSIBILITY"
    if any(m in lower for m in MUST_HAVE_MARKERS):
        return "MUST_HAVE"
    return "MUST_HAVE" if line.strip().startswith(("-", "•", "*")) else "RESPONSIBILITY"


def _split_into_requirement_lines(text: str) -> List[str]:
    lines = [normalize_whitespace(l) for l in text.split("\n") if normalize_whitespace(l)]
    result = []
    for line in lines:
        if len(line.split()) < 2:
            continue
        result.append(line)
    if len(result) < 3:
        result = sentences(text)
    return result


def analyze_jd(text: str) -> JDAnalysis:
    lines = [l for l in text.split("\n") if l.strip()]
    title = _guess_title(text, lines)
    min_years, exp_text = _extract_min_experience(text)
    education = _extract_education(text)
    domains = _extract_domains(text)

    req_lines = _split_into_requirement_lines(text)

    # section-aware pass: text after a "preferred/nice to have" heading is
    # treated as preferred even if individual lines don't repeat the marker
    requirements: List[Requirement] = []
    responsibilities: List[str] = []
    current_mode = "MUST_HAVE"

    for line in req_lines:
        lower = line.lower()
        if any(m in lower for m in NICE_TO_HAVE_MARKERS) and len(line.split()) <= 6:
            current_mode = "NICE_TO_HAVE"
            continue
        if any(m in lower for m in RESPONSIBILITY_MARKERS) and len(line.split()) <= 6:
            current_mode = "RESPONSIBILITY"
            continue
        if any(m in lower for m in MUST_HAVE_MARKERS) and len(line.split()) <= 6:
            current_mode = "MUST_HAVE"
            continue

        category = _classify_line(line)
        if category in ("MUST_HAVE", "RESPONSIBILITY") and current_mode == "NICE_TO_HAVE":
            category = "NICE_TO_HAVE"
        elif category == "MUST_HAVE" and current_mode == "RESPONSIBILITY":
            category = "RESPONSIBILITY"

        line_skills = extract_skills(line)
        requirements.append(Requirement(text=line, category=category, skills_mentioned=line_skills))
        if category == "RESPONSIBILITY":
            responsibilities.append(line)

    all_skills = extract_skills(text)
    required_skills = set()
    preferred_skills = set()
    for req in requirements:
        if req.category == "NICE_TO_HAVE":
            preferred_skills |= req.skills_mentioned
        else:
            required_skills |= req.skills_mentioned
    # anything found in the whole doc but not bucketed yet defaults to required
    required_skills |= (all_skills - preferred_skills - required_skills)

    soft_skill_names = ["Communication", "Leadership", "Problem Solving", "Project Management", "Agile/Scrum"]
    soft_skills = [s for s in soft_skill_names if s in all_skills]

    return JDAnalysis(
        job_title=title,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        all_skills=all_skills,
        min_years_experience=min_years,
        experience_text=exp_text,
        education_requirements=education,
        domain_hints=domains,
        requirements=requirements,
        responsibilities=responsibilities[:15],
        soft_skills=soft_skills,
    )
