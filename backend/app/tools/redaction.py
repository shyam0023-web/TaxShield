"""
TaxShield — PII Redaction Tool
In-memory redaction of PAN, Aadhaar, phone, email before LLM sees the text.
DPDP Act compliant — PII never leaves the server.
"""
import re
import logging

logger = logging.getLogger(__name__)


class PIIRedactor:
    """Redacts PII from text. Returns redacted text + list of redacted fields."""
    
    PATTERNS = {
        "PAN": {
            "regex": r'\b[A-Z]{5}\d{4}[A-Z]\b',
            "replacement": "[PAN_REDACTED]"
        },
        "AADHAAR": {
            "regex": r'\b\d{4}\s?\d{4}\s?\d{4}\b',
            "replacement": "[AADHAAR_REDACTED]"
        },
        "PHONE": {
            "regex": r'\b(?:\+91[\-\s]?)?[6-9]\d{9}\b',
            "replacement": "[PHONE_REDACTED]"
        },
        "EMAIL": {
            "regex": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "replacement": "[EMAIL_REDACTED]"
        },
        "BANK_ACCOUNT": {
            "regex": r'\b\d{9,18}\b',  # Conservative — only in banking context
            "replacement": "[BANK_REDACTED]"
        }
    }
    
    # Fields to KEEP (not redact) — these are business identifiers, not personal PII
    KEEP_PATTERNS = [
        r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}',  # GSTIN (15 chars)
        r'[A-Z]{3}[A-Z\d]{17}',  # DIN (20 chars)
    ]
    
    def redact(self, text: str) -> dict:
        """
        Redact PII from text.
        Returns: {redacted_text, redacted_fields: [{type, original, position}]}
        """
        redacted_text = text
        redacted_fields = []
        
        # First, mark GSTIN and DIN positions so we don't redact them
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
                # Check if this span is protected (GSTIN/DIN)
                is_protected = any(
                    match.start() >= s and match.end() <= e 
                    for s, e in protected_spans
                )
                
                if not is_protected:
                    redacted_fields.append({
                        "type": field_type,
                        "original_length": len(match.group()),
                        "position": match.start()
                    })
            
            # Do the actual replacement (skip protected)
            if field_type != "BANK_ACCOUNT" or ("bank" in text.lower() or "account" in text.lower()):
                redacted_text = self._replace_unprotected(
                    redacted_text, config["regex"], config["replacement"], protected_spans
                )
        
        logger.info(f"Redacted {len(redacted_fields)} PII fields: {[f['type'] for f in redacted_fields]}")
        
        return {
            "redacted_text": redacted_text,
            "redacted_fields": redacted_fields,
            "pii_found": len(redacted_fields) > 0
        }
    
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


# Singleton
redactor = PIIRedactor()
