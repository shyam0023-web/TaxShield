"""
TaxShield — Shared Regex Patterns
Single source of truth for all GST-related regex patterns.
Used by: OCR, NER, Redaction, and any future tools.
"""
import re

# ═══ GST Entity Patterns ═══
GSTIN_PATTERN = r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}'
DIN_PATTERN = r'[A-Z]{3}[A-Z\d]{17}'  # 20-char DIN format
SECTION_PATTERN = r'[Ss]ection\s+(\d+[A-Za-z]*(?:\(\d+\))*)'
PAN_PATTERN = r'[A-Z]{5}\d{4}[A-Z]{1}'
AMOUNT_PATTERN = r'₹?\s*[\d,]+\.?\d*'
NOTICE_NUMBER_PATTERN = r'(?i)notice\s+no\.?\s*[:\-]?\s*([A-Z0-9\-/]+)'

# ═══ Date Patterns ═══
DATE_PATTERNS = [
    r'\b\d{2}-\d{2}-\d{4}\b',       # DD-MM-YYYY
    r'\b\d{2}/\d{2}/\d{4}\b',       # DD/MM/YYYY
    r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',  # DD Month YYYY
]

# ═══ PII Patterns (for redaction) ═══
PII_PATTERNS = {
    "PAN": {
        "regex": PAN_PATTERN,
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
        "regex": r'\b\d{9,18}\b',
        "replacement": "[BANK_REDACTED]"
    },
}

# ═══ Business Identifiers to KEEP (not redact) ═══
KEEP_PATTERNS = [GSTIN_PATTERN, DIN_PATTERN]

# ═══ Compiled versions for performance ═══
GSTIN_RE = re.compile(GSTIN_PATTERN)
DIN_RE = re.compile(DIN_PATTERN)
SECTION_RE = re.compile(SECTION_PATTERN)
PAN_RE = re.compile(PAN_PATTERN)
AMOUNT_RE = re.compile(AMOUNT_PATTERN)
