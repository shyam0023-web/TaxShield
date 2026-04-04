"""
TaxShield — PII Redaction Tool (Presidio + Regex Hybrid)
Primary: Microsoft Presidio (NER-based, detects names, addresses, etc.)
Fallback: Regex-only (if Presidio not installed)
Supports reversible anonymization for PII re-injection after LLM drafting.
DPDP Act 2023 compliant — PII never leaves the server unredacted.
"""
import re
import os
import logging
import hashlib
import json
from typing import Dict, List, Optional, Tuple

from app.tools.patterns import PII_PATTERNS, KEEP_PATTERNS, GSTIN_PATTERN, DIN_PATTERN

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# Encryption key for reversible anonymization
# ═══════════════════════════════════════════
_REDACTION_KEY = os.environ.get("REDACTION_KEY", "taxshield-default-dev-key-change-in-prod")


def _make_token(pii_type: str, original: str) -> str:
    """Create a deterministic but non-reversible-without-key token for a PII value."""
    h = hashlib.sha256(f"{_REDACTION_KEY}:{original}".encode()).hexdigest()[:8]
    return f"[{pii_type}_{h}]"


class PIIRedactor:
    """
    Hybrid PII redactor.
    - Primary: Microsoft Presidio (NER-based) + custom Indian recognizers
    - Fallback: Regex patterns from app.tools.patterns
    - Supports reversible mode: stores a mapping to restore PII after LLM drafting
    """

    PATTERNS = PII_PATTERNS
    KEEP_PATTERNS = KEEP_PATTERNS

    def __init__(self):
        self._presidio_available = False
        self._analyzer = None
        self._anonymizer = None
        self._init_presidio()

    def _init_presidio(self):
        """Try to initialize Presidio with custom Indian PII recognizers."""
        try:
            from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
            from presidio_anonymizer import AnonymizerEngine

            # Custom Indian PII recognizers
            pan_recognizer = PatternRecognizer(
                supported_entity="IN_PAN",
                name="Indian PAN Recognizer",
                patterns=[Pattern(name="PAN", regex=r"\b[A-Z]{5}\d{4}[A-Z]\b", score=0.9)],
                context=["PAN", "pan", "permanent account"],
            )

            aadhaar_recognizer = PatternRecognizer(
                supported_entity="IN_AADHAAR",
                name="Indian Aadhaar Recognizer",
                patterns=[
                    Pattern(name="Aadhaar_no_space", regex=r"\b\d{12}\b", score=0.6),
                    Pattern(name="Aadhaar_spaced", regex=r"\b\d{4}\s\d{4}\s\d{4}\b", score=0.85),
                ],
                context=["aadhaar", "Aadhaar", "AADHAAR", "uid", "UID"],
            )

            phone_recognizer = PatternRecognizer(
                supported_entity="IN_PHONE",
                name="Indian Phone Recognizer",
                patterns=[
                    Pattern(name="Phone", regex=r"\b(?:\+91[\-\s]?)?[6-9]\d{9}\b", score=0.7),
                ],
                context=["phone", "mobile", "contact", "call"],
            )

            # GSTIN deny-list — tell Presidio to NOT flag these as PII
            gstin_recognizer = PatternRecognizer(
                supported_entity="IN_GSTIN",
                name="GSTIN Recognizer (keep, not PII)",
                patterns=[
                    Pattern(name="GSTIN", regex=GSTIN_PATTERN, score=0.95),
                ],
            )

            din_recognizer = PatternRecognizer(
                supported_entity="IN_DIN",
                name="DIN Recognizer (keep, not PII)",
                patterns=[
                    Pattern(name="DIN", regex=DIN_PATTERN, score=0.95),
                ],
            )

            # Use small spaCy model to fit Railway's 1GB RAM limit
            from presidio_analyzer.nlp_engine import NlpEngineProvider
            nlp_config = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
            provider = NlpEngineProvider(nlp_configuration=nlp_config)
            nlp_engine = provider.create_engine()
            self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            # Add custom recognizers
            self._analyzer.registry.add_recognizer(pan_recognizer)
            self._analyzer.registry.add_recognizer(aadhaar_recognizer)
            self._analyzer.registry.add_recognizer(phone_recognizer)
            self._analyzer.registry.add_recognizer(gstin_recognizer)
            self._analyzer.registry.add_recognizer(din_recognizer)

            self._anonymizer = AnonymizerEngine()
            self._presidio_available = True
            logger.info("Presidio PII engine initialized with Indian recognizers")

        except ImportError:
            logger.warning("Presidio not installed — using regex-only fallback. "
                           "Install with: pip install presidio-analyzer presidio-anonymizer")
            self._presidio_available = False

    # ═══════════════════════════════════════════
    # Public API (backward compatible)
    # ═══════════════════════════════════════════

    def redact(self, text: str, reversible: bool = False) -> dict:
        """
        Redact PII from text.

        Args:
            text: Input text to redact.
            reversible: If True, stores a mapping so PII can be restored later
                        via deanonymize().

        Returns:
            {
                redacted_text: str,
                redacted_fields: [{type, original_length, position}],
                pii_found: bool,
                pii_mapping: dict (only if reversible=True)
            }
        """
        if self._presidio_available:
            return self._redact_presidio(text, reversible)
        else:
            return self._redact_regex(text, reversible)

    def deanonymize(self, redacted_text: str, pii_mapping: dict) -> str:
        """
        Restore PII in a redacted text using the mapping from a reversible redact() call.
        Use this AFTER the LLM generates its draft to put real PII back.
        """
        result = redacted_text
        # Sort by token length descending to avoid partial replacements
        for token, original in sorted(pii_mapping.items(), key=lambda x: -len(x[0])):
            result = result.replace(token, original)
        return result

    # ═══════════════════════════════════════════
    # Presidio-based redaction
    # ═══════════════════════════════════════════

    def _redact_presidio(self, text: str, reversible: bool) -> dict:
        """Redact using Microsoft Presidio."""
        from presidio_analyzer import RecognizerResult
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig

        # Analyze text for PII
        results = self._analyzer.analyze(
            text=text,
            language="en",
            entities=[
                "IN_PAN", "IN_AADHAAR", "IN_PHONE",
                "EMAIL_ADDRESS", "PERSON",
                "IN_GSTIN", "IN_DIN",  # detected but excluded from redaction
            ],
        )

        # Filter out GSTIN and DIN — they are business identifiers, not PII
        business_entities = {"IN_GSTIN", "IN_DIN"}
        pii_results = [r for r in results if r.entity_type not in business_entities]

        # Also filter out any PAN-like match that falls inside a GSTIN span
        gstin_spans = [(r.start, r.end) for r in results if r.entity_type == "IN_GSTIN"]
        din_spans = [(r.start, r.end) for r in results if r.entity_type == "IN_DIN"]
        protected_spans = gstin_spans + din_spans

        pii_results = [
            r for r in pii_results
            if not any(r.start >= s and r.end <= e for s, e in protected_spans)
        ]

        # Build redacted text and mapping
        redacted_fields = []
        pii_mapping = {}

        # Map Presidio entity types to our placeholder names
        type_map = {
            "IN_PAN": "PAN",
            "IN_AADHAAR": "AADHAAR",
            "IN_PHONE": "PHONE",
            "EMAIL_ADDRESS": "EMAIL",
            "PERSON": "PERSON",
            "PHONE_NUMBER": "PHONE",
            "CREDIT_CARD": "CREDIT_CARD",
        }

        # Sort results by position (descending) to replace from end to start
        pii_results.sort(key=lambda r: r.start, reverse=True)

        redacted_text = text
        for r in pii_results:
            original = text[r.start:r.end]
            pii_type = type_map.get(r.entity_type, r.entity_type)

            if reversible:
                token = _make_token(pii_type, original)
                pii_mapping[token] = original
                replacement = token
            else:
                replacement = f"[{pii_type}_REDACTED]"

            redacted_text = redacted_text[:r.start] + replacement + redacted_text[r.end:]

            redacted_fields.append({
                "type": pii_type,
                "original_length": len(original),
                "position": r.start,
                "score": round(r.score, 2),
                "engine": "presidio",
            })

        # Reverse the fields list so they're in document order
        redacted_fields.reverse()

        logger.info(f"Presidio redacted {len(redacted_fields)} PII fields: "
                    f"{[f['type'] for f in redacted_fields]}")

        result = {
            "redacted_text": redacted_text,
            "redacted_fields": redacted_fields,
            "pii_found": len(redacted_fields) > 0,
        }
        if reversible:
            result["pii_mapping"] = pii_mapping

        return result

    # ═══════════════════════════════════════════
    # Regex fallback (backward compatible)
    # ═══════════════════════════════════════════

    def _redact_regex(self, text: str, reversible: bool) -> dict:
        """Fallback: regex-only redaction (original implementation)."""
        redacted_text = text
        redacted_fields = []
        pii_mapping = {}

        # Mark protected spans (GSTIN, DIN)
        protected_spans = set()
        for pattern in self.KEEP_PATTERNS:
            for match in re.finditer(pattern, text):
                protected_spans.add((match.start(), match.end()))

        # Redact PII patterns
        for field_type, config in self.PATTERNS.items():
            # Skip bank account unless in banking context
            if field_type == "BANK_ACCOUNT":
                if "bank" not in text.lower() and "account" not in text.lower():
                    continue

            for match in re.finditer(config["regex"], redacted_text):
                is_protected = any(
                    match.start() >= s and match.end() <= e
                    for s, e in protected_spans
                )
                if not is_protected:
                    redacted_fields.append({
                        "type": field_type,
                        "original_length": len(match.group()),
                        "position": match.start(),
                    })

            # Do the actual replacement
            if field_type != "BANK_ACCOUNT" or ("bank" in text.lower() or "account" in text.lower()):
                if reversible:
                    redacted_text = self._replace_reversible(
                        redacted_text, config["regex"], field_type, protected_spans, pii_mapping
                    )
                else:
                    redacted_text = self._replace_unprotected(
                        redacted_text, config["regex"], config["replacement"], protected_spans
                    )

        logger.info(f"Regex redacted {len(redacted_fields)} PII fields: "
                    f"{[f['type'] for f in redacted_fields]}")

        result = {
            "redacted_text": redacted_text,
            "redacted_fields": redacted_fields,
            "pii_found": len(redacted_fields) > 0,
        }
        if reversible:
            result["pii_mapping"] = pii_mapping

        return result

    def _replace_unprotected(self, text: str, pattern: str, replacement: str,
                              protected_spans: set) -> str:
        """Replace matches that aren't in protected spans."""
        result = text
        offset = 0
        for match in re.finditer(pattern, text):
            is_protected = any(
                match.start() >= s and match.end() <= e
                for s, e in protected_spans
            )
            if not is_protected:
                start = match.start() + offset
                end = match.end() + offset
                result = result[:start] + replacement + result[end:]
                offset += len(replacement) - (match.end() - match.start())
        return result

    def _replace_reversible(self, text: str, pattern: str, field_type: str,
                             protected_spans: set, pii_mapping: dict) -> str:
        """Replace with reversible tokens."""
        result = text
        offset = 0
        for match in re.finditer(pattern, text):
            is_protected = any(
                match.start() >= s and match.end() <= e
                for s, e in protected_spans
            )
            if not is_protected:
                original = match.group()
                token = _make_token(field_type, original)
                pii_mapping[token] = original

                start = match.start() + offset
                end = match.end() + offset
                result = result[:start] + token + result[end:]
                offset += len(token) - (match.end() - match.start())
        return result


# Singleton
redactor = PIIRedactor()
