"""
Multi-layer matching engine.

Layers implemented (no Hugging Face anywhere):
  1. Exact keyword matching       - raw substring/word match
  2. Normalized keyword matching  - via the skill alias/taxonomy engine
  3. Skill taxonomy matching      - category-level overlap
  4. TF-IDF similarity            - scikit-learn, classic bag-of-words
  5. Semantic similarity          - spaCy word vectors (en_core_web_md),
                                     falls back gracefully to TF-IDF-only
                                     if the vector model isn't available
  6. Experience alignment         - years required vs. years found in resume
  7. Education alignment          - degree requirement vs. resume education
  8. Responsibility alignment     - TF-IDF similarity of responsibility text
                                     against the resume's experience section

Each layer is deliberately kept transparent and inspectable so the final
score can be explained rather than treated as a black box.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.keyword_engine import extract_skills, canonical_category
from src.utils import tokenize, pct

_SPACY_MODEL = None
_SPACY_LOAD_ATTEMPTED = False


def get_spacy_model():
    """Lazily load a spaCy medium model (word vectors) if it is installed.
    Returns None if unavailable so callers can degrade gracefully — this is
    NOT a Hugging Face model, it ships through spaCy's own model index."""
    global _SPACY_MODEL, _SPACY_LOAD_ATTEMPTED
    if _SPACY_LOAD_ATTEMPTED:
        return _SPACY_MODEL
    _SPACY_LOAD_ATTEMPTED = True
    try:
        import spacy
        try:
            _SPACY_MODEL = spacy.load("en_core_web_md")
        except OSError:
            _SPACY_MODEL = spacy.load("en_core_web_sm")
    except Exception:
        _SPACY_MODEL = None
    return _SPACY_MODEL


# ------------------------------------------------------------------
# Experience extraction (from resume free text)
# ------------------------------------------------------------------

YEAR_RANGE_RE = re.compile(
    r"(19|20)\d{2}\s*(?:-|–|to)\s*(present|current|now|(19|20)\d{2})",
    re.IGNORECASE,
)


def estimate_resume_experience_years(text: str) -> float:
    """Sum non-overlapping-ish year ranges found in the resume as a rough
    proxy for total professional experience. This is a heuristic, not a
    guarantee — it is only used as one input signal among several."""
    import datetime
    current_year = datetime.datetime.now().year
    spans = []
    for m in YEAR_RANGE_RE.finditer(text):
        start = int(m.group(0)[:4])
        end_raw = m.group(2)
        end = current_year if end_raw.lower() in ("present", "current", "now") else int(end_raw)
        if end >= start and (end - start) <= 40:
            spans.append((start, end))
    if not spans:
        return 0.0
    spans.sort()
    total = 0
    last_end = None
    for start, end in spans:
        if last_end is None or start > last_end:
            total += (end - start)
            last_end = end
        elif end > last_end:
            total += (end - last_end)
            last_end = end
    return float(total)


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------

@dataclass
class SkillMatchResult:
    matched: Set[str] = field(default_factory=set)
    partial: Set[str] = field(default_factory=set)
    missing: Set[str] = field(default_factory=set)
    category_coverage: Dict[str, float] = field(default_factory=dict)


@dataclass
class MatchResult:
    exact_keyword_score: float = 0.0
    normalized_keyword_score: float = 0.0
    taxonomy_category_score: float = 0.0
    tfidf_score: float = 0.0
    semantic_score: float = 0.0
    semantic_method: str = "tfidf-only"
    experience_score: float = 0.0
    education_score: float = 0.0
    responsibility_score: float = 0.0
    keyword_coverage: float = 0.0
    skill_match: SkillMatchResult = field(default_factory=SkillMatchResult)
    resume_years: float = 0.0
    required_years: int = 0


# ------------------------------------------------------------------
# Layer 1 & 2: exact + normalized keyword matching
# ------------------------------------------------------------------

def exact_keyword_score(resume_text: str, jd_text: str) -> float:
    jd_tokens = set(tokenize(jd_text))
    resume_tokens = set(tokenize(resume_text))
    if not jd_tokens:
        return 0.0
    overlap = jd_tokens & resume_tokens
    return pct(len(overlap), len(jd_tokens))


def normalized_skill_match(resume_text: str, jd_skills: Set[str]) -> SkillMatchResult:
    resume_skills = extract_skills(resume_text)
    matched = resume_skills & jd_skills
    missing = jd_skills - resume_skills

    # partial: a related skill in the same taxonomy category is present,
    # but the exact required skill is not (never claim the exact skill exists)
    partial = set()
    still_missing = set()
    for skill in missing:
        cat = canonical_category(skill)
        same_category_present = any(canonical_category(s) == cat for s in resume_skills)
        if same_category_present and cat != "Other":
            partial.add(skill)
        else:
            still_missing.add(skill)

    coverage = pct(len(matched), len(jd_skills)) if jd_skills else 0.0

    category_totals: Dict[str, int] = {}
    category_hits: Dict[str, int] = {}
    for skill in jd_skills:
        cat = canonical_category(skill)
        category_totals[cat] = category_totals.get(cat, 0) + 1
        if skill in matched:
            category_hits[cat] = category_hits.get(cat, 0) + 1
    category_coverage = {
        cat: pct(category_hits.get(cat, 0), total) for cat, total in category_totals.items()
    }

    return SkillMatchResult(
        matched=matched, partial=partial, missing=still_missing,
        category_coverage=category_coverage,
    ), coverage


