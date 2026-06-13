import streamlit as st
import requests
from resume_parser import extract_resume

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

    # Extract text from resume
    resume_text = extract_resume(uploaded_file)

    try:
        # Send data to FastAPI backend
        response = requests.post(
            "http://127.0.0.1:8000/analyze/",
            params={
                "resume_text": resume_text,
                "job_description": job_description
            }
        )

        data = response.json()

    except:
        st.error("Backend server is not running.")
        st.stop()

    # Fetch results
    skills = data["skills"]
    categorized = data["categories"]
    sections = data["sections"]
    score = data["ats_score"]

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

    section_recs = data["section_recommendations"]

    if section_recs:

        for rec in section_recs:
            st.warning(rec)

    else:
        st.success(
            "All important sections are present."
        )

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

        st.subheader("📋 Job Requirements")

        col1, col2 = st.columns(2)

        with col1:
            st.info(
                f"🎓 Degree Required: {data['degree_required']}"
            )

        with col2:
            st.info(
                f"💼 Experience Required: {data['experience_required']}"
            )

        # =========================
        # SEMANTIC MATCH
        # =========================

        st.subheader("🧠 Semantic Similarity")

        st.metric(
            label="Semantic Score",
            value=f"{data['semantic_score']}%"
        )

        # =========================
        # MATCH ANALYSIS
        # =========================

        st.subheader("🎯 Job Match Analysis")

        st.metric(
            label="Keyword Match Percentage",
            value=f"{data['match_score']}%"
        )

        st.success(
            f"Candidate Fit: {data['fit_verdict']}"
        )

        if data["matched"]:
            st.success(
                f"Matching Skills: {', '.join(data['matched'])}"
            )

        if data["missing"]:
            st.warning(
                f"Missing Skills: {', '.join(data['missing'])}"
            )

        # =========================
        # RECOMMENDATIONS
        # =========================

        st.subheader("🚀 Skill Recommendations")

        if data["recommendations"]:

            for rec in data["recommendations"]:
                st.write(f"• {rec}")

        else:
            st.success(
                "Excellent match for this role."
            )