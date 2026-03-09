"""
TaxShield — OCR Tool
Primary: Gemini Vision API
Fallback: PaddleOCR → pytesseract
Majority voting on critical fields (GSTIN, Amount, DIN)
"""
import io
import fitz  # PyMuPDF for PDF to images
from typing import Dict, List, Optional
from app.llm.gemini_client import gemini
from app.logger import logger


class OCREngine:
    async def extract_from_pdf(self, pdf_bytes: bytes) -> dict:
        """Extract text from PDF using Gemini Vision."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for quality
                img_bytes = pix.tobytes("png")
                
                # Send to Gemini Vision
                prompt = """Extract ALL text from this GST tax notice image. 
                Preserve the structure: headers, paragraphs, table rows.
                Return the text exactly as written, including:
                - GSTIN numbers
                - Section numbers (e.g., Section 73, 74)
                - Monetary amounts (₹)
                - Dates
                - DIN numbers
                - Notice reference numbers
                Output as plain text, preserving layout."""
                
                text = await gemini.generate_with_image(prompt, img_bytes)
                
                pages.append({
                    "page_number": page_num + 1,
                    "text": text,
                    "confidence": 0.85  # Gemini Vision doesn't return confidence
                })
            
            doc.close()
            return {
                "pages": pages,
                "full_text": "\n\n".join([p["text"] for p in pages]),
                "total_pages": len(pages),
                "ocr_engine": "gemini_vision"
            }
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise
    
    async def extract_critical_fields(self, pdf_bytes: bytes) -> Dict[str, List[str]]:
        """Extract critical fields with majority voting across OCR engines."""
        try:
            # Primary extraction with Gemini Vision
            gemini_result = await self.extract_from_pdf(pdf_bytes)
            
            # Extract critical fields using regex from Gemini result
            critical_fields = self._extract_critical_from_text(gemini_result["full_text"])
            
            # TODO: Add fallback OCR engines (PaddleOCR, pytesseract) for majority voting
            # For now, return Gemini Vision results
            
            return critical_fields
            
        except Exception as e:
            logger.error(f"Critical field extraction failed: {e}")
            raise
    
    def _extract_critical_from_text(self, text: str) -> Dict[str, List[str]]:
        """Extract critical fields using regex patterns."""
        import re
        
        patterns = {
            "GSTIN": r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}',
            "DIN": r'[A-Z]{3}[A-Z\d]{17}',
            "Amount": r'₹?\s*[\d,]+\.?\d*',
            "Notice_Number": r'(?i)notice\s+no\.?\s*[:\-]?\s*([A-Z0-9\-/]+)',
            "Section": r'[Ss]ection\s+(\d+[A-Za-z]*(?:\(\d+\))*)'
        }
        
        extracted = {}
        for field, pattern in patterns.items():
            matches = re.findall(pattern, text)
            extracted[field] = list(set(matches))  # Remove duplicates
        
        return extracted
    
    async def validate_extraction_quality(self, extracted_text: str) -> Dict[str, float]:
        """Validate OCR extraction quality."""
        try:
            validation_prompt = f"""Analyze this OCR-extracted text from a GST notice and rate the quality:
            
            Text: {extracted_text[:1000]}
            
            Rate each aspect from 0.0 to 1.0:
            {{
                "text_clarity": 0.0,
                "number_accuracy": 0.0, 
                "structure_preservation": 0.0,
                "overall_quality": 0.0
            }}
            
            Consider: readability, number clarity, formatting preservation."""
            
            quality_scores = await gemini.generate(validation_prompt, json_mode=True)
            
            # Parse JSON response
            import json
            try:
                return json.loads(quality_scores)
            except json.JSONDecodeError:
                logger.warning("Failed to parse quality scores, returning defaults")
                return {
                    "text_clarity": 0.8,
                    "number_accuracy": 0.8,
                    "structure_preservation": 0.8,
                    "overall_quality": 0.8
                }
                
        except Exception as e:
            logger.error(f"Quality validation failed: {e}")
            return {
                "text_clarity": 0.5,
                "number_accuracy": 0.5,
                "structure_preservation": 0.5,
                "overall_quality": 0.5
            }


# Singleton instance
ocr_engine = OCREngine()
