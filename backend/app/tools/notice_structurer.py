"""
TaxShield — Notice Structurer
Annotates each paragraph with a role: HEADER, FACTS, DEMAND, PENALTY, PRAYER, PROCEDURE
"""
from app.llm.router import llm_router
import json
import logging

logger = logging.getLogger(__name__)


class NoticeStructurer:
    """Break notice into annotated paragraphs with roles."""
    
    async def structure_notice(self, text: str) -> list:
        """
        Classify each paragraph into roles.
        Returns: list of {paragraph, text_preview, role, summary}
        """
        try:
            prompt = f"""Analyze this GST tax notice and classify each paragraph into roles.

Return a JSON array:
[
    {{
        "paragraph": 1,
        "text_preview": "first 80 chars...",
        "role": "HEADER",
        "summary": "one line summary"
    }}
]

Roles (pick exactly one per paragraph):
- HEADER: Notice number, date, addresses, reference, subject line
- FACTS: What the department found or alleges (e.g., ITC mismatch, turnover discrepancy)
- DEMAND: Tax amount demanded, breakdown of IGST/CGST/SGST/Cess
- PENALTY: Penalty imposed or proposed under specific sections
- INTEREST: Interest calculation details
- PRAYER: What the department wants (appear, pay, respond, show cause)
- PROCEDURE: Hearing dates, submission requirements, timelines
- LEGAL_BASIS: Sections of CGST/SGST Act cited as authority
- OTHER: Anything else

Notice text:
{text[:4000]}"""
            
            result = await llm_router.generate(prompt, risk_level="LOW")
            
            try:
                annotations = json.loads(result)
                logger.info(f"Structured notice into {len(annotations)} paragraphs")
                return annotations
            except json.JSONDecodeError:
                logger.warning("Failed to parse structure as JSON, returning raw")
                return [{"paragraph": 1, "text_preview": text[:80], "role": "UNKNOWN", "summary": "Parse failed"}]
                
        except Exception as e:
            logger.error(f"Notice structuring failed: {e}")
            return [{"paragraph": 1, "text_preview": text[:80], "role": "UNKNOWN", "summary": str(e)}]


# Singleton
structurer = NoticeStructurer()
