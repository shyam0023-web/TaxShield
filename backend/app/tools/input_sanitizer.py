"""
TaxShield — Input Sanitizer
Strips prompt injection attempts and invisible characters from OCR text.
"""
import re
import logging

logger = logging.getLogger(__name__)


class InputSanitizer:
    """Defense against prompt injection in OCR-extracted text."""
    
    # Patterns that indicate prompt injection
    INJECTION_PATTERNS = [
        r'ignore\s+(previous|above|all)\s+instructions',
        r'you\s+are\s+now\s+',
        r'system\s*:\s*',
        r'<\s*/?script',
        r'```\s*system',
        r'forget\s+(everything|all)',
        r'new\s+instruction',
        r'override\s+',
        r'act\s+as\s+',
        r'pretend\s+',
    ]
    
    # Zero-width and invisible characters
    INVISIBLE_CHARS = re.compile(
        r'[\u200b\u200c\u200d\u2060\ufeff\u00ad\u200e\u200f]'
    )
    
    def sanitize(self, text: str) -> dict:
        """
        Clean text from potential prompt injections.
        Returns: {sanitized_text, injections_found: int, flags: list}
        """
        flags = []
        
        # Strip invisible characters
        clean_text = self.INVISIBLE_CHARS.sub('', text)
        invisible_count = len(text) - len(clean_text)
        if invisible_count > 0:
            flags.append(f"Removed {invisible_count} invisible characters")
        
        # Strip excessive whitespace (hidden text technique)
        clean_text = re.sub(r'\s{10,}', ' ', clean_text)
        
        # Check for injection patterns
        injections_found = 0
        for pattern in self.INJECTION_PATTERNS:
            matches = re.findall(pattern, clean_text, re.IGNORECASE)
            if matches:
                injections_found += len(matches)
                clean_text = re.sub(pattern, '[SANITIZED]', clean_text, flags=re.IGNORECASE)
                flags.append(f"Sanitized injection pattern: {pattern[:30]}...")
        
        if injections_found > 0:
            logger.warning(f"Found {injections_found} potential injection attempts")
        
        return {
            "sanitized_text": clean_text.strip(),
            "injections_found": injections_found,
            "flags": flags
        }


# Singleton
sanitizer = InputSanitizer()
