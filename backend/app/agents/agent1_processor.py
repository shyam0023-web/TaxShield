"""
TaxShield — Agent 1: Document Processor
Pipeline: PDF → OCR → Sanitize → Redact PII → NER → Structure → Time-Bar Flag

Does NOT make legal decisions — only extracts and flags.
Does NOT short-circuit on time-bar — passes everything to Agent 2.
"""
from app.tools.ocr import ocr_engine
from app.tools.notice_ner import notice_ner
from app.tools.input_sanitizer import sanitizer
from app.tools.notice_structurer import structurer
from app.tools.timebar import timebar
from app.tools.redaction import redactor
from app.utils import parse_llm_extracted
import json
import logging

logger = logging.getLogger(__name__)


class Agent1Processor:
    """
    Document Processor Agent.
    
    6-step pipeline:
    1. OCR — Extract text from PDF via Gemini Vision
    2. Sanitize — Strip prompt injection attempts
    3. Redact — Remove PII (PAN, Aadhaar) before any LLM sees it
    4. NER — Extract entities (GSTIN, sections, amounts, dates)
    5. Structure — Annotate paragraphs (HEADER, FACTS, DEMAND, etc.)
    6. Time-bar flag — Preliminary check, Agent 2 decides
    """
    
    async def process(self, pdf_bytes: bytes) -> dict:
        """
        Full processing pipeline for a GST notice PDF.
        Returns structured output for Agent 2.
        """
        logger.info("Agent 1: Starting document processing")
        errors = []
        
        # ═══ Step 1: OCR ═══
        logger.info("Step 1/6: OCR extraction via local engine (Surya / Tesseract)")
        try:
            ocr_result = await ocr_engine.extract_from_pdf(pdf_bytes)
            raw_text = ocr_result["full_text"]
            logger.info(f"OCR complete: {ocr_result['total_pages']} pages, {len(raw_text)} chars")
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return {
                "processing_status": "failed",
                "error": f"OCR extraction failed: {str(e)}",
                "stage": "ocr",
                "current_agent": "agent1"
            }
        
        # ═══ Step 1B: GST Notice Validation Gate ═══
        logger.info("Step 1B: Validating if document is a GST notice...")
        is_gst = self._is_gst_notice(raw_text)
        if not is_gst:
            logger.warning("Document is NOT a GST notice. Rejecting.")
            return {
                "processing_status": "rejected",
                "is_gst_notice": False,
                "raw_text": raw_text[:500],
                "draft_error": "This document does not appear to be a GST notice. TaxShield only processes GST-related notices (SCN, DRC, ASMT, etc.).",
                "current_agent": "agent1",
            }
        logger.info("✅ Document confirmed as GST notice")

        # ═══ Step 2: Sanitize ═══
        logger.info("Step 2/6: Input sanitization")
        sanitize_result = sanitizer.sanitize(raw_text)
        clean_text = sanitize_result["sanitized_text"]
        if sanitize_result["injections_found"] > 0:
            logger.warning(f"Found {sanitize_result['injections_found']} injection attempts")
        
        # ═══ Step 3: PII Redaction ═══
        logger.info("Step 3/6: PII redaction")
        redaction_result = redactor.redact(clean_text)
        redacted_text = redaction_result["redacted_text"]
        logger.info(f"Redacted {len(redaction_result['redacted_fields'])} PII fields")
        
        # ═══ Step 4: Named Entity Recognition ═══
        logger.info("Step 4/6: Entity extraction (NER)")
        try:
            entities = await notice_ner.extract_entities(redacted_text)
            
            # Validate entities
            validation = await notice_ner.validate_entities(entities)
            logger.info(f"NER complete: completeness={validation['completeness_score']:.0%}")
        except Exception as e:
            logger.error(f"NER failed: {e}")
            entities = {"GSTIN": [], "DIN": [], "SECTIONS": [], "llm_extracted": {}}
            validation = {"is_valid": False, "completeness_score": 0}
            errors.append(f"NER partially failed: {str(e)}")
        
        # ═══ Step 5: Notice Structuring ═══
        logger.info("Step 5/6: Notice structuring")
        try:
            annotations = await structurer.structure_notice(redacted_text)
        except Exception as e:
            logger.error(f"Structuring failed: {e}")
            annotations = []
            errors.append(f"Structuring failed: {str(e)}")
        
        # ═══ Step 6: Preliminary Time-Bar Check ═══
        logger.info("Step 6/6: Preliminary time-bar check")
        llm_data = parse_llm_extracted(entities)
        
        time_bar = timebar.check_potential_timebar(
            notice_date_str=llm_data.get("notice_date", ""),
            financial_year=llm_data.get("financial_year", "")
        )
        
        # ═══ Build Output ═══
        output = {
            # Text
            "raw_text": redacted_text,  # PII-redacted version
            
            # OCR metadata
            "ocr_metadata": {
                "engine": ocr_result["ocr_engine"],
                "total_pages": ocr_result["total_pages"],
                "confidence": ocr_result["pages"][0]["confidence"] if ocr_result["pages"] else 0
            },
            
            # Entities
            "entities": entities,
            "entity_validation": validation,
            
            # Structure
            "notice_annotations": annotations,
            
            # Time-bar (preliminary — Agent 2 decides)
            "time_bar": time_bar,
            
            # Redaction info
            "redacted_fields": [f["type"] for f in redaction_result["redacted_fields"]],
            
            # Sanitization info
            "sanitization": {
                "injections_found": sanitize_result["injections_found"],
                "flags": sanitize_result["flags"]
            },
            
            # Processing status — explicit signal for Agent 2
            "processing_status": "partial" if errors else "complete",
            
            # Processing errors (non-fatal)
            "processing_errors": errors,
            
            # Agent metadata
            "current_agent": "agent1"
        }
        
        logger.info(f"Agent 1: Processing complete. "
                     f"Pages={ocr_result['total_pages']}, "
                     f"Entities={len(entities.get('GSTIN', []))} GSTINs, "
                     f"Sections={entities.get('SECTIONS', [])}, "
                     f"TimeBar={time_bar.get('potentially_time_barred', False)}")
        
        return output

    def _is_gst_notice(self, text: str) -> bool:
        """
        Check if the extracted text is a GST-related notice.
        Uses keyword matching against a curated set of GST legal vocabulary.
        Returns True if at least 2 GST-specific signals are found.
        """
        import re
        text_lower = text.lower()

        # Tier 1: Strong GST signals (any ONE of these = GST notice)
        strong_signals = [
            r'\bgstin\b',
            r'\bgstr[-\s]?[123][ab]?\b',
            r'\bcgst\b',
            r'\bsgst\b',
            r'\bigst\b',
            r'\bgst\s+act\b',
            r'\bcentral\s+goods\s+and\s+services\s+tax\b',
            r'\bstate\s+goods\s+and\s+services\s+tax\b',
            r'\binput\s+tax\s+credit\b',
            r'\bitc\b',
            r'\bdrc[-\s]?0[1-9]\b',
            r'\basmt[-\s]?\d{2}\b',
        ]

        strong_hits = sum(1 for p in strong_signals if re.search(p, text_lower))
        if strong_hits >= 1:
            return True

        # Tier 2: Weak GST signals (need at least 3 together)
        weak_signals = [
            r'\bshow\s+cause\s+notice\b',
            r'\bscn\b',
            r'\bsection\s+(73|74|16|17|29|30)\b',
            r'\bdemand\b',
            r'\bpenalty\b',
            r'\btax\s+(period|liability|amount)\b',
            r'\bregistered\s+person\b',
            r'\bproper\s+officer\b',
            r'\badjudicating\s+authority\b',
            r'\breturn\s+filing\b',
            r'\be[-\s]?way\s+bill\b',
        ]

        weak_hits = sum(1 for p in weak_signals if re.search(p, text_lower))
        if weak_hits >= 3:
            return True

        logger.info(f"GST gate: strong_hits={strong_hits}, weak_hits={weak_hits} — NOT a GST notice")
        return False


# Singleton
agent1 = Agent1Processor()
