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

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# Prompt Templates
# ═══════════════════════════════════════════

TIME_BAR_PROMPT = """You are a GST tax consultant drafting a reply to a time-barred notice.

NOTICE DETAILS:
- Notice Text (first 2000 chars): {notice_text}
- Financial Year: {fy}
- Section: {section}
- Notice Type: {notice_type}
- Demand Amount: ₹{demand_amount}
- Time-Bar Detail: {time_bar_detail}

ENTITIES EXTRACTED:
- GSTINs: {gstins}
- Sections Referenced: {sections}
- Notice Date: {notice_date}

INSTRUCTIONS:
Draft a professional reply that:
1. Opens with a respectful salutation and notice reference
2. States that the notice is time-barred under the applicable limitation period
3. Cites the specific section (73 = 3 years, 74 = 5 years) and the exact date calculation
4. References any CBIC extensions for COVID period if applicable
5. Requests withdrawal/dropping of proceedings
6. Includes a "Without Prejudice" section briefly addressing merits (in case time-bar argument fails)
7. Closes with a prayer for relief

FORMAT:
- Use formal legal language appropriate for a GST tribunal
- Include proper headings (Subject, Reference, Body, Prayer)
- Keep it professional but assertive
- Cite relevant sections of the CGST Act
- Do NOT fabricate case law citations — only cite sections of the Act

Output the complete draft reply text. Do not wrap in JSON.
"""

MERIT_PROMPT = """You are a GST tax consultant drafting a substantive reply to a GST notice.

NOTICE DETAILS:
- Notice Text (first 3000 chars): {notice_text}
- Financial Year: {fy}
- Section: {section}
- Notice Type: {notice_type}
- Demand Amount: ₹{demand_amount}
- Risk Level: {risk_level}
- Risk Reasoning: {risk_reasoning}

ENTITIES:
- GSTINs: {gstins}
- Sections Referenced: {sections}
- Notice Date: {notice_date}
- Response Deadline: {response_deadline}

NOTICE STRUCTURE:
{notice_structure}

RELEVANT CIRCULARS (from knowledge base):
{circulars}

INSTRUCTIONS:
Draft a professional reply that:
1. Opens with respectful salutation, notice reference number, and date
2. Acknowledges receipt of the notice
3. Addresses EACH allegation/demand point raised in the notice, paragraph by paragraph
4. For ITC mismatch: explain possible reasons (timing differences, GSTR-2A/2B reconciliation, supplier default)
5. For demand: challenge the computation if applicable, request detailed working
6. Cite relevant CGST Act sections and circulars from the knowledge base
7. Request personal hearing opportunity under Section 75(4)
8. Include a "Without Prejudice" submission section
9. Close with a prayer for relief (drop proceedings / reduce demand / waive penalty)

RISK-ADJUSTED APPROACH:
- LOW risk: Concise, factual response with standard defenses
- MEDIUM risk: Detailed response addressing each point, request for documents
- HIGH risk: Comprehensive response with multiple defense arguments, request for adjournment if needed

FORMAT:
- Formal legal language appropriate for GST proceedings
- Proper headings (Subject, Reference, Preliminary Submissions, On Merits, Prayer)
- Professional but assertive tone
- Do NOT fabricate case law citations — only cite CGST Act sections and circulars provided
- Include annexure list if supporting documents would strengthen the case

Output the complete draft reply text. Do not wrap in JSON.
"""


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
        llm_data = entities.get("llm_extracted", {})
        if isinstance(llm_data, str):
            try:
                llm_data = json.loads(llm_data)
            except json.JSONDecodeError:
                llm_data = {}

        # Common variables
        gstins = [g.get("value", "") for g in entities.get("GSTIN", [])]
        sections = entities.get("SECTIONS", [])
        fy = llm_data.get("financial_year", "")
        section = sections[0] if sections else ""
        notice_type = llm_data.get("notice_type", "Unknown")
        notice_date = llm_data.get("notice_date", "")
        response_deadline = llm_data.get("response_deadline", "")

        # Parse demand amount
        demand_amount = 0
        raw_demand = llm_data.get("demand_amount")
        if isinstance(raw_demand, dict):
            demand_amount = raw_demand.get("total", 0) or 0
        elif isinstance(raw_demand, (int, float)):
            demand_amount = raw_demand

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
