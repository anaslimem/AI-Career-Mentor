import fitz 
from typing import Union
from io import BytesIO

def extract_text_from_pdf(file_path: Union[str, bytes]) -> str:
    """Extract text from a PDF file."""
    text = ""
    if isinstance(file_path, str):
        doc = fitz.open(file_path)
    else:
        doc = fitz.open(stream=BytesIO(file_path), filetype="pdf")
    
    try:
        for page in doc:
            text += page.get_text()
    finally:
        doc.close()
    return text

