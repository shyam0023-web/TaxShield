"""
TaxShield — OCR Tool (Privacy-Safe Local OCR)
Primary: Surya OCR (100% local, no data leaves the server)
Fallback: pytesseract (local)
No cloud API calls — DPDP Act compliant.
"""
import io
import json
import re
import fitz  # PyMuPDF for PDF to images
from typing import Dict, List, Optional
from PIL import Image
from app.logger import logger


class OCREngine:
    """
    Local-only OCR using Surya.
    Models are loaded lazily on first use (~200MB download on first run).
    Runs on CPU by default; GPU if available.
    """

    def __init__(self):
        self._foundation = None
        self._recognition = None
        self._detection = None

    def _ensure_models(self):
        """Lazy-load Surya models on first call (avoids import-time delay)."""
        if self._recognition is not None:
            return

        logger.info("Loading Surya OCR models (first run downloads ~200MB)...")
        try:
            from surya.foundation import FoundationPredictor
            from surya.recognition import RecognitionPredictor
            from surya.detection import DetectionPredictor

            self._foundation = FoundationPredictor()
            self._detection = DetectionPredictor()
            self._recognition = RecognitionPredictor(self._foundation)
            logger.info("Surya OCR models loaded successfully")
        except ImportError:
            logger.warning("Surya OCR not installed, will use Tesseract fallback")
            self._recognition = None

    def _pdf_to_images(self, pdf_bytes: bytes) -> List[Image.Image]:
        """Convert PDF pages to PIL images using PyMuPDF."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            # 2x zoom for better OCR quality
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        doc.close()
        return images

    def _ocr_with_surya(self, images: List[Image.Image]) -> List[dict]:
        """Run Surya OCR on a list of PIL images."""
        self._ensure_models()

        if self._recognition is None:
            raise RuntimeError("Surya OCR not available")

        predictions = self._recognition(images, det_predictor=self._detection)

        pages = []
        for page_num, pred in enumerate(predictions):
            # Each prediction has text_lines with text + confidence
            page_text_lines = []
            total_confidence = 0.0
            line_count = 0

            for line in pred.text_lines:
                page_text_lines.append(line.text)
                total_confidence += line.confidence
                line_count += 1

            avg_confidence = total_confidence / max(line_count, 1)
            page_text = "\n".join(page_text_lines)

            pages.append({
                "page_number": page_num + 1,
                "text": page_text,
                "confidence": round(avg_confidence, 3),
                "line_count": line_count,
            })

        return pages

    def _ocr_with_tesseract(self, images: List[Image.Image]) -> List[dict]:
        """Fallback: Tesseract OCR (local, needs tesseract binary installed)."""
        try:
            import pytesseract
        except ImportError:
            raise RuntimeError("Neither Surya nor Tesseract available for OCR")

        pages = []
        for page_num, img in enumerate(images):
            text = pytesseract.image_to_string(img, lang="eng")
            pages.append({
                "page_number": page_num + 1,
                "text": text,
                "confidence": 0.70,  # Tesseract doesn't give per-page confidence easily
                "line_count": len(text.strip().split("\n")),
            })
        return pages

    async def extract_from_pdf(self, pdf_bytes: bytes) -> dict:
        """
        Extract text from PDF using local OCR.
        Primary: Surya OCR | Fallback: Tesseract
        Returns same shape as the old Gemini Vision OCR for compatibility.
        """
        import asyncio

        try:
            # Convert PDF to images (CPU, fast)
            images = await asyncio.to_thread(self._pdf_to_images, pdf_bytes)
            logger.info(f"Converted PDF to {len(images)} page images")

            # Try Surya first, fall back to Tesseract
            try:
                pages = await asyncio.to_thread(self._ocr_with_surya, images)
                engine_name = "surya_local"
            except Exception as e:
                logger.warning(f"Surya OCR failed ({e}), falling back to Tesseract")
                pages = await asyncio.to_thread(self._ocr_with_tesseract, images)
                engine_name = "tesseract_local"

            # Sort by page number
            pages = sorted(pages, key=lambda p: p["page_number"])

            return {
                "pages": pages,
                "full_text": "\n\n".join([p["text"] for p in pages]),
                "total_pages": len(pages),
                "ocr_engine": engine_name,
            }

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise

    async def extract_critical_fields(self, pdf_bytes: bytes) -> Dict[str, List[str]]:
        """Extract critical fields using regex from OCR'd text."""
        try:
            result = await self.extract_from_pdf(pdf_bytes)
            return self._extract_critical_from_text(result["full_text"])
        except Exception as e:
            logger.error(f"Critical field extraction failed: {e}")
            raise

    def _extract_critical_from_text(self, text: str) -> Dict[str, List[str]]:
        """Extract critical fields using regex patterns."""
        from app.tools.patterns import (
            GSTIN_PATTERN, DIN_PATTERN, AMOUNT_PATTERN,
            NOTICE_NUMBER_PATTERN, SECTION_PATTERN,
        )

        patterns = {
            "GSTIN": GSTIN_PATTERN,
            "DIN": DIN_PATTERN,
            "Amount": AMOUNT_PATTERN,
            "Notice_Number": NOTICE_NUMBER_PATTERN,
            "Section": SECTION_PATTERN,
        }

        extracted = {}
        for field, pattern in patterns.items():
            matches = re.findall(pattern, text)
            extracted[field] = list(set(matches))

        return extracted

    async def validate_extraction_quality(self, extracted_text: str) -> Dict[str, float]:
        """
        Validate OCR quality using heuristics (no cloud calls).
        Checks: text length, number density, structure markers.
        """
        if not extracted_text or len(extracted_text.strip()) < 50:
            return {
                "text_clarity": 0.2,
                "number_accuracy": 0.2,
                "structure_preservation": 0.2,
                "overall_quality": 0.2,
            }

        text = extracted_text.strip()

        # Heuristic 1: Text clarity — ratio of printable chars
        printable = sum(1 for c in text if c.isprintable() or c in "\n\t")
        clarity = min(printable / len(text), 1.0)

        # Heuristic 2: Number density — GST notices should have numbers
        digits = sum(1 for c in text if c.isdigit())
        number_density = min(digits / max(len(text), 1) * 10, 1.0)

        # Heuristic 3: Structure — presence of key GST markers
        markers = ["GSTIN", "Section", "Notice", "Order", "Tax", "Amount",
                    "Rs.", "₹", "DIN", "dated", "Deputy", "Assistant"]
        found = sum(1 for m in markers if m.lower() in text.lower())
        structure = min(found / 5, 1.0)

        overall = (clarity * 0.3 + number_density * 0.3 + structure * 0.4)

        return {
            "text_clarity": round(clarity, 2),
            "number_accuracy": round(number_density, 2),
            "structure_preservation": round(structure, 2),
            "overall_quality": round(overall, 2),
        }


# Singleton instance
ocr_engine = OCREngine()
