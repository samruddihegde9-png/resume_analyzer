# AI Resume Intelligence & Job Matching System

*AI-powered resume analysis, semantic job matching, skill-gap detection and career intelligence.*

## Overview

AI Resume Intelligence is a Streamlit application that analyzes a resume against a specific job description and produces a transparent, multi-dimensional match report: an overall match score, an estimated ATS compatibility score, skill-gap analysis, resume-improvement suggestions, and tailored interview-prep questions.

It began as a small Flask API that computed a single cosine-similarity score between a resume and a job description using a Hugging Face sentence-transformer. This version replaces that with a modular, multi-layer analysis pipeline, drops the Hugging Face dependency entirely, and is built to be deployed on **Streamlit Community Cloud**.

## Problem

Generic keyword-matching tools give a single number with no explanation, and candidates are left guessing why their resume scored the way it did. This project instead aims to show *why* a resume matches or doesn't — which skills are present, which are missing, how experience and education line up, and what specifically could be rewritten to improve the resume, without inventing facts the candidate never wrote.

## Features

- Resume parsing for **PDF, DOCX, and TXT** with a hybrid PyMuPDF/pdfplumber extraction fallback
- Contact info extraction (name, email, phone, LinkedIn, GitHub, portfolio link)
- Resume structure analysis: detected/missing sections, bullet quality, action-verb and metric coverage, repeated phrases, formatting red flags
- Job description analysis: title, must-have vs. nice-to-have requirements, responsibilities, required experience/education, domain hints
- An 8-layer, weighted, and fully documented matching engine (see below)
- A skill normalization engine mapping dozens of aliases ("ML", "sklearn", "Postgres"...) to canonical skill names across 14 categories
- Skill-gap analysis: **Matched / Partial / Missing**, each with an importance explanation
- Estimated ATS compatibility score with strengths/warnings
- Resume bullet-improvement suggestions (wording only — no invented facts)
- Project relevance analysis (Keep / Rewrite / Remove, with reasoning)
- Experience-entry vs. job-description comparison
- Interview question generation (Technical, Project, Behavioural, Role-specific, Resume-based)
- CSV / JSON / TXT export of every major result
- No data is persisted — files are processed in memory for the session only

## Architecture

```
resume-intelligence/
│
├── app.py                     # Streamlit UI and orchestration
│
├── src/
│   ├── parser.py               # PDF/DOCX/TXT extraction, contact info, section splitting
│   ├── resume_analyzer.py      # Resume structure & bullet-quality analysis
│   ├── jd_analyzer.py          # Job description requirement extraction & classification
│   ├── matcher.py              # 8-layer matching engine
│   ├── scoring.py              # Weighted scoring engine (Overall Match + ATS score)
│   ├── recommendations.py      # Bullet rewrites, project relevance, interview questions
│   ├── keyword_engine.py       # Skill alias/taxonomy dictionary + normalization
│   ├── explainability.py       # Plain-English explanations grounded in detected data
│   └── utils.py                 # Shared text-cleaning / tokenizing helpers
│
├── assets/
├── sample_data/
├── outputs/
├── requirements.txt
├── README.md
├── .gitignore
└── LICENSE
```

## NLP / Matching Approach

**No Hugging Face models, packages, or hosted infrastructure are used anywhere in this project.**

