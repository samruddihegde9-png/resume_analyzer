"""
Skill normalization engine.

Maps many surface forms ("ML", "machine-learning", "Machine Learning")
to one canonical skill name, and groups canonical skills into categories.
This dictionary is intentionally a plain, maintainable Python structure —
add new aliases/categories here rather than touching matching logic.
"""

import re
from typing import Dict, List, Set, Tuple

# canonical_skill -> list of alias surface forms (lowercase, no punctuation needed;
# matching is done on normalized tokens so "scikit-learn" and "scikit learn" both work)
SKILL_ALIASES: Dict[str, List[str]] = {
    # Programming
    "Python": ["python", "python3", "py"],
    "Java": ["java"],
    "JavaScript": ["javascript", "js", "ecmascript"],
    "TypeScript": ["typescript", "ts"],
    "C++": ["c++", "cpp"],
    "C#": ["c#", "csharp"],
    "C": ["c programming"],
    "Go": ["golang", "go lang"],
    "R": ["r programming", "r language"],
    "SQL": ["sql", "structured query language", "t-sql", "pl/sql"],
    "Scala": ["scala"],
    "Bash/Shell": ["bash", "shell scripting", "shell script"],

    # Data
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Data Analysis": ["data analysis", "data analytics"],
    "Data Visualization": ["data visualization", "data viz"],
    "Excel": ["excel", "ms excel", "microsoft excel"],
    "Power BI": ["power bi", "powerbi"],
    "Tableau": ["tableau"],
    "ETL": ["etl", "extract transform load", "data pipelines", "data pipeline"],
    "Apache Spark": ["spark", "apache spark", "pyspark"],
    "Hadoop": ["hadoop"],
    "Apache Airflow": ["airflow", "apache airflow"],
    "Databricks": ["databricks"],
    "Snowflake": ["snowflake"],

    # Machine Learning
    "Machine Learning": ["machine learning", "ml", "machine-learning"],
    "Deep Learning": ["deep learning", "dl"],
    "Scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
    "TensorFlow": ["tensorflow", "tf"],
    "PyTorch": ["pytorch", "torch"],
    "XGBoost": ["xgboost", "xg boost"],
    "LightGBM": ["lightgbm", "light gbm"],
    "Keras": ["keras"],
    "Feature Engineering": ["feature engineering"],
    "Model Deployment": ["model deployment", "mlops", "ml ops"],
    "Time Series Analysis": ["time series", "time series analysis", "forecasting"],

    # NLP
    "Natural Language Processing": ["nlp", "natural language processing"],
    "spaCy": ["spacy"],
    "NLTK": ["nltk"],
    "Text Classification": ["text classification"],
    "Named Entity Recognition": ["named entity recognition", "ner"],
    "Large Language Models": ["llm", "llms", "large language model", "large language models", "genai", "generative ai"],
    "Retrieval Augmented Generation": ["rag", "retrieval augmented generation", "retrieval-augmented generation"],
    "Prompt Engineering": ["prompt engineering"],

    # Computer Vision
    "Computer Vision": ["computer vision", "cv"],
    "OpenCV": ["opencv", "open cv"],
    "Image Processing": ["image processing"],

    # Cloud
    "AWS": ["aws", "amazon web services"],
    "AWS Glue": ["aws glue"],
    "AWS Redshift": ["redshift", "aws redshift"],
    "AWS Athena": ["athena", "aws athena"],
    "GCP": ["gcp", "google cloud", "google cloud platform"],
    "Microsoft Azure": ["azure", "microsoft azure"],

    # Databases
    "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
    "SQLite": ["sqlite"],
    "NoSQL": ["nosql"],

    # BI
    "Business Intelligence": ["business intelligence", "bi"],

    # DevOps
    "Docker": ["docker", "containerization"],
    "Kubernetes": ["kubernetes", "k8s"],
    "CI/CD": ["ci/cd", "cicd", "continuous integration", "continuous deployment"],
    "Git": ["git", "version control"],
    "GitHub": ["github"],
    "GitLab": ["gitlab"],
    "Jenkins": ["jenkins"],
    "Linux": ["linux", "unix"],
    "Terraform": ["terraform", "infrastructure as code", "iac"],

    # Web
    "Flask": ["flask"],
    "FastAPI": ["fastapi"],
    "Django": ["django"],
    "Streamlit": ["streamlit"],
    "REST APIs": ["rest api", "restful api", "rest apis", "api development"],
    "React": ["react", "react.js", "reactjs"],
    "Node.js": ["node.js", "nodejs", "node"],
    "HTML/CSS": ["html", "css", "html/css"],

    # AI/LLM tooling
    "LangChain": ["langchain"],
    "Vector Databases": ["vector database", "vector databases", "faiss", "pinecone", "chromadb", "vector search"],
    "OpenAI API": ["openai", "openai api", "gpt", "chatgpt api"],

    # Analytics / Stats
    "Statistics": ["statistics", "statistical analysis"],
    "A/B Testing": ["a/b testing", "ab testing", "experimentation"],
    "Data Modeling": ["data modeling", "data modelling"],

    # Finance (domain)
    "Financial Modeling": ["financial modeling", "financial modelling"],
    "Risk Analysis": ["risk analysis", "risk management"],

    # Soft / role
    "Project Management": ["project management"],
    "Agile/Scrum": ["agile", "scrum"],
    "Communication": ["communication skills", "communication"],
    "Leadership": ["leadership", "team leadership"],
    "Problem Solving": ["problem solving", "problem-solving"],
}

