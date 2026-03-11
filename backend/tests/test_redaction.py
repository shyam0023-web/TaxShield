"""
Tests for PII Redaction (app.tools.redaction)
Pure-logic tests — no LLM calls needed.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.tools.redaction import redactor


class TestPIIRedactor:
    """Tests for PIIRedactor.redact()"""

    # ═══ PAN Detection ═══

    def test_redacts_pan(self):
        text = "The taxpayer's PAN is ABCDE1234F and the amount is due."
        result = redactor.redact(text)
        assert "[PAN_REDACTED]" in result["redacted_text"]
        assert "ABCDE1234F" not in result["redacted_text"]
        assert result["pii_found"] is True

    def test_redacts_multiple_pans(self):
        text = "PAN: ABCDE1234F and XYZAB5678C"
        result = redactor.redact(text)
        assert result["redacted_text"].count("[PAN_REDACTED]") == 2

    # ═══ Aadhaar Detection ═══

    def test_redacts_aadhaar_no_spaces(self):
        text = "Aadhaar: 123456789012"
        result = redactor.redact(text)
        assert "[AADHAAR_REDACTED]" in result["redacted_text"]
        assert "123456789012" not in result["redacted_text"]

    def test_redacts_aadhaar_with_spaces(self):
        text = "Aadhaar: 1234 5678 9012"
        result = redactor.redact(text)
        assert "[AADHAAR_REDACTED]" in result["redacted_text"]

    # ═══ Phone Detection ═══

    def test_redacts_phone(self):
        text = "Contact: 9876543210"
        result = redactor.redact(text)
        assert "[PHONE_REDACTED]" in result["redacted_text"]
        assert "9876543210" not in result["redacted_text"]

    def test_redacts_phone_with_country_code(self):
        text = "Contact: +91 9876543210"
        result = redactor.redact(text)
        assert "[PHONE_REDACTED]" in result["redacted_text"]

    # ═══ Email Detection ═══

    def test_redacts_email(self):
        text = "Email: taxpayer@example.com for correspondence"
        result = redactor.redact(text)
        assert "[EMAIL_REDACTED]" in result["redacted_text"]
        assert "taxpayer@example.com" not in result["redacted_text"]

    # ═══ GSTIN Protection (should NOT be redacted) ═══

    def test_preserves_gstin(self):
        """GSTIN is a business identifier, not PII — should NOT be redacted"""
        text = "GSTIN: 27AAPFU0939F1ZV is registered"
        result = redactor.redact(text)
        # GSTIN contains a PAN-like substring, but should be protected
        assert "27AAPFU0939F1ZV" in result["redacted_text"]

    def test_preserves_din(self):
        """DIN is a business identifier — should NOT be redacted"""
        text = "DIN: ITBA012345678901234A issued by department"
        result = redactor.redact(text)
        assert "ITBA012345678901234A" in result["redacted_text"]

    # ═══ Bank Account (context-dependent) ═══

    def test_redacts_bank_account_in_banking_context(self):
        """Bank account numbers should only be redacted when banking context present"""
        text = "Please deposit to bank account 123456789012345"
        result = redactor.redact(text)
        assert "[BANK_REDACTED]" in result["redacted_text"]

    def test_no_bank_redaction_without_context(self):
        """Numbers should NOT be redacted as bank account without banking context"""
        text = "The amount is 123456789012345 units"
        result = redactor.redact(text)
        assert "[BANK_REDACTED]" not in result["redacted_text"]

    # ═══ No PII ═══

    def test_no_pii_returns_clean(self):
        text = "This is a plain notice with no personal information."
        result = redactor.redact(text)
        assert result["redacted_text"] == text
        assert result["pii_found"] is False
        assert len(result["redacted_fields"]) == 0

    # ═══ Mixed PII ═══

    def test_mixed_pii_types(self):
        text = "PAN: ABCDE1234F, Phone: 9876543210, Email: test@example.com"
        result = redactor.redact(text)
        assert "[PAN_REDACTED]" in result["redacted_text"]
        assert "[PHONE_REDACTED]" in result["redacted_text"]
        assert "[EMAIL_REDACTED]" in result["redacted_text"]
        assert len(result["redacted_fields"]) >= 3

    # ═══ Output Structure ═══

    def test_output_has_required_fields(self):
        result = redactor.redact("Any text")
        assert "redacted_text" in result
        assert "redacted_fields" in result
        assert "pii_found" in result
