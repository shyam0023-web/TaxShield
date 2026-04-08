"""
TaxShield — Enhanced OCR+PDF Processor
Handles scanned tax notices, structured extraction, format preservation.
Integrates with existing OCREngine but adds domain-specific processing.
"""
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re
from datetime import datetime

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class DocumentStructure:
    """Represents extracted structure from a tax document"""
    header: Optional[str] = None
    body_paragraphs: List[Dict[str, Any]] = None
    footer: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.body_paragraphs is None:
            self.body_paragraphs = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PageAnalysis:
    """Structure of a single page"""
    page_number: int
    raw_text: str
    confidence: float
    sections: List[Dict[str, Any]]  # Detected sections on page
    tables: List[Dict[str, Any]]  # Detected tables
    page_role: str  # e.g., "header", "body", "footer"


class TaxDocumentParser:
    """
    Parse tax notices/circulars with domain awareness.
    
    Recognizes:
    - Notice header (letterhead, issue details)
    - Body sections (facts, demand, timeline)
    - Footer (officer signature, date)
    - Structured tables (demand schedule, additions)
    """
    
    # Patterns to identify tax notice structure
    HEADER_PATTERNS = [
        r"(?:show\s+cause\s+notice|demand\s+notice|notice(?:\s+under)?)",
        r"(?:central\s+gstin|income\s+tax\s+department)",
        r"(?:notice\s+no\.?|reference\s+no\.?)[\s:]+([\d\w\-/]+)",
    ]
    
    SECTION_PATTERNS = [
        r"(?:facts|background|reason|grounds)[\s:]*\n",
        r"(?:demand|liability|assessment)[\s:]*\n",
        r"(?:statutory\s+provisions|law|sections)[\s:]*\n",
        r"(?:relief|exemption|time\s+bar)[\s:]*\n",
    ]
    
    FOOTER_PATTERNS = [
        r"(?:respectfully|yours\s+faithfully)",
        r"(?:signature|signed)",
        r"(?:date)[\s:]*(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})",
    ]
    
    # Notice type detection
    NOTICE_TYPE_PATTERNS = {
        "SCN": r"show\s+cause\s+notice",
        "DEMAND": r"demand\s+notice",
        "PENALTY": r"penalty\s+notice",
        "ADJOURNMENT": r"adjournment\s+notice",
        "EXEMPTION": r"exemption\s+notice|exemption\s+clause",
    }
    
    # Extract key amounts (with currency and context)
    AMOUNT_PATTERNS = [
        r"(?:demand|liability|tax)[\s:]*₹\s*([\d,]+(?:\.\d+)?)",
        r"(?:amount|sum)[\s:]*[₹Rs\.]*\s*([\d,]+(?:\.\d+)?)",
        r"([\d,]+(?:\.\d+)?)\s*(?:lakhs?|crores?|thousands?)",
    ]
    
    def __init__(self):
        self.header_regexes = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.HEADER_PATTERNS]
        self.section_regexes = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.SECTION_PATTERNS]
        self.footer_regexes = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.FOOTER_PATTERNS]
        self.notice_type_regexes = {k: re.compile(v, re.IGNORECASE) for k, v in self.NOTICE_TYPE_PATTERNS.items()}
        self.amount_regexes = [re.compile(p, re.IGNORECASE) for p in self.AMOUNT_PATTERNS]
    
    def detect_notice_type(self, text: str) -> Optional[str]:
        """Detect notice type from text"""
        for notice_type, regex in self.notice_type_regexes.items():
            if regex.search(text[:2000]):  # Check in header
                return notice_type
        return "OTHER"
    
    def extract_key_dates(self, text: str) -> Dict[str, Optional[str]]:
        """Extract important dates from notice"""
        dates = {}
        
        # Issue date
        issue_match = re.search(r"(?:issued?|date)[\s:]*(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})", text[:1000], re.IGNORECASE)
        if issue_match:
            dates["issued"] = issue_match.group(1)
        
        # Response deadline
        deadline_match = re.search(r"(?:within|by|before)[\s]*(\d+)\s*(?:days?|weeks?)", text, re.IGNORECASE)
        if deadline_match:
            dates["response_period_days"] = deadline_match.group(1)
        
        # FY reference
        fy_match = re.search(r"(20\d{2}[-/]?\d{2})", text)
        if fy_match:
            dates["financial_year"] = fy_match.group(1)
        
        return dates
    
    def extract_amounts(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract monetary amounts with context"""
        amounts_found = {}
        
        for amount_type, pattern in [
            ("demand", r"(?:demand|liability)[\s:]*[₹Rs\.]*\s*([\d,]+(?:\.\d+)?)"),
            ("penalty", r"(?:penalty)[\s:]*[₹Rs\.]*\s*([\d,]+(?:\.\d+)?)"),
            ("interest", r"(?:interest)[\s:]*[₹Rs\.]*\s*([\d,]+(?:\.\d+)?)"),
            ("tax", r"(?:tax)[\s:]*[₹Rs\.]*\s*([\d,]+(?:\.\d+)?)"),
        ]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            amounts_found[amount_type] = [
                {"value": m.group(1).replace(",", ""), "context_start": max(0, m.start()-50)}
                for m in matches
            ]
        
        return amounts_found
    
    def split_into_paragraphs(self, text: str) -> List[Dict[str, Any]]:
        """Split text into logical paragraphs with role detection"""
        paragraphs = []
        
        # Split by blank lines
        raw_paras = text.split("\n\n")
        
        for i, para_text in enumerate(raw_paras):
            para_text = para_text.strip()
            if not para_text:
                continue
            
            # Detect paragraph role
            role = "body"
            if i < 5:  # Early paragraphs likely header
                if any(regex.search(para_text) for regex in self.header_regexes):
                    role = "header"
            if i > len(raw_paras) - 3:  # Last few paragraphs
                if any(regex.search(para_text) for regex in self.footer_regexes):
                    role = "footer"
            
            # Detect section markers
            section_match = next(
                (m for regex in self.section_regexes for m in [regex.search(para_text)]),
                None
            )
            section_type = None
            if section_match:
                section_type = section_match.group(0).strip()
            
            paragraphs.append({
                "text": para_text,
                "role": role,
                "section_type": section_type,
                "line_count": len(para_text.split("\n")),
                "char_count": len(para_text),
            })
        
        return paragraphs
    
    def extract_structure(self, full_text: str, ocr_confidence: float = 0.8) -> DocumentStructure:
        """
        Extract structured information from full document text.
        
        Args:
            full_text: Full OCR text from document
            ocr_confidence: OCR confidence score (0-1)
            
        Returns:
            DocumentStructure with identified components
        """
        logger.info(f"Extracting structure (OCR confidence: {ocr_confidence:.2%})")
        
        # Split into paragraphs
        paragraphs = self.split_into_paragraphs(full_text)
        
        # Extract header
        header_para = next((p for p in paragraphs if p["role"] == "header"), None)
        header_text = header_para["text"] if header_para else None
        
        # Extract body
        body_paragraphs = [p for p in paragraphs if p["role"] == "body"]
        
        # Extract footer
        footer_para = next((p for p in paragraphs if p["role"] == "footer"), None)
        footer_text = footer_para["text"] if footer_para else None
        
        # Extract metadata
        metadata = {
            "extracted_at": datetime.utcnow().isoformat(),
            "ocr_confidence": ocr_confidence,
            "notice_type": self.detect_notice_type(full_text),
            "dates": self.extract_key_dates(full_text),
            "amounts": self.extract_amounts(full_text),
            "paragraph_count": len(body_paragraphs),
        }
        
        return DocumentStructure(
            header=header_text,
            body_paragraphs=body_paragraphs,
            footer=footer_text,
            metadata=metadata,
        )


class EnhancedPDFProcessor:
    """
    Enhanced PDF processing with structure preservation.
    
    Pipeline:
    1. Detect PDF type (digital vs. scanned)
    2. Extract text (native or OCR)
    3. Analyze structure (header, body, footer)
    4. Extract metadata (notice type, dates, amounts)
    5. Return structured document
    """
    
    def __init__(self, ocr_engine=None):
        """
        Initialize processor.
        
        Args:
            ocr_engine: OCREngine instance from app.tools.ocr
        """
        self.ocr_engine = ocr_engine  # Will use existing if provided
        self.parser = TaxDocumentParser()
    
    async def process_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Process PDF and return structured output.
        
        Args:
            pdf_bytes: PDF file bytes
            
        Returns:
            Dict with full_text, structure, metadata
        """
        logger.info(f"Processing PDF ({len(pdf_bytes)/1024:.1f} KB)")
        
        # Extract text using existing OCREngine if available
        if self.ocr_engine:
            try:
                ocr_result = await self.ocr_engine.extract_from_pdf(pdf_bytes)
                pages_data = ocr_result.get("pages", [])
                full_text = ocr_result.get("full_text", "")
                ocr_confidence = np.mean([p.get("confidence", 0.8) for p in pages_data])
            except Exception as e:
                logger.warning(f"OCR failed, using fallback: {e}")
                pages_data, full_text, ocr_confidence = await self._fallback_extraction(pdf_bytes)
        else:
            pages_data, full_text, ocr_confidence = await self._fallback_extraction(pdf_bytes)
        
        # Analyze structure
        structure = self.parser.extract_structure(full_text, ocr_confidence)
        
        return {
            "full_text": full_text,
            "pages": pages_data,
            "structure": {
                "header": structure.header,
                "body_paragraphs": structure.body_paragraphs,
                "footer": structure.footer,
                "metadata": structure.metadata,
            },
            "quality_metrics": {
                "ocr_confidence": float(ocr_confidence),
                "total_pages": len(pages_data),
                "text_length": len(full_text),
                "is_digital_pdf": ocr_confidence > 0.9,
            },
            "tax_metadata": {
                "notice_type": structure.metadata.get("notice_type"),
                "dates": structure.metadata.get("dates"),
                "amounts": structure.metadata.get("amounts"),
            },
        }
    
    async def _fallback_extraction(self, pdf_bytes: bytes) -> Tuple[List[Dict], str, float]:
        """Fallback text extraction using PyMuPDF only"""
        import asyncio
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_data = []
        full_text = ""
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            pages_data.append({
                "page_number": page_num + 1,
                "text": text,
                "confidence": 0.95,  # Native PDF
                "line_count": len(text.split("\n")),
            })
            full_text += text + "\n\n"
        
        doc.close()
        
        # Average confidence
        avg_confidence = np.mean([p["confidence"] for p in pages_data])
        
        return pages_data, full_text, avg_confidence


# ═══════════════════════════════════════════
# Singleton Instance
# ═══════════════════════════════════════════

pdf_processor = EnhancedPDFProcessor()
