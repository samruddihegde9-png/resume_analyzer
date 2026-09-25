"""
AI Resume Intelligence & Job Matching System
Streamlit entry point. Deployable as-is on Streamlit Community Cloud.
"""

import io
import csv
import json

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.parser import parse_resume, parse_plain_text
from src.resume_analyzer import analyze_structure
from src.jd_analyzer import analyze_jd
from src.matcher import run_full_match, get_spacy_model
from src.scoring import build_score_breakdown
from src.explainability import overall_explanation, skill_importance, ats_summary_line
from src.recommendations import (
    weak_bullet_improvements, analyze_project_relevance,
    analyze_experience_entries, generate_interview_questions,
)

st.set_page_config(
    page_title="AI Resume Intelligence",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------
# Styling
# ------------------------------------------------------------------

st.markdown("""
<style>
    .kpi-card {
        background: linear-gradient(135deg, #101827 0%, #1f2937 100%);
        border-radius: 14px;
        padding: 18px 20px;
        color: white;
        border: 1px solid #2d3748;
    }
    .kpi-value { font-size: 2.1rem; font-weight: 700; margin: 0; }
    .kpi-label { font-size: 0.85rem; opacity: 0.75; margin: 0; letter-spacing: 0.04em; text-transform: uppercase; }
    .section-header {
        font-size: 1.3rem; font-weight: 700; margin-top: 0.4rem; margin-bottom: 0.6rem;
        border-left: 4px solid #6366f1; padding-left: 10px;
    }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Cached resources / helpers
# ------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def load_semantic_model():
    """Warms the spaCy vector model once per app instance."""
    return get_spacy_model()


@st.cache_data(show_spinner=False)
def cached_parse_resume(file_bytes: bytes, filename: str):
    return parse_resume(file_bytes, filename)


@st.cache_data(show_spinner=False)
def cached_parse_jd(text: str):
    return parse_plain_text(text)


@st.cache_data(show_spinner=False)
def cached_jd_analysis(text: str):
    return analyze_jd(text)


def kpi_card(col, label, value, suffix="%"):
    col.markdown(f"""
        <div class="kpi-card">
            <p class="kpi-label">{label}</p>
            <p class="kpi-value">{value}{suffix}</p>
        </div>
    """, unsafe_allow_html=True)


def donut_chart(matched, partial, missing, title):
    labels = ["Matched", "Partial", "Missing"]
    values = [matched, partial, missing]
    colors = ["#22c55e", "#eab308", "#ef4444"]
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors), textinfo="label+percent",
    )])
    fig.update_layout(title=title, showlegend=True, height=340, margin=dict(t=50, b=10, l=10, r=10))
    return fig


def bar_chart(categories: dict, title: str):
    if not categories:
        return None
    fig = go.Figure(data=[go.Bar(
        x=list(categories.values()), y=list(categories.keys()), orientation="h",
        marker=dict(color=list(categories.values()), colorscale="Blues"),
    )])
    fig.update_layout(title=title, height=max(300, 30 * len(categories)), margin=dict(t=50, b=10, l=10, r=10),
                       xaxis_title="Coverage %")
    return fig


def to_csv_bytes(rows, headers) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for r in rows:
        writer.writerow(r)
    return buf.getvalue().encode("utf-8")


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 🧭 AI Resume Intelligence")
    st.caption("Resume ↔ Job Description Analysis")
    st.divider()

    st.markdown("### 📄 Resume")
    resume_file = st.file_uploader("Upload resume", type=["pdf", "docx", "txt"], key="resume_upload")

    st.markdown("### 📋 Job Description")
    jd_input_mode = st.radio("Input method", ["Paste text", "Upload file"], horizontal=True)
    jd_text_input = ""
    jd_file = None
    if jd_input_mode == "Paste text":
        jd_text_input = st.text_area("Paste the job description", height=220)
    else:
        jd_file = st.file_uploader("Upload JD", type=["pdf", "docx", "txt"], key="jd_upload")

    st.divider()
    st.markdown("### ⚙️ Analysis Settings")
    show_semantic_details = st.checkbox("Show matching methodology details", value=False)
    max_interview_qs = st.slider("Max interview questions per category", 2, 8, 5)

    run_analysis = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    st.divider()
    st.caption(
        "This tool provides decision support only — it does not make hiring "
        "decisions and does not infer or use protected characteristics."
    )

# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------

st.markdown("# AI Resume Intelligence")
st.markdown("##### AI-powered resume analysis, semantic job matching, skill-gap detection and career intelligence")
st.write("")

if "results" not in st.session_state:
    st.session_state.results = None

# ------------------------------------------------------------------
# Run pipeline
# ------------------------------------------------------------------

if run_analysis:
    if resume_file is None:
        st.error("Please upload a resume to continue.")
    elif jd_input_mode == "Paste text" and not jd_text_input.strip():
        st.error("Please paste a job description, or switch to file upload.")
    elif jd_input_mode == "Upload file" and jd_file is None:
        st.error("Please upload a job description file.")
    else:
        with st.spinner("Parsing documents..."):
            resume_bytes = resume_file.read()
            parsed_resume = cached_parse_resume(resume_bytes, resume_file.name)

            if jd_input_mode == "Paste text":
                jd_text = jd_text_input
            else:
                jd_bytes = jd_file.read()
                parsed_jd_doc = cached_parse_resume(jd_bytes, jd_file.name)
                jd_text = parsed_jd_doc.raw_text

            parsed_jd = cached_parse_jd(jd_text)

        if len(parsed_resume.raw_text.split()) < 15:
            st.error(
                "Very little text could be extracted from the resume file. "
                "It may be a scanned image or an unusual format — try a text-based PDF or DOCX."
            )
        elif len(jd_text.split()) < 15:
            st.error("The job description looks too short to analyze meaningfully. Please provide more detail.")
        else:
            with st.spinner("Running structure analysis..."):
                structure = analyze_structure(parsed_resume)

            with st.spinner("Analyzing job description..."):
                jd_analysis = cached_jd_analysis(jd_text)

            with st.spinner("Running multi-layer matching..."):
                load_semantic_model()
                experience_text = parsed_resume.sections.get("Experience", "") + "\n" + parsed_resume.sections.get("Internships", "")
                match = run_full_match(parsed_resume.cleaned_text, experience_text, jd_analysis and jd_text, jd_analysis)

            with st.spinner("Scoring..."):
                has_contact = bool(parsed_resume.contact.email or parsed_resume.contact.phone)
                scores = build_score_breakdown(match, structure, has_contact)

            with st.spinner("Generating recommendations..."):
                bullet_improvements = weak_bullet_improvements(structure.bullets)
                projects_text = parsed_resume.sections.get("Projects", "")
                project_relevance = analyze_project_relevance(projects_text, jd_analysis.all_skills)
                experience_comparison = analyze_experience_entries(
                    experience_text, jd_analysis.all_skills, jd_analysis.responsibilities
                )
                interview_qs = generate_interview_questions(
                    parsed_resume.raw_text,
                    sorted(match.skill_match.matched),
                    sorted(match.skill_match.missing),
                    projects_text,
                    jd_analysis.job_title,
                )
                interview_qs = {k: v[:max_interview_qs] for k, v in interview_qs.items()}

            st.session_state.results = dict(
                parsed_resume=parsed_resume, jd_analysis=jd_analysis, jd_text=jd_text,
                structure=structure, match=match, scores=scores,
                bullet_improvements=bullet_improvements, project_relevance=project_relevance,
                experience_comparison=experience_comparison, interview_qs=interview_qs,
            )
            st.success("Analysis complete.")

# ------------------------------------------------------------------
# Results display
# ------------------------------------------------------------------

results = st.session_state.results

if results is None:
    st.info("👈 Upload a resume and provide a job description, then click **Run Analysis**.")
    st.stop()

parsed_resume = results["parsed_resume"]
jd_analysis = results["jd_analysis"]
structure = results["structure"]
match = results["match"]
scores = results["scores"]

for w in parsed_resume.warnings:
    st.warning(w)

# KPI row
k1, k2, k3, k4 = st.columns(4)
kpi_card(k1, "Overall Match", scores.overall_match)
kpi_card(k2, "Estimated ATS Compatibility", scores.ats_score)
kpi_card(k3, "Skill Match", scores.component_scores.get("skill_match", 0))
kpi_card(k4, "Experience Match", scores.component_scores.get("experience_match", 0))

st.write("")

tabs = st.tabs([
    "📊 Overview", "🎯 Match Analysis", "🧩 Skill Gap",
    "🖥️ ATS Analysis", "✍️ Resume Improvements", "🎤 Interview Prep", "⬇️ Export",
])

# --- Overview ---
with tabs[0]:
    st.markdown('<p class="section-header">Overall Match Score</p>', unsafe_allow_html=True)
    st.progress(min(scores.overall_match / 100, 1.0))
    st.write(overall_explanation(scores, match, jd_analysis))

    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(
            bar_chart(scores.component_scores, "Score components (weighted contributors)"),
            use_container_width=True,
        )
    with col2:
        st.markdown("**Job title detected:** " + jd_analysis.job_title)
        st.markdown(f"**Experience required:** {jd_analysis.experience_text}")
        st.markdown(f"**Education required:** {', '.join(jd_analysis.education_requirements) or 'Not specified'}")
        if jd_analysis.domain_hints:
            st.markdown(f"**Domain hints:** {', '.join(jd_analysis.domain_hints)}")

    if show_semantic_details:
        st.markdown('<p class="section-header">Matching methodology</p>', unsafe_allow_html=True)
        st.json({
            "exact_keyword_score": match.exact_keyword_score,
            "normalized_keyword_score (skill match)": match.normalized_keyword_score,
            "taxonomy_category_score": match.taxonomy_category_score,
            "tfidf_score": match.tfidf_score,
            "semantic_score": match.semantic_score,
            "semantic_method": match.semantic_method,
            "experience_score": match.experience_score,
            "education_score": match.education_score,
            "responsibility_score": match.responsibility_score,
            "resume_years_detected": match.resume_years,
            "required_years": match.required_years,
            "weights_used": scores.component_weights,
        })

# --- Match Analysis ---
with tabs[1]:
    st.markdown('<p class="section-header">Requirement-by-requirement analysis</p>', unsafe_allow_html=True)
    rows = []
    for req in jd_analysis.requirements[:60]:
        if not req.skills_mentioned:
            continue
        status = []
        for s in req.skills_mentioned:
            if s in match.skill_match.matched:
                status.append("Matched")
            elif s in match.skill_match.partial:
                status.append("Partial")
            else:
                status.append("Missing")
        rows.append({
            "Requirement": req.text[:120],
            "Category": req.category.replace("_", " ").title(),
            "Skills mentioned": ", ".join(sorted(req.skills_mentioned)),
            "Status": ", ".join(sorted(set(status))),
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No specific skill-bearing requirement lines were detected in the job description.")

    st.markdown('<p class="section-header">Experience entries vs. job description</p>', unsafe_allow_html=True)
    if results["experience_comparison"]:
        for entry in results["experience_comparison"]:
            with st.expander(entry.entry_title or "Experience entry"):
                st.write(f"**Matching skills:** {', '.join(entry.matching_skills) or 'None detected'}")
                st.write(f"**Missing requirements:** {', '.join(entry.missing_requirements) or 'None'}")
    else:
        st.info("No distinct experience entries were detected to compare individually.")

# --- Skill Gap ---
with tabs[2]:
    sm = match.skill_match
    st.markdown('<p class="section-header">Matched vs. partial vs. missing skills</p>', unsafe_allow_html=True)
    st.plotly_chart(
        donut_chart(len(sm.matched), len(sm.partial), len(sm.missing), "Skill coverage"),
        use_container_width=True,
    )

    category_filter = st.multiselect(
        "Filter by category",
        options=sorted(sm.category_coverage.keys()) if sm.category_coverage else [],
    )

    from src.keyword_engine import canonical_category

    def _filtered(skills):
        if not category_filter:
            return sorted(skills)
        return sorted(s for s in skills if canonical_category(s) in category_filter)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### ✅ Matched")
        for s in _filtered(sm.matched):
            st.success(s)
    with c2:
        st.markdown("#### 🟡 Partial")
        for s in _filtered(sm.partial):
            st.warning(f"{s} — related skill detected, not this exact one")
    with c3:
        st.markdown("#### ❌ Missing")
        for s in _filtered(sm.missing):
            st.error(f"{s} — {skill_importance(s, jd_analysis)}")

# --- ATS Analysis ---
with tabs[3]:
    st.markdown('<p class="section-header">Estimated ATS Compatibility</p>', unsafe_allow_html=True)
    st.progress(min(scores.ats_score / 100, 1.0))
    st.write(ats_summary_line(scores))
    st.caption("This is an estimate based on resume structure and content — not a score from any specific ATS vendor.")

    st.plotly_chart(bar_chart(scores.ats_components, "ATS component breakdown"), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Strengths")
        for s in scores.ats_strengths:
            st.success(f"✓ {s}")
    with c2:
        st.markdown("#### Warnings")
        for w in scores.ats_warnings:
            st.warning(f"⚠ {w}")

    st.markdown('<p class="section-header">Resume structure detail</p>', unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Detected sections", len(structure.detected_sections))
    d2.metric("Bullet count", structure.bullet_count)
    d3.metric("Avg. bullet length", f"{structure.avg_bullet_length} words")
    d4.metric("Content density", structure.content_density.title())
    if structure.repeated_phrases:
        st.write("**Frequently repeated phrases:** " + ", ".join(structure.repeated_phrases[:10]))

# --- Resume Improvements ---
with tabs[4]:
    st.markdown('<p class="section-header">Bullet point improvements</p>', unsafe_allow_html=True)
    st.caption("Suggestions only rework wording already in your resume — nothing is invented.")
    if results["bullet_improvements"]:
        for imp in results["bullet_improvements"]:
            with st.container(border=True):
                st.markdown(f"**CURRENT:** {imp.current}")
                st.markdown(f"**IMPROVED:** {imp.improved}")
                st.caption(f"WHY: {imp.why}")
    else:
        st.success("No clearly weak bullets were detected — nice work.")

    st.markdown('<p class="section-header">Project relevance</p>', unsafe_allow_html=True)
    if results["project_relevance"]:
        for proj in results["project_relevance"]:
            badge = {"KEEP": "🟢", "REWRITE": "🟡", "REMOVE": "🔴"}.get(proj.recommendation, "⚪")
            with st.expander(f"{badge} {proj.title}  —  {proj.recommendation}  ({proj.relevance_score}% relevant)"):
                st.write(f"**Matching skills:** {', '.join(proj.matching_skills) or 'None detected'}")
                st.write(f"**Missing technologies for this JD:** {', '.join(proj.missing_technologies) or 'None'}")
                st.write(f"**Reasoning:** {proj.reasoning}")
    else:
        st.info("No distinct project entries were detected in a 'Projects' section.")

# --- Interview Prep ---
with tabs[5]:
    st.markdown('<p class="section-header">Interview preparation questions</p>', unsafe_allow_html=True)
    st.caption("Generated only from your resume, the job description, and the detected skill gaps.")
    categories = list(results["interview_qs"].keys())
    if categories:
        selected = st.multiselect("Categories", categories, default=categories)
        for cat in selected:
            st.markdown(f"#### {cat}")
            for q in results["interview_qs"][cat]:
                with st.expander(q):
                    st.write(
                        "Structure your answer with context, the specific action you took, "
                        "and the outcome or result (situation → task → action → result)."
                    )
    else:
        st.info("Not enough detail was detected to generate interview questions.")

# --- Export ---
with tabs[6]:
    st.markdown('<p class="section-header">Download results</p>', unsafe_allow_html=True)

    matched_csv = to_csv_bytes([[s] for s in sorted(match.skill_match.matched)], ["Matched Skill"])
    missing_csv = to_csv_bytes([[s] for s in sorted(match.skill_match.missing)], ["Missing Skill"])
    improvements_csv = to_csv_bytes(
        [[i.current, i.improved, i.why] for i in results["bullet_improvements"]],
        ["Current", "Improved", "Why"],
    )
    interview_rows = [[cat, q] for cat, qs in results["interview_qs"].items() for q in qs]
    interview_csv = to_csv_bytes(interview_rows, ["Category", "Question"])

    summary = {
        "overall_match": scores.overall_match,
        "ats_score": scores.ats_score,
        "component_scores": scores.component_scores,
        "matched_skills": sorted(match.skill_match.matched),
        "partial_skills": sorted(match.skill_match.partial),
        "missing_skills": sorted(match.skill_match.missing),
        "job_title": jd_analysis.job_title,
    }
    report_text = (
        f"AI RESUME INTELLIGENCE REPORT\n{'=' * 40}\n\n"
        f"Job Title: {jd_analysis.job_title}\n"
        f"Overall Match Score: {scores.overall_match}/100\n"
        f"Estimated ATS Compatibility: {scores.ats_score}/100\n\n"
        f"COMPONENT SCORES\n" + "\n".join(f"  {k}: {v}%" for k, v in scores.component_scores.items()) +
        f"\n\nMATCHED SKILLS\n  " + ", ".join(sorted(match.skill_match.matched)) +
        f"\n\nMISSING SKILLS\n  " + ", ".join(sorted(match.skill_match.missing)) +
        f"\n\nSUMMARY\n{overall_explanation(scores, match, jd_analysis)}\n"
    )

    c1, c2, c3 = st.columns(3)
    c1.download_button("📄 Analysis report (.txt)", report_text, file_name="resume_analysis_report.txt")
    c1.download_button("🧾 Full summary (.json)", json.dumps(summary, indent=2), file_name="resume_analysis_summary.json")
    c2.download_button("✅ Matched skills (.csv)", matched_csv, file_name="matched_skills.csv")
    c2.download_button("❌ Missing skills (.csv)", missing_csv, file_name="missing_skills.csv")
    c3.download_button("✍️ Improvements (.csv)", improvements_csv, file_name="bullet_improvements.csv")
    c3.download_button("🎤 Interview questions (.csv)", interview_csv, file_name="interview_questions.csv")
