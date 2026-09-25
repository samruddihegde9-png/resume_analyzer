"""
Shared low-level helpers: text cleanup, tokenisation, safe I/O.
No third-party AI models live here — this module stays dependency-light
so every other module can import it without side effects.
"""

import re
import string
from typing import List

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "of", "at", "by", "for",
    "with", "about", "against", "between", "into", "through", "during",
    "before", "after", "above", "below", "to", "from", "up", "down", "in",
    "out", "on", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "s", "t", "can", "will", "just", "don", "should", "now", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "having",
    "do", "does", "did", "doing", "this", "that", "these", "those", "i",
    "you", "he", "she", "it", "we", "they", "them", "his", "her", "its",
    "our", "their", "as", "we're", "we'll", "we'd",
}

_PUNCT_TABLE = str.maketrans({c: " " for c in string.punctuation if c not in "+#."})


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace and strip."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text: str) -> str:
    """Lowercase + strip stray control characters, keep punctuation that
    matters for skills like 'c++', 'c#', 'node.js'."""
    if not text:
        return ""
    text = text.replace("\u2019", "'").replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", " ", text)
    return normalize_whitespace(text)


def tokenize(text: str) -> List[str]:
    """Simple, dependency-free word tokenizer used for TF-IDF fallback
    and keyword scanning. Keeps tokens like c++, c#, .net, node.js intact."""
    text = text.lower()
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#\.\-]*", text)
    cleaned = []
    for t in tokens:
        t = t.strip(".-")
        if not t or t in STOPWORDS:
            continue
        if len(t) == 1 and t not in {"c", "r"}:
            continue
        cleaned.append(t)
    return cleaned


def sentences(text: str) -> List[str]:
    """Very light sentence/bullet splitter used across modules."""
    text = normalize_whitespace(text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def bullet_lines(text: str) -> List[str]:
    """Split raw resume text into candidate bullet points."""
    lines = re.split(r"[\n\r]+", text)
    bullets = []
    for line in lines:
        line = line.strip(" \t")
        line = re.sub(r"^[\u2022\-\*\u25CF\u25AA\u2013▪●○◦]+\s*", "", line)
        if len(line.split()) >= 4:
            bullets.append(line)
    return bullets


def safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def pct(a: float, b: float) -> float:
    return round(safe_div(a, b) * 100, 2)


def clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))