| Layer | Technique | Library |
|---|---|---|
| 1. Exact keyword matching | Raw token overlap | Python `re` |
| 2. Normalized keyword matching | Skill alias/taxonomy lookup | Custom (`keyword_engine.py`) |
| 3. Skill taxonomy matching | Category-level coverage | Custom |
| 4. TF-IDF similarity | Classic bag-of-words cosine similarity | scikit-learn |
| 5. Semantic similarity | Word-vector document similarity | **spaCy** (`en_core_web_md`, installed from spaCy's own GitHub-hosted wheel — not Hugging Face) |
| 6. Experience alignment | Regex-based year-range extraction vs. JD requirement | Custom |
| 7. Education alignment | Degree-level comparison | Custom |
| 8. Responsibility alignment | TF-IDF similarity of experience text vs. JD duties | scikit-learn |

If the spaCy vector model fails to load in a given environment (e.g. a minimal deployment where the model wheel didn't install), semantic similarity **automatically falls back to the TF-IDF score** rather than failing or fabricating a number. The active method is always reported in the UI's "matching methodology" panel.

## Scoring Methodology

```
Overall Match Score =
      35% Skill Match           (normalized/taxonomy skill coverage)
    + 20% Experience Match      (years required vs. years detected)
    + 15% Responsibility Match  (experience text vs. JD duties, TF-IDF)
    + 10% Education Match       (degree-level alignment)
    + 10% Keyword Coverage      (exact keyword overlap)
    + 10% Semantic Similarity   (spaCy vectors, or TF-IDF fallback)
```

These weights favor concrete, verifiable overlap (skills, experience, responsibilities) over generic text similarity, since two resumes can read similarly but differ hugely in actual fit. The exact formula and every component score are shown in the app's Overview tab — nothing is hidden.

## ATS Analysis

A separate **Estimated ATS Compatibility** score (0–100) evaluates resume structure independent of any single job description: presence of standard sections, keyword coverage, action-verb usage, quantified outcomes, formatting red flags (heavy tables, unusual symbols, poor text extraction), and detectable contact information. It is explicitly labeled *"estimated"* — this project does not claim to replicate any specific commercial ATS vendor's algorithm.

## Skill Gap Analysis

Every job-description skill is bucketed as:

- **Matched** — the exact canonical skill (or a recognised alias of it) was found in the resume
- **Partial** — a different skill from the *same taxonomy category* was found, but not the specific one requested (the app never claims a skill exists that wasn't actually detected)
- **Missing** — no related skill was found, with an explanation of how central that skill is to the job description

## Resume Improvement Engine

Weak bullets (missing an action verb and/or a quantified outcome) are flagged and shown as **Current / Improved / Why**. Improvements only rework existing wording — they suggest a stronger opening verb or prompt the user to add a real metric; they never invent tools, technologies, or outcomes that weren't in the original bullet.

## Interview Preparation

Questions are generated only from what was actually detected: matched skills, missing skills, individual project entries, and literal resume lines — never from a generic question bank unrelated to the uploaded documents.

## Tech Stack

Python · Streamlit · scikit-learn · spaCy · PyMuPDF · pdfplumber · python-docx · Plotly · Pandas

## Installation

```bash
git clone <your-repo-url>
cd resume-intelligence
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

> The `en_core_web_md` spaCy model installs automatically from `requirements.txt` (a direct wheel URL from spaCy's own GitHub releases). If it's ever unavailable, the app still runs — semantic similarity falls back to TF-IDF automatically.

## Streamlit Deployment

1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and click **New app**.
3. Select the repository, branch, and set the main file path to `app.py`.
4. If you later add an optional external API key (e.g. for an LLM-based enhancement), add it under **App settings → Secrets** as:
   ```toml
   OPENAI_API_KEY = "your-key-here"
   ```
   and read it in code via `st.secrets["OPENAI_API_KEY"]` — never hard-code keys. The current version does not require any API key to run.
5. Deploy. First boot may take a minute while dependencies (including the spaCy model wheel) install.

## Screenshots

*(Add screenshots of the Overview, Skill Gap, and ATS Analysis tabs here after your first deployment.)*

## Limitations

- Experience-year detection relies on date ranges written in the resume (e.g. "2021–2023") and will under-count experience described only in prose.
- Section and heading detection uses pattern matching, so highly unconventional resume layouts may be partially mis-segmented.
- The skill taxonomy, while broad, is a curated dictionary — very niche or brand-new tools may not be recognized until added to `keyword_engine.py`.
- "Estimated ATS Compatibility" is a heuristic proxy, not a certified score from any specific ATS product.
- Bullet-improvement suggestions intentionally avoid adding specifics not present in the original resume, so some suggestions are prompts to add detail rather than fully rewritten sentences.

## Future Improvements

- Optional LLM-backed rewriting (via a user-supplied API key in Streamlit secrets) for richer bullet suggestions, with the deterministic engine kept as the default/no-key fallback.
- Resume-to-resume benchmarking across multiple job descriptions at once.
- A downloadable, fully designed PDF report (current export is CSV/JSON/TXT).
- Configurable scoring weights per industry.

## Ethical Considerations

This tool provides **decision support, not hiring decisions**. It is intended to help a candidate understand and improve how their resume reads against a specific job description.

- It does not infer, use, or report on protected characteristics (age, gender, race, religion, disability, national origin, or similar).
- It does not rank or compare candidates against one another.
- All scores are heuristics grounded in text actually present in the uploaded documents — the system does not fabricate skills, experience, or qualifications.
- Uploaded resumes are processed in memory for the session and are not stored permanently.
