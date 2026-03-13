"""
TaxShield — Agent 3: Legal Analyst
Performs legal research using RAG, contradiction detection, procedural
defect analysis, and defense strategy building.

Only runs for merit-based cases (not time-barred — those skip to Agent 4).
"""
import json
import logging

from app.llm.router import llm_router
from app.retrieval.hybrid import searcher

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# Prompt Templates
# ═══════════════════════════════════════════

CONTRADICTION_PROMPT = """You are a GST legal analyst. Analyze this notice for internal contradictions, 
inconsistencies, or factual errors that could be used as defense arguments.

NOTICE TEXT (first 3000 chars):
{notice_text}

ENTITIES EXTRACTED:
- Sections: {sections}
- Notice Type: {notice_type}
- Demand Amount: {demand_amount}
- Financial Year: {fy}

NOTICE STRUCTURE:
{notice_structure}

Identify ALL contradictions, for example:
- Section cited vs actual provisions applicable
- Demand computation errors (amounts don't add up)
- Dates inconsistent with the period in question
- Allegation in one paragraph contradicted in another
- Wrong GSTIN or taxpayer details
- Missing mandatory elements (e.g., no DIN, no proper opportunity of hearing)

Return JSON:
{{
    "contradictions": [
        {{
            "type": "SECTION_MISMATCH|COMPUTATION_ERROR|DATE_INCONSISTENCY|FACTUAL_ERROR|MISSING_ELEMENT",
            "description": "...",
            "severity": "HIGH|MEDIUM|LOW",
            "defense_value": "How this can be used in reply"
        }}
    ],
    "overall_notice_quality": "STRONG|MODERATE|WEAK"
}}
"""

PROCEDURAL_DEFECT_PROMPT = """You are a GST procedural law expert. Analyze this notice for procedural defects 
that could invalidate or weaken it.

NOTICE TEXT (first 2000 chars):
{notice_text}

ENTITIES:
- Sections: {sections}
- DINs found: {dins}
- Notice Date: {notice_date}
- Financial Year: {fy}

Check for these procedural defects under CGST Act:
1. **DIN requirement** (Circular 128/47/2019): Every communication must have a DIN. No DIN = invalid.
2. **Proper officer** (Section 2(91)): Was the notice issued by the proper officer?
3. **Opportunity of hearing** (Section 75(4)): Was personal hearing offered before adverse order?
4. **Time limit compliance**: Was the notice issued within the statutory time limit?
5. **Proper service** (Section 169): Was the notice properly served?
6. **Pre-SCN intimation** (Section 73(5)/74(5)): Was pre-notice intimation given?
7. **Demand computation**: Does the notice show detailed computation or just a lump-sum demand?
8. **Reasons recorded**: Are reasons for demand clearly stated?

Return JSON:
{{
    "defects": [
        {{
            "type": "NO_DIN|IMPROPER_OFFICER|NO_HEARING_OFFERED|TIME_LIMIT|SERVICE_DEFECT|NO_INTIMATION|NO_COMPUTATION|NO_REASONS",
            "description": "...",
            "legal_basis": "Section/Circular reference",
            "severity": "FATAL|SERIOUS|MINOR",
            "defense_value": "How to argue this in reply"
        }}
    ],
    "procedural_soundness": "SOUND|QUESTIONABLE|DEFECTIVE"
}}
"""

DEFENSE_STRATEGY_PROMPT = """You are a senior GST consultant building a defense strategy for a client.

NOTICE DETAILS:
- Notice Type: {notice_type}
- Section: {section}
- Financial Year: {fy}
- Demand Amount: ₹{demand_amount}
- Risk Level: {risk_level}

CONTRADICTIONS FOUND:
{contradictions}

PROCEDURAL DEFECTS:
{procedural_defects}

RELEVANT CIRCULARS:
{circulars}

NOTICE TEXT (first 2000 chars):
{notice_text}

Build a defense strategy with:
1. **Primary defense** — Strongest argument (procedural or substantive)
2. **Secondary defenses** — Additional arguments ranked by strength
3. **Documents to request** — What supporting documents the taxpayer should gather
4. **Questions for client** — Key facts to verify with the taxpayer before drafting
5. **Recommended approach** — File reply / Request adjournment / Request PH / Consent to partial demand

Return JSON:
{{
    "primary_defense": {{
        "argument": "...",
        "legal_basis": "Section/Circular",
        "strength": "STRONG|MODERATE|WEAK"
    }},
    "secondary_defenses": [
        {{
            "argument": "...",
            "legal_basis": "...",
            "strength": "STRONG|MODERATE|WEAK"
        }}
    ],
    "documents_needed": ["GSTR-1 for period", "GSTR-3B for period", "..."],
    "client_questions": ["Did you claim the ITC in question?", "..."],
    "recommended_approach": "FILE_REPLY|REQUEST_ADJOURNMENT|REQUEST_PH|PARTIAL_CONSENT",
    "overall_strength": "STRONG|MODERATE|WEAK"
}}
"""


