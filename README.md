# 📄 AI Resume Analyzer

An AI-powered Resume Analyzer that evaluates resumes for ATS compatibility, extracts skills, compares them against job descriptions, and calculates semantic similarity using transformer embeddings.

## 🚀 Features

### ✅ ATS Score Analysis
- Calculates ATS score based on:
  - Skills detected
  - Resume sections present
- Provides improvement suggestions

### ✅ Skill Extraction
Detects technical skills like:
- Python
- SQL
- Machine Learning
- NLP
- TensorFlow
- AWS
- Docker
- FastAPI
- and more

### ✅ Skill Categorization
Groups skills into:
- Programming
- Machine Learning
- Data Analysis
- Cloud
- DevOps
- AI

### ✅ Resume Section Detection
Checks for:
- Education
- Projects
- Skills
- Experience
- Certifications

### ✅ Job Description Matching
Compares resume against JD and shows:
- Match percentage
- Missing skills
- Candidate fit

### ✅ Semantic Similarity (AI-powered)
Uses Sentence Transformers to compare:
- Resume meaning
- Job description meaning

Provides deeper matching beyond keywords.

---

## 🛠 Tech Stack

### Frontend
- Streamlit

### Backend
- FastAPI

### AI / NLP
- Sentence Transformers
- Scikit-learn
- Hugging Face Spaces

### Utilities
- pdfplumber
- requests

---

## 📂 Project Structure

```bash
resume-analyzer/
│── app.py              # Streamlit frontend
│── api.py              # FastAPI backend
│── utils.py            # Core logic
│── resume_parser.py    # PDF text extraction
│── requirements.txt
│── README.md
│── .gitignore
```

---

## ⚙ Installation

Clone repository:

```bash
git clone https://github.com/yourusername/resume-analyzer.git
cd resume-analyzer
```

Create virtual environment:

```bash
python -m venv venv
```

Activate:

Windows:

```bash
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## ▶ Run Project

Start FastAPI backend:

```bash
uvicorn api:app --reload
```

Start Streamlit frontend:

```bash
streamlit run app.py
```

---

## 🌐 Semantic API

Semantic similarity is hosted separately on Hugging Face:

```text
https://sam444m-resume-semantic-api.hf.space/semantic-match
```

---

## 📊 Example Output

- ATS Score: 71.3%
- Semantic Similarity: 36.52%
- Keyword Match: 66.67%
- Missing Skills Detection
- Resume Improvement Suggestions

---

## Future Improvements

- Weighted ATS scoring
- Resume PDF report generation
- Better skill database
- Resume ranking system
- Multi-job comparison
- Recruiter dashboard

---

## Author

Built by **Samruddi**