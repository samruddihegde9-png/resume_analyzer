import fitz
import pdfplumber

# =========================
# HYBRID RESUME PARSER
# =========================

def extract_resume(file):

    text = ""

    # Primary extraction using PyMuPDF
    try:

        pdf = fitz.open(
            stream=file.read(),
            filetype="pdf"
        )

        for page in pdf:
            text += page.get_text()

    except:
        pass

    # Fallback extraction using pdfplumber
    if not text.strip():

        file.seek(0)

        with pdfplumber.open(file) as pdf:

            for page in pdf.pages:

                extracted = page.extract_text()

                if extracted:
                    text += extracted

    return text