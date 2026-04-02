"""
TaxShield — Agent 4: Master Drafter
Generates a professional GST notice reply using pipeline output.

Handles two paths:
1. Time-barred notices → Strong procedural defense citing limitation period
2. Merit-based notices → Substantive defense using entities, risk, and circulars
"""
import json
import logging

from app.llm.router import llm_router
from app.retrieval.hybrid import searcher
from app.agents.prompt_loader import load_prompt
from app.utils import parse_llm_extracted, parse_demand_amount

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# Load prompts from markdown files (WISC: procedural memory)
# ═══════════════════════════════════════════

TIME_BAR_PROMPT = load_prompt("draft_time_barred.md")
MERIT_PROMPT = load_prompt("draft_merit.md")


class Agent4Drafter:
    """
    Master Drafter Agent.
    
    Takes pipeline state and generates a professional GST notice reply.
    Uses Gemini Pro for HIGH risk, Gemini Flash for LOW/MEDIUM.
    """

    async def process(self, state_dict: dict) -> dict:
        """Generate draft reply from pipeline state."""
        logger.info("=== Agent 4: Master Drafter ===")

        # Check upstream status
        processing_status = state_dict.get("processing_status", "unknown")
        if processing_status == "failed":
            logger.error("Cannot draft — Agent 1 failed. No text available.")
            return {
                "current_agent": "agent4",
                "draft_reply": "",
                "draft_error": "Cannot generate draft — document processing failed",
            }

        risk_level = state_dict.get("risk_level", "UNKNOWN")
        if risk_level == "UNKNOWN":
            logger.warning("Risk level is UNKNOWN — proceeding with MEDIUM defaults")
            risk_level = "MEDIUM"

        # Extract fields from state
        raw_text = state_dict.get("raw_text", "")
        entities = state_dict.get("entities", {})
        is_time_barred = state_dict.get("is_time_barred", False)
        time_bar_detail = state_dict.get("time_bar_detail", {})

        # Parse LLM-extracted entities
        llm_data = parse_llm_extracted(entities)

        # Common variables
        gstins = [g.get("value", "") for g in entities.get("GSTIN", [])]
        sections = entities.get("SECTIONS", [])
        fy = llm_data.get("financial_year", "")
        section = sections[0] if sections else ""
        notice_type = llm_data.get("notice_type", "Unknown")
        notice_date = llm_data.get("notice_date", "")
        response_deadline = llm_data.get("response_deadline", "")

        # Parse demand amount
        demand_amount = parse_demand_amount(llm_data)

        # ═══ Retrieve relevant circulars ═══
        # Prefer Agent 3's pre-fetched results if available
        retrieved_circulars = state_dict.get("retrieved_circulars", [])
        if retrieved_circulars:
            logger.info(f"Using {len(retrieved_circulars)} circulars from Agent 3")
            circulars_text = "\n\n".join([
                f"[{r['doc_id']}] {r['text'][:500]}"
                for r in retrieved_circulars
            ])
        else:
            circulars_text = "No circulars found in knowledge base."
            try:
                query = f"GST Section {section} {notice_type} {fy}"
                results = searcher.search(query, top_k=3)
                if results:
                    circulars_text = "\n\n".join([
                        f"[{r['doc_id']}] {r['text'][:500]}"
                        for r in results
                    ])
            except Exception as e:
                logger.warning(f"Circular search failed (non-fatal): {e}")

        # ═══ Build notice structure summary ═══
        annotations = state_dict.get("notice_annotations", [])
        notice_structure = "Not available"
        if annotations:
            notice_structure = "\n".join([
                f"- [{a.get('role', 'UNKNOWN')}] {a.get('summary', a.get('text_preview', ''))}"
                for a in annotations[:10]
            ])

        # ═══ Integrate Agent 3 defense analysis (if available) ═══
        defense_strategy_text = ""
        defense_strategy = state_dict.get("defense_strategy", "")
        contradictions = state_dict.get("contradictions", {})
        if defense_strategy:
            defense_strategy_text = f"\n\nDEFENSE STRATEGY FROM LEGAL ANALYST:\n{defense_strategy}"
        if contradictions and contradictions.get("contradictions"):
            defense_strategy_text += f"\n\nCONTRADICTIONS FOUND IN NOTICE:\n{json.dumps(contradictions['contradictions'], indent=2)}"

        # ═══ Select prompt and generate ═══
        if is_time_barred:
            logger.info("Drafting TIME-BARRED defense")
            prompt = TIME_BAR_PROMPT.format(
                notice_text=raw_text[:2000],
                fy=fy,
                section=section,
                notice_type=notice_type,
                demand_amount=f"{demand_amount:,.2f}",
                time_bar_detail=json.dumps(time_bar_detail, indent=2) if time_bar_detail else "Not available",
                gstins=", ".join(gstins) or "Not extracted",
                sections=", ".join(sections) or "Not extracted",
                notice_date=notice_date or "Not extracted",
            )
        else:
            logger.info(f"Drafting MERIT-BASED defense (risk={risk_level})")
            prompt = MERIT_PROMPT.format(
                notice_text=raw_text[:3000],
                fy=fy,
                section=section,
                notice_type=notice_type,
                demand_amount=f"{demand_amount:,.2f}",
                risk_level=risk_level,
                risk_reasoning=state_dict.get("risk_reasoning", "No reasoning provided"),
                gstins=", ".join(gstins) or "Not extracted",
                sections=", ".join(sections) or "Not extracted",
                notice_date=notice_date or "Not extracted",
                response_deadline=response_deadline or "Not specified",
                notice_structure=notice_structure,
                circulars=circulars_text,
            )
            # Append Agent 3's analysis if available
            if defense_strategy_text:
                prompt += defense_strategy_text

        try:
            draft_reply = await llm_router.generate(
                prompt,
                risk_level=risk_level,
            )
            logger.info(f"Draft generated: {len(draft_reply)} chars")
        except Exception as e:
            logger.error(f"Draft generation failed: {e}")
            return {
                "current_agent": "agent4",
                "draft_reply": "",
                "draft_error": f"LLM generation failed: {str(e)}",
            }

        return {
            "current_agent": "agent4",
            "draft_reply": draft_reply,
            "draft_type": "time_barred" if is_time_barred else "merit_based",
        }


# Singleton
agent4 = Agent4Drafter()
