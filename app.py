import streamlit as st
import requests
from datetime import datetime
from resume_parser import extract_resume
from utils import *

# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📄",
    layout="wide"
)

st.title("📄 AI Resume Analyzer")
st.write(
    "Upload your resume and compare it against a job description."
)

# =========================
# FILE UPLOAD
# =========================

uploaded_file = st.file_uploader(
    "Upload Resume (PDF)",
    type=["pdf"]
)

# =========================
# JOB DESCRIPTION INPUT
# =========================

job_description = st.text_area(
    "Paste Job Description",
    height=250
)

# =========================
# MAIN LOGIC
# =========================

if uploaded_file is not None:

    # Extract resume text
    resume_text = extract_resume(uploaded_file)

    # Log upload
    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"UPLOAD | File: {uploaded_file.name}"
    )

    # =========================
    # RESUME ANALYSIS
    # =========================

    skills = extract_skills(resume_text)
    sections = check_sections(resume_text)
    score = ats_score(skills, sections)
    categorized = categorize_skills(skills)
    section_recs = section_recommendations(sections)

    # =========================
    # ATS SCORE
    # =========================

    st.subheader("📊 ATS Score")

    st.progress(min(score / 100, 1.0))

    st.metric(
        label="ATS Score",
        value=f"{score}%"
    )

    # =========================
    # SKILLS FOUND
    # =========================

    st.subheader("🛠 Skills Found")

    if skills:
        for category, skill_list in categorized.items():

            if skill_list:
                st.write(f"### {category}")

                cols = st.columns(4)

                for i, skill in enumerate(skill_list):
                    cols[i % 4].success(skill)

    else:
        st.warning("No skills detected.")

    # =========================
    # RESUME SECTION ANALYSIS
    # =========================

    st.subheader("📑 Resume Section Analysis")

    for section, status in sections.items():

        if status:
            st.success(f"✅ {section} Found")
        else:
            st.error(f"❌ {section} Missing")

    # =========================
    # SECTION RECOMMENDATIONS
    # =========================

    st.subheader("📌 Resume Improvement Suggestions")

    if section_recs:
        for rec in section_recs:
            st.warning(rec)
    else:
        st.success("All important sections are present.")

    # =========================
    # ATS FEEDBACK
    # =========================

    st.subheader("💡 Resume Feedback")

    if score < 60:
        st.warning(
            "Add more technical skills, certifications, and projects."
        )

    elif score < 80:
        st.info(
            "Good resume. Add stronger projects and quantified impact."
        )

    else:
        st.success(
            "Strong ATS-friendly resume."
        )

    # =========================
    # JOB DESCRIPTION ANALYSIS
    # =========================

    if job_description:

        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"ANALYSIS_STARTED"
        )

        degree_required = extract_degree(job_description)

        experience_required = extract_experience(
            job_description
        )

        matched, missing, match_score = compare_with_jd(
            skills,
            job_description
        )

        # =========================
        # SEMANTIC API CALL
        # =========================

        semantic_score = 0

        try:
            response = requests.post(
                "https://sam444m-resume-semantic-api.hf.space/semantic-match",
                json={
                    "resume_text": resume_text,
                    "jd_text": job_description
                }
            )

            if response.status_code == 200:
                semantic_score = response.json().get(
                    "semantic_score",
                    0
                )

                print(
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"ANALYSIS_COMPLETED"
                )

            else:
                print(
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"SEMANTIC_API_FAILED"
                )

        except Exception as e:
            print(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"ERROR: {str(e)}"
            )

        fit_verdict = candidate_fit(match_score)

        recommendations = generate_recommendations(
            missing
        )

        # =========================
        # JOB REQUIREMENTS
        # =========================

        st.subheader("📋 Job Requirements")

        col1, col2 = st.columns(2)

        with col1:
            st.info(
                f"🎓 Degree Required: {degree_required}"
            )

        with col2:
            st.info(
                f"💼 Experience Required: {experience_required}"
            )

        # =========================
        # SEMANTIC MATCH
        # =========================

        st.subheader("🧠 Semantic Similarity")

        st.metric(
            label="Semantic Score",
            value=f"{semantic_score}%"
        )

        # =========================
        # KEYWORD MATCH
        # =========================

        st.subheader("🎯 Job Match Analysis")

        st.metric(
            label="Keyword Match Percentage",
            value=f"{match_score}%"
        )

        st.success(
            f"Candidate Fit: {fit_verdict}"
        )

        if matched:
            st.success(
                f"Matching Skills: {', '.join(matched)}"
            )

        if missing:
            st.warning(
                f"Missing Skills: {', '.join(missing)}"
            )

        # =========================
        # RECOMMENDATIONS
        # =========================

        st.subheader("🚀 Skill Recommendations")

        if recommendations:
            for rec in recommendations:
                st.write(f"• {rec}")
        else:
            st.success(
                "Excellent match for this role."
            )