# category -> canonical skill names in that category (drives UI grouping)
SKILL_CATEGORIES: Dict[str, List[str]] = {
    "Programming": ["Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "C", "Go", "R", "SQL", "Scala", "Bash/Shell"],
    "Data": ["Pandas", "NumPy", "Data Analysis", "Data Visualization", "Excel", "Power BI", "Tableau",
             "ETL", "Apache Spark", "Hadoop", "Apache Airflow", "Databricks", "Snowflake", "Data Modeling"],
    "Machine Learning": ["Machine Learning", "Deep Learning", "Scikit-learn", "TensorFlow", "PyTorch",
                          "XGBoost", "LightGBM", "Keras", "Feature Engineering", "Model Deployment",
                          "Time Series Analysis"],
    "NLP": ["Natural Language Processing", "spaCy", "NLTK", "Text Classification",
            "Named Entity Recognition"],
    "Computer Vision": ["Computer Vision", "OpenCV", "Image Processing"],
    "Cloud": ["AWS", "AWS Glue", "AWS Redshift", "AWS Athena", "GCP", "Microsoft Azure"],
    "Databases": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "NoSQL"],
    "BI": ["Business Intelligence"],
    "DevOps": ["Docker", "Kubernetes", "CI/CD", "Git", "GitHub", "GitLab", "Jenkins", "Linux", "Terraform"],
    "Web": ["Flask", "FastAPI", "Django", "Streamlit", "REST APIs", "React", "Node.js", "HTML/CSS"],
    "AI/LLM": ["Large Language Models", "Retrieval Augmented Generation", "Prompt Engineering",
               "LangChain", "Vector Databases", "OpenAI API"],
    "Finance": ["Financial Modeling", "Risk Analysis"],
    "Analytics": ["Statistics", "A/B Testing"],
    "Soft Skills": ["Project Management", "Agile/Scrum", "Communication", "Leadership", "Problem Solving"],
}


def _build_alias_lookup() -> Dict[str, str]:
    """alias (normalized) -> canonical skill name, longest-alias-first isn't
    needed here because matching is done as whole-phrase regex, not substring."""
    lookup = {}
    for canonical, aliases in SKILL_ALIASES.items():
        all_forms = set(aliases) | {canonical.lower()}
        for alias in all_forms:
            lookup[_normalize_alias(alias)] = canonical
    return lookup


def _normalize_alias(alias: str) -> str:
    alias = alias.lower().strip()
    alias = re.sub(r"[\s\-]+", " ", alias)
    return alias


ALIAS_LOOKUP = _build_alias_lookup()

# sort aliases longest-first so multi-word skills match before their
# single-word substrings would otherwise short-circuit
_ALL_ALIASES_SORTED = sorted(ALIAS_LOOKUP.keys(), key=len, reverse=True)

# precompiled regex per alias, word-boundary safe even for tokens with . + #
_ALIAS_PATTERNS: List[Tuple[re.Pattern, str]] = []
for alias in _ALL_ALIASES_SORTED:
    escaped = re.escape(alias).replace(r"\ ", r"[\s\-]+")
    pattern = re.compile(r"(?<![a-zA-Z0-9])" + escaped + r"(?![a-zA-Z0-9])", re.IGNORECASE)
    _ALIAS_PATTERNS.append((pattern, ALIAS_LOOKUP[alias]))


def canonical_category(skill: str) -> str:
    for cat, skills in SKILL_CATEGORIES.items():
        if skill in skills:
            return cat
    return "Other"


def extract_skills(text: str) -> Set[str]:
    """Return the set of canonical skills explicitly present in text.
    Uses exact/alias phrase matching only — never infers a skill from a
    loosely related term."""
    if not text:
        return set()
    found = set()
    for pattern, canonical in _ALIAS_PATTERNS:
        if pattern.search(text):
            found.add(canonical)
    return found


def normalize_skill_phrase(phrase: str) -> str:
    """Best-effort: map a single free-text phrase to its canonical skill
    name if recognised, else return the original phrase title-cased."""
    key = _normalize_alias(phrase)
    if key in ALIAS_LOOKUP:
        return ALIAS_LOOKUP[key]
    found = extract_skills(phrase)
    if len(found) == 1:
        return next(iter(found))
    return phrase.strip()


ALL_CANONICAL_SKILLS = sorted(SKILL_ALIASES.keys())