class Agent3Analyst:
    """
    Legal Analyst Agent.

    Runs only for merit-based cases (not time-barred).
    Performs:
    1. Circular/case law search (RAG via hybrid search)
    2. Contradiction detection in the notice
    3. Procedural defect analysis (HIGH risk only)
    4. Defense strategy building
    """

    async def _search_circulars(self, entities: dict, raw_text: str) -> list:
        """Search for relevant circulars and case laws via hybrid search."""
        llm_data = entities.get("llm_extracted", {})
        if isinstance(llm_data, str):
            try:
                llm_data = json.loads(llm_data)
            except json.JSONDecodeError:
                llm_data = {}

        sections = entities.get("SECTIONS", [])
        notice_type = llm_data.get("notice_type", "")
        fy = llm_data.get("financial_year", "")

        # Build multiple search queries for better recall
        queries = [
            f"GST Section {' '.join(sections)} {notice_type}",
            f"CGST circular {notice_type} {fy}",
        ]
        if sections:
            queries.append(f"Section {sections[0]} limitation defense reply")

        all_results = []
        seen_ids = set()

        for query in queries:
            try:
                results = searcher.search(query, top_k=3)
                for r in results:
                    if r["doc_id"] not in seen_ids:
                        seen_ids.add(r["doc_id"])
                        all_results.append(r)
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")

        logger.info(f"Found {len(all_results)} unique circulars/case laws")
        return all_results[:8]  # Cap at 8 results

    async def _detect_contradictions(self, state_dict: dict) -> dict:
        """Use LLM to detect contradictions in the notice."""
        entities = state_dict.get("entities", {})
        llm_data = entities.get("llm_extracted", {})
        if isinstance(llm_data, str):
            try:
                llm_data = json.loads(llm_data)
            except json.JSONDecodeError:
                llm_data = {}

        annotations = state_dict.get("notice_annotations", [])
        notice_structure = "Not available"
        if annotations:
            notice_structure = "\n".join([
                f"- [{a.get('role', 'UNKNOWN')}] {a.get('summary', a.get('text_preview', ''))}"
                for a in annotations[:10]
            ])

        prompt = CONTRADICTION_PROMPT.format(
            notice_text=state_dict.get("raw_text", "")[:3000],
            sections=", ".join(entities.get("SECTIONS", [])) or "Not extracted",
            notice_type=llm_data.get("notice_type", "Unknown"),
            demand_amount=llm_data.get("demand_amount", "Unknown"),
            fy=llm_data.get("financial_year", "Unknown"),
            notice_structure=notice_structure,
        )

        try:
            result = await llm_router.generate(prompt, risk_level="LOW", json_mode=True)
            return json.loads(result) if isinstance(result, str) else result
        except Exception as e:
            logger.error(f"Contradiction detection failed: {e}")
            return {"contradictions": [], "overall_notice_quality": "UNKNOWN"}

    async def _analyze_procedural_defects(self, state_dict: dict) -> dict:
        """Analyze notice for procedural defects (HIGH risk cases)."""
        entities = state_dict.get("entities", {})
        llm_data = entities.get("llm_extracted", {})
        if isinstance(llm_data, str):
            try:
                llm_data = json.loads(llm_data)
            except json.JSONDecodeError:
                llm_data = {}

        dins = [d.get("value", "") for d in entities.get("DIN", [])]

        prompt = PROCEDURAL_DEFECT_PROMPT.format(
            notice_text=state_dict.get("raw_text", "")[:2000],
            sections=", ".join(entities.get("SECTIONS", [])) or "Not extracted",
            dins=", ".join(dins) if dins else "NONE FOUND (potential defect!)",
            notice_date=llm_data.get("notice_date", "Unknown"),
            fy=llm_data.get("financial_year", "Unknown"),
        )

        try:
            result = await llm_router.generate(prompt, risk_level="MEDIUM", json_mode=True)
            return json.loads(result) if isinstance(result, str) else result
        except Exception as e:
            logger.error(f"Procedural defect analysis failed: {e}")
            return {"defects": [], "procedural_soundness": "UNKNOWN"}

    async def _build_defense_strategy(
        self, state_dict: dict, circulars: list,
        contradictions: dict, procedural_defects: dict
    ) -> dict:
        """Build defense strategy combining all findings."""
        entities = state_dict.get("entities", {})
        llm_data = entities.get("llm_extracted", {})
        if isinstance(llm_data, str):
            try:
                llm_data = json.loads(llm_data)
            except json.JSONDecodeError:
                llm_data = {}

        sections = entities.get("SECTIONS", [])

        # Format circulars for prompt
        circulars_text = "No circulars found."
        if circulars:
            circulars_text = "\n\n".join([
                f"[{c['doc_id']}] {c['text'][:400]}"
                for c in circulars
            ])

        # Parse demand amount
        demand_amount = 0
        raw_demand = llm_data.get("demand_amount")
        if isinstance(raw_demand, dict):
            demand_amount = raw_demand.get("total", 0) or 0
        elif isinstance(raw_demand, (int, float)):
            demand_amount = raw_demand

        prompt = DEFENSE_STRATEGY_PROMPT.format(
            notice_type=llm_data.get("notice_type", "Unknown"),
            section=sections[0] if sections else "Unknown",
            fy=llm_data.get("financial_year", "Unknown"),
            demand_amount=f"{demand_amount:,.2f}",
            risk_level=state_dict.get("risk_level", "MEDIUM"),
            contradictions=json.dumps(contradictions.get("contradictions", []), indent=2),
            procedural_defects=json.dumps(procedural_defects.get("defects", []), indent=2),
            circulars=circulars_text,
            notice_text=state_dict.get("raw_text", "")[:2000],
        )

        try:
            result = await llm_router.generate(
                prompt,
                risk_level=state_dict.get("risk_level", "MEDIUM"),
                json_mode=True,
            )
            return json.loads(result) if isinstance(result, str) else result
        except Exception as e:
            logger.error(f"Defense strategy building failed: {e}")
            return {
                "primary_defense": {"argument": "Standard defense", "strength": "WEAK"},
                "secondary_defenses": [],
                "documents_needed": [],
                "client_questions": [],
                "recommended_approach": "FILE_REPLY",
                "overall_strength": "WEAK",
            }

    async def process(self, state_dict: dict) -> dict:
        """
        Main Agent 3 processing. Takes Agent 1+2 output.
        Returns legal analysis for Agent 4.
        """
        logger.info("=== Agent 3: Legal Analyst ===")

        # Check upstream status
        processing_status = state_dict.get("processing_status", "unknown")
        if processing_status == "failed":
            logger.error("Agent 1 failed — skipping legal analysis.")
            return {
                "current_agent": "agent3",
                "retrieved_circulars": [],
                "defense_strategy": "Cannot analyze — document processing failed.",
            }

        risk_level = state_dict.get("risk_level", "MEDIUM")
        entities = state_dict.get("entities", {})
        raw_text = state_dict.get("raw_text", "")

        if not raw_text:
            logger.warning("No text available for legal analysis.")
            return {"current_agent": "agent3", "retrieved_circulars": [], "defense_strategy": ""}

        # ═══ Step 1: Search for relevant circulars ═══
        logger.info("Step 1/4: Searching circulars and case laws...")
        circulars = await self._search_circulars(entities, raw_text)

        # ═══ Step 2: Detect contradictions ═══
        logger.info("Step 2/4: Detecting contradictions...")
        contradictions = await self._detect_contradictions(state_dict)
        contradiction_count = len(contradictions.get("contradictions", []))
        logger.info(
            f"Found {contradiction_count} contradictions. "
            f"Notice quality: {contradictions.get('overall_notice_quality', 'UNKNOWN')}"
        )

        # ═══ Step 3: Procedural defect analysis (MEDIUM + HIGH risk only) ═══
        procedural_defects = {"defects": [], "procedural_soundness": "NOT_ANALYZED"}
        if risk_level in ("MEDIUM", "HIGH"):
            logger.info("Step 3/4: Analyzing procedural defects...")
            procedural_defects = await self._analyze_procedural_defects(state_dict)
            defect_count = len(procedural_defects.get("defects", []))
            logger.info(
                f"Found {defect_count} procedural defects. "
                f"Soundness: {procedural_defects.get('procedural_soundness', 'UNKNOWN')}"
            )
        else:
            logger.info("Step 3/4: Skipping procedural defect analysis (LOW risk)")

        # ═══ Step 4: Build defense strategy ═══
        logger.info("Step 4/4: Building defense strategy...")
        strategy = await self._build_defense_strategy(
            state_dict, circulars, contradictions, procedural_defects
        )
        logger.info(
            f"Defense strategy built. Strength: {strategy.get('overall_strength', 'UNKNOWN')}. "
            f"Approach: {strategy.get('recommended_approach', 'UNKNOWN')}"
        )

        # ═══ Build output ═══
        return {
            "current_agent": "agent3",

            # Circulars for Agent 4 to cite
            "retrieved_circulars": [
                {"doc_id": c["doc_id"], "text": c["text"][:500], "score": c.get("score", 0)}
                for c in circulars
            ],

            # Legal analysis for Agent 4
            "defense_strategy": json.dumps(strategy),

            # Additional analysis (stored in state, available to Agent 4)
            "contradictions": contradictions,
            "procedural_defects": procedural_defects,
            "notice_quality": contradictions.get("overall_notice_quality", "UNKNOWN"),
            "procedural_soundness": procedural_defects.get("procedural_soundness", "NOT_ANALYZED"),
        }


# Singleton
agent3 = Agent3Analyst()
