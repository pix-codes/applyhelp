import fitz

from app.services.resume.parser import ResumeParserService


def test_pdf_text_extraction():
    # Create an in-memory PDF using PyMuPDF
    doc = fitz.open()
    page = doc.new_page()
    sample_text = "John Doe\nSenior Python Backend Engineer\nSkills: Python, FastAPI, Docker, PostgreSQL\nKathmandu, Nepal"
    page.insert_text((50, 50), sample_text)
    pdf_bytes = doc.tobytes()
    doc.close()

    extracted = ResumeParserService.extract_text_from_pdf(pdf_bytes)
    assert "John Doe" in extracted
    assert "FastAPI" in extracted
    assert "Nepal" in extracted
