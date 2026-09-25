"""
Resume structure analysis: which sections exist, bullet quality,
repeated phrasing, and other signals used later by ATS scoring.
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List

from src.parser import ParsedDocument, IMPORTANT_SECTIONS
from src.utils import bullet_lines, tokenize

ACTION_VERBS = {
    "led", "built", "designed", "developed", "implemented", "created",
    "managed", "optimized", "automated", "improved", "reduced", "increased",
    "launched", "deployed", "engineered", "architected", "analyzed",
    "researched", "collaborated", "coordinated", "delivered", "trained",
    "mentored", "streamlined", "integrated", "migrated", "resolved",
    "achieved", "spearheaded", "established", "presented", "authored",
}

METRIC_PATTERN = re.compile(
    r"(\d+(\.\d+)?\s*%|\$\s?\d+[kKmMbB]?|\b\d+[kKmMbB]\b|\b\d{2,}\+?\b)"
)


@dataclass
class BulletAnalysis:
    text: str
    section: str
    has_metric: bool
    has_action_verb: bool
    word_count: int
    is_weak: bool


@dataclass
class StructureReport:
    detected_sections: List[str] = field(default_factory=list)
    missing_sections: List[str] = field(default_factory=list)
    section_order: List[str] = field(default_factory=list)
    bullets: List[BulletAnalysis] = field(default_factory=list)
    bullet_count: int = 0
    avg_bullet_length: float = 0.0
    bullets_with_metrics_pct: float = 0.0
    bullets_with_action_verbs_pct: float = 0.0
    repeated_phrases: List[str] = field(default_factory=list)
    formatting_issues: List[str] = field(default_factory=list)
    content_density: str = "moderate"


def _is_weak_bullet(bullet: str, has_metric: bool, has_action_verb: bool) -> bool:
    weak = not has_action_verb or not has_metric
    vague_starts = ("worked on", "responsible for", "helped with", "involved in", "assisted")
    if bullet.lower().startswith(vague_starts):
        weak = True
    return weak


_TITLE_LINE_RE = re.compile(
    r"^[A-Za-z0-9&.,'\- ]{2,70},.{0,40}(19|20)\d{2}\s*(-|–|to)\s*((19|20)\d{2}|present|current)",
    re.IGNORECASE,
)


def _looks_like_entry_header(line: str) -> bool:
    """Lines like 'Data Scientist, Acme Corp, 2022-2024' are job/degree
    headers, not achievement bullets — exclude them from bullet analysis."""
    return bool(_TITLE_LINE_RE.match(line.strip()))


def analyze_bullets(sections: Dict[str, str]) -> List[BulletAnalysis]:
    analyzed = []
    skip_sections = ("Header", "Skills", "Education", "Certifications", "Languages")
    for section_name, section_text in sections.items():
        if section_name in skip_sections:
            continue
        for bullet in bullet_lines(section_text):
            if _looks_like_entry_header(bullet):
                continue
            has_metric = bool(METRIC_PATTERN.search(bullet))
            first_word = bullet.strip().split(" ")[0].lower().strip(".,")
            has_action_verb = first_word in ACTION_VERBS
            analyzed.append(BulletAnalysis(
                text=bullet,
                section=section_name,
                has_metric=has_metric,
                has_action_verb=has_action_verb,
                word_count=len(bullet.split()),
                is_weak=_is_weak_bullet(bullet, has_metric, has_action_verb),
            ))
    return analyzed


def find_repeated_phrases(text: str, min_repeats: int = 3) -> List[str]:
    """Find 2-3 word phrases repeated often enough to look like padding."""
    tokens = tokenize(text)
    phrases = Counter()
    for n in (2, 3):
        for i in range(len(tokens) - n + 1):
            phrase = " ".join(tokens[i:i + n])
            phrases[phrase] += 1
    return [p for p, c in phrases.most_common(15) if c >= min_repeats]


def detect_formatting_issues(raw_text: str, extraction_quality: str) -> List[str]:
    issues = []
    if extraction_quality == "poor":
        issues.append("Little to no text could be extracted — likely a scanned image or heavily graphical layout.")
    if extraction_quality == "partial":
        issues.append("Extraction returned unusually little text for a full resume.")
    if raw_text.count("|") > 40:
        issues.append("Heavy use of table-like pipe characters detected — tables can confuse ATS parsers.")
    unusual_symbols = re.findall(r"[^\x00-\x7F]", raw_text)
    if len(unusual_symbols) > 15:
        issues.append("Several non-standard symbols/characters detected — some ATS systems may misread these.")
    if len(raw_text.split("\n")) < 8:
        issues.append("Very few line breaks detected — the layout may rely on columns or text boxes that don't parse well.")
    return issues


def analyze_structure(parsed: ParsedDocument) -> StructureReport:
    detected = [s for s in parsed.section_order if s in IMPORTANT_SECTIONS]
    missing = [s for s in IMPORTANT_SECTIONS if s not in parsed.sections]

    bullets = analyze_bullets(parsed.sections) if parsed.sections else analyze_bullets(
        {"Header": parsed.raw_text}
    )
    bullet_count = len(bullets)
    avg_len = round(sum(b.word_count for b in bullets) / bullet_count, 1) if bullet_count else 0.0
    with_metrics = round(sum(1 for b in bullets if b.has_metric) / bullet_count * 100, 1) if bullet_count else 0.0
    with_verbs = round(sum(1 for b in bullets if b.has_action_verb) / bullet_count * 100, 1) if bullet_count else 0.0

    word_count = len(parsed.raw_text.split())
    if word_count < 200:
        density = "sparse"
    elif word_count > 900:
        density = "dense"
    else:
        density = "moderate"

    return StructureReport(
        detected_sections=detected,
        missing_sections=missing,
        section_order=parsed.section_order,
        bullets=bullets,
        bullet_count=bullet_count,
        avg_bullet_length=avg_len,
        bullets_with_metrics_pct=with_metrics,
        bullets_with_action_verbs_pct=with_verbs,
        repeated_phrases=find_repeated_phrases(parsed.raw_text),
        formatting_issues=detect_formatting_issues(parsed.raw_text, parsed.extraction_quality),
        content_density=density,
    )
