"""
Turns raw scores + matched/missing skill sets into plain-English
explanations. Every sentence here references something actually detected
in the analysis — nothing is invented or templated with placeholder facts.
"""

from typing import List

from src.matcher import MatchResult
from src.jd_analyzer import JDAnalysis
from src.scoring import ScoreBreakdown


def overall_explanation(scores: ScoreBreakdown, match: MatchResult, jd: JDAnalysis) -> str:
    matched = sorted(match.skill_match.matched)
    missing = sorted(match.skill_match.missing)

    parts = []
    if matched:
        top_matched = ", ".join(matched[:5])
        parts.append(f"Your resume aligns with {top_matched}")
        if len(matched) > 5:
            parts[-1] += f" and {len(matched) - 5} other required skill(s)"
        parts[-1] += "."
    else:
        parts.append("Your resume does not clearly mention any of the skills this job description asks for.")

    if missing:
        top_missing = ", ".join(missing[:4])
        parts.append(f"It lacks explicit evidence of {top_missing}.")

    if match.required_years > 0:
        if match.resume_years >= match.required_years:
            parts.append(
                f"The role asks for about {match.required_years}+ years of experience, and roughly "
                f"{match.resume_years:.0f} were detected in your resume's date ranges."
            )
        else:
            parts.append(
                f"The role asks for about {match.required_years}+ years of experience; only around "
                f"{match.resume_years:.0f} could be detected from your resume's date ranges."
            )

    if scores.overall_match >= 75:
        verdict = "This is a strong overall match."
    elif scores.overall_match >= 55:
        verdict = "This is a moderate match with some clear gaps."
    else:
        verdict = "This is a weak match based on the detected skills and experience."
    parts.append(verdict)

    return " ".join(parts)


def skill_importance(skill: str, jd: JDAnalysis) -> str:
    if skill in jd.required_skills:
        return "Listed as a core requirement in the job description."
    if skill in jd.preferred_skills:
        return "Mentioned as a preferred / nice-to-have skill."
    return "Mentioned in the job description."


def ats_summary_line(scores: ScoreBreakdown) -> str:
    if scores.ats_score >= 80:
        return "Strong, ATS-friendly formatting overall."
    if scores.ats_score >= 60:
        return "Reasonably ATS-friendly, with a few gaps worth fixing."
    return "Several ATS-compatibility issues were detected — addressing these should meaningfully help."