# ------------------------------------------------------------------
# Layer 3: taxonomy category-level score
# ------------------------------------------------------------------

def taxonomy_category_score(skill_result: SkillMatchResult) -> float:
    if not skill_result.category_coverage:
        return 0.0
    values = list(skill_result.category_coverage.values())
    return round(sum(values) / len(values), 2)


# ------------------------------------------------------------------
# Layer 4: TF-IDF similarity
# ------------------------------------------------------------------

def tfidf_similarity(resume_text: str, jd_text: str) -> float:
    if not resume_text.strip() or not jd_text.strip():
        return 0.0
    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        matrix = vectorizer.fit_transform([resume_text, jd_text])
        sim = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
        return round(float(sim) * 100, 2)
    except ValueError:
        return 0.0


# ------------------------------------------------------------------
# Layer 5: semantic similarity via spaCy vectors (fallback: TF-IDF)
# ------------------------------------------------------------------

def semantic_similarity(resume_text: str, jd_text: str) -> (float, str):
    nlp = get_spacy_model()
    if nlp is not None and nlp.meta.get("vectors", {}).get("width", 0) > 0:
        try:
            doc_a = nlp(resume_text[:100000])
            doc_b = nlp(jd_text[:100000])
            if doc_a.has_vector and doc_b.has_vector and doc_a.vector_norm and doc_b.vector_norm:
                sim = doc_a.similarity(doc_b)
                return round(float(sim) * 100, 2), "spaCy word vectors (en_core_web_md)"
        except Exception:
            pass
    # graceful fallback — reuse TF-IDF so the pipeline always returns a value
    return tfidf_similarity(resume_text, jd_text), "tfidf-fallback"


# ------------------------------------------------------------------
# Layer 6 & 7: experience / education alignment
# ------------------------------------------------------------------

def experience_alignment(resume_years: float, required_years: int) -> float:
    if required_years <= 0:
        return 100.0
    if resume_years >= required_years:
        return 100.0
    return round(pct(resume_years, required_years), 2)


def education_alignment(resume_text: str, jd_education: List[str]) -> float:
    if not jd_education:
        return 100.0
    resume_lower = resume_text.lower()
    degree_order = ["diploma", "bachelor", "b.tech", "b.e", "master", "m.tech", "phd"]
    resume_level = -1
    for i, d in enumerate(degree_order):
        if d in resume_lower:
            resume_level = max(resume_level, i)
    required_level = -1
    for req in jd_education:
        for i, d in enumerate(degree_order):
            if d in req.lower():
                required_level = max(required_level, i)
    if resume_level == -1:
        return 30.0  # education mentioned as requirement but not clearly detected in resume
    if resume_level >= required_level:
        return 100.0
    return round(pct(resume_level + 1, required_level + 1), 2)


# ------------------------------------------------------------------
# Layer 8: responsibility alignment
# ------------------------------------------------------------------

def responsibility_alignment(resume_experience_text: str, responsibilities: List[str]) -> float:
    if not responsibilities or not resume_experience_text.strip():
        return 0.0
    jd_resp_text = " ".join(responsibilities)
    return tfidf_similarity(resume_experience_text, jd_resp_text)


# ------------------------------------------------------------------
# Orchestration
# ------------------------------------------------------------------

def run_full_match(resume_text: str, resume_experience_text: str, jd_text: str, jd_analysis) -> MatchResult:
    result = MatchResult()

    result.exact_keyword_score = exact_keyword_score(resume_text, jd_text)

    skill_result, coverage = normalized_skill_match(resume_text, jd_analysis.all_skills)
    result.skill_match = skill_result
    result.normalized_keyword_score = coverage
    result.keyword_coverage = coverage

    result.taxonomy_category_score = taxonomy_category_score(skill_result)
    result.tfidf_score = tfidf_similarity(resume_text, jd_text)
    result.semantic_score, result.semantic_method = semantic_similarity(resume_text, jd_text)

    result.resume_years = estimate_resume_experience_years(resume_text)
    result.required_years = jd_analysis.min_years_experience
    result.experience_score = experience_alignment(result.resume_years, result.required_years)

    result.education_score = education_alignment(resume_text, jd_analysis.education_requirements)
    result.responsibility_score = responsibility_alignment(
        resume_experience_text or resume_text, jd_analysis.responsibilities
    )

    return result
