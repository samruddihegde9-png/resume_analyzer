from fastapi import FastAPI
from utils import *

app = FastAPI()


@app.post("/analyze/")
def analyze_resume(
    resume_text: str,
    job_description: str = ""
):

    # =========================
    # RESUME ANALYSIS
    # =========================

    skills = extract_skills(resume_text)
    sections = check_sections(resume_text)
    score = ats_score(skills, sections)
    categorized = categorize_skills(skills)

    section_recs = section_recommendations(
        sections
    )

    result = {
        "skills": skills,
        "categories": categorized,
        "ats_score": score,
        "sections": sections,
        "section_recommendations": section_recs
    }

    # =========================
    # JOB DESCRIPTION ANALYSIS
    # =========================

    if job_description:

        degree_required = extract_degree(
            job_description
        )

        experience_required = extract_experience(
            job_description
        )

        matched, missing, match_score = compare_with_jd(
            skills,
            job_description
        )

        # Semantic matching from Colab API
        semantic_score = semantic_match(
            resume_text,
            job_description
        )

        fit_verdict = candidate_fit(
            match_score
        )

        recommendations = generate_recommendations(
            missing
        )

        result.update({
            "degree_required": degree_required,
            "experience_required": experience_required,
            "matched": matched,
            "missing": missing,
            "match_score": match_score,
            "semantic_score": semantic_score,
            "fit_verdict": fit_verdict,
            "recommendations": recommendations
        })

    return result