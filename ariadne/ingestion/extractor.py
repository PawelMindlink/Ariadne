import os
from pypdf import PdfReader
import pytesseract
from PIL import Image
import io
# import fitz # PyMuPDF removed as we are using pypdf for now
# actually pypdf image extraction is hard.
# Let's use `pdf2image` if we can, but that requires poppler.
# Start with pypdf text extraction. If 0 text, return empty.
# For OCR, we usually need to convert PDF to Image. 
# Simplest route without heavily external deps (poppler) on Windows is problematic.
# Let's assume the user has Tesseract installed.

class Extractor:
    def __init__(self):
        pass

    def extract_text(self, file_path):
        """
        Extracts text from a file.
        Returns: (text, method) where method is 'native' or 'ocr' or 'error'.
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return self._extract_from_pdf(file_path)
        elif ext in ['.txt', '.md', '.csv', '.json']:
            return self._extract_plain(file_path)
        else:
            return None, 'unsupported'

    def _extract_from_pdf(self, file_path):
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            
            # Heuristic: If text is very short given the number of pages, it's likely a scan.
            # E.g. < 50 chars per page on average?
            if len(text.strip()) < 50:
                 # TODO: OCR FALLBACK
                 # Implementing robust OCR requires converting PDF -> Image.
                 # This often requires poppler/pdf2image. 
                 # For Phase 1, we will mark it as 'SCAN_REQUIRED' if text is empty.
                 return "", "needs_ocr_scan"
            
            return text, 'native'
            
        except Exception as e:
            return str(e), 'error'

    def _extract_plain(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read(), 'native'
        except Exception as e:
            return str(e), 'error'
