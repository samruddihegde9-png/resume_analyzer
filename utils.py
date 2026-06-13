import re
import requests

# =========================
# COLAB SEMANTIC API URL
# =========================
import requests

SEMANTIC_API_URL = "https://sam444m-resume-semantic-api.hf.space/semantic-match"


def semantic_match(resume_text, jd_text):
    response = requests.post(
        SEMANTIC_API_URL,
        json={
            "resume_text": resume_text,
            "jd_text": jd_text
        }
    )

    return response.json()["semantic_score"]

# =========================
# SKILL DATABASE
# =========================

skills_db = [
    "python", "java", "sql",
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "scikit-learn", "xgboost",
    "pandas", "numpy",
    "power bi", "tableau",
    "streamlit", "flask", "fastapi",
    "docker", "kubernetes",
    "git", "github",
    "aws", "aws glue", "athena", "redshift",
    "gcp", "azure",
    "mongodb", "mysql", "postgresql",
    "etl", "spark", "hadoop", "airflow",
    "databricks", "snowflake",
    "jenkins", "linux", "ci/cd",
    "rest api", "postman",
    "generative ai", "rag", "llm", "opencv"
]


# =========================
# SKILL CATEGORIES
# =========================

skill_categories = {
    "Programming": ["python", "java", "sql"],

    "Machine Learning": [
        "machine learning",
        "deep learning",
        "nlp",
        "computer vision",
        "tensorflow",
        "pytorch",
        "xgboost",
        "opencv"
    ],

    "Data Analysis": [
        "pandas",
        "numpy",
        "power bi",
        "tableau"
    ],

    "Backend": [
        "flask",
        "fastapi",
        "rest api"
    ],

    "Cloud": [
        "aws",
        "gcp",
        "azure",
        "redshift",
        "aws glue"
    ],

    "Data Engineering": [
        "etl",
        "spark",
        "hadoop",
        "airflow",
        "databricks",
        "snowflake"
    ],

    "DevOps": [
        "docker",
        "kubernetes",
        "jenkins",
        "linux",
        "ci/cd"
    ],

    "AI": [
        "generative ai",
        "rag",
        "llm"
    ]
}


# =========================
# SEMANTIC MATCHING (COLAB API)
# =========================

def semantic_match(resume_text, jd_text):

    try:
        response = requests.post(
            SEMANTIC_API_URL,
            json={
                "resume_text": resume_text,
                "jd_text": jd_text
            }
        )

        if response.status_code == 200:
            return response.json()["semantic_score"]

        return 0

    except:
        return 0


# =========================
# SKILL EXTRACTION
# =========================

def extract_skills(resume_text):

    resume_text = resume_text.lower()
    found_skills = []

    for skill in skills_db:
        pattern = r'\b' + re.escape(skill) + r'\b'

        if re.search(pattern, resume_text):
            found_skills.append(skill)

    return found_skills


# =========================
# SKILL CATEGORIZATION
# =========================

def categorize_skills(found_skills):

    categorized = {}

    for category, skills in skill_categories.items():
        categorized[category] = []

        for skill in skills:
            if skill in found_skills:
                categorized[category].append(skill)

    return categorized


# =========================
# ATS SCORE
# =========================

def ats_score(skills, sections):

    skill_score = (len(skills) / len(skills_db)) * 60
    completed_sections = sum(sections.values())
    section_score = (completed_sections / 5) * 40

    total = skill_score + section_score

    return round(min(total, 100), 2)


# =========================
# JOB DESCRIPTION MATCHING
# =========================

def compare_with_jd(resume_skills, jd_text):

    jd_text = jd_text.lower()
    jd_skills = []

    for skill in skills_db:
        pattern = r'\b' + re.escape(skill) + r'\b'

        if re.search(pattern, jd_text):
            jd_skills.append(skill)

    matched = list(set(resume_skills) & set(jd_skills))
    missing = list(set(jd_skills) - set(resume_skills))

    if jd_skills:
        match_score = round(
            (len(matched) / len(jd_skills)) * 100,
            2
        )
    else:
        match_score = 0

    return matched, missing, match_score


# =========================
# DEGREE EXTRACTION
# =========================

def extract_degree(jd_text):

    degrees = [
        "bachelor", "master",
        "b.e", "b.tech",
        "m.tech",
        "computer science",
        "information technology",
        "data science"
    ]

    jd_text = jd_text.lower()
    found = [d for d in degrees if d in jd_text]

    return ", ".join(found) if found else "Not Specified"


# =========================
# EXPERIENCE EXTRACTION
# =========================

def extract_experience(jd_text):

    patterns = [
        r'\d+\+?\s*years?',
        r'\d+\s*-\s*\d+\s*years?',
        r'\d+\+?\s*years?\s*of\s*experience'
    ]

    jd_text = jd_text.lower()

    for pattern in patterns:
        match = re.search(pattern, jd_text)

        if match:
            return match.group()

    return "Not Specified"


# =========================
# SECTION CHECKER
# =========================

def check_sections(resume_text):

    text = resume_text.lower()

    return {
        "Education": "education" in text,
        "Projects": "project" in text,
        "Skills": "skill" in text,
        "Experience": "experience" in text,
        "Certifications": "certification" in text
    }


# =========================
# SKILL RECOMMENDATIONS
# =========================

def generate_recommendations(missing_skills):

    return [
        f"Consider learning or adding {skill}"
        for skill in missing_skills
    ]


# =========================
# SECTION RECOMMENDATIONS
# =========================

def section_recommendations(sections):

    recommendations = []

    for section, present in sections.items():
        if not present:
            recommendations.append(
                f"Add {section} section to improve ATS score"
            )

    return recommendations


# =========================
# CANDIDATE FIT
# =========================

def candidate_fit(match_score):

    if match_score >= 80:
        return "Excellent Match"

    elif match_score >= 60:
        return "Good Match"

    elif match_score >= 40:
        return "Moderate Match"

    return "Low Match"