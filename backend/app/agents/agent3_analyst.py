"""
TaxShield — Agent 3: Legal Analyst
Performs legal research using RAG, contradiction detection, procedural
defect analysis, and defense strategy building.

WISC Isolation: Sub-tasks run in parallel via asyncio.gather() with
isolated context dicts. Only defense strategy depends on prior results.

Only runs for merit-based cases (not time-barred — those skip to Agent 4).
"""
import asyncio
import json
import logging

from app.llm.router import llm_router
from app.retrieval.hybrid import searcher
from app.retrieval.section_kb import section_kb
from app.agents.prompt_loader import load_prompt
from app.utils import parse_llm_extracted, parse_demand_amount

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# Load prompts from markdown files (WISC: procedural memory)
# ═══════════════════════════════════════════

CONTRADICTION_PROMPT = load_prompt("contradiction.md")
PROCEDURAL_DEFECT_PROMPT = load_prompt("procedural_defect.md")
DEFENSE_STRATEGY_PROMPT = load_prompt("defense_strategy.md")


# ═══════════════════════════════════════════
# WISC: Isolated context builders for sub-tasks
# ═══════════════════════════════════════════

def _build_contradiction_context(state: dict) -> dict:
    """Isolated context for contradiction detection sub-task."""
    return {
        "entities": state.get("entities", {}),
        "raw_text": state.get("raw_text", "")[:3000],
        "notice_annotations": state.get("notice_annotations", []),
    }


def _build_procedural_context(state: dict) -> dict:
    """Isolated context for procedural defect sub-task."""
    return {
        "entities": state.get("entities", {}),
        "raw_text": state.get("raw_text", "")[:2000],
    }


def _build_defense_context(state: dict) -> dict:
    """Isolated context for defense strategy sub-task."""
    return {
        "entities": state.get("entities", {}),
        "raw_text": state.get("raw_text", "")[:2000],
        "risk_level": state.get("risk_level", "MEDIUM"),
    }


class Agent3Analyst:
    """
    Legal Analyst Agent.

    Runs only for merit-based cases (not time-barred).

    WISC Fan-Out Pattern:
      Step 1 (search) + Step 2 (contradictions) + Step 3 (defects) → parallel
      Step 4 (defense strategy) → sequential (depends on 1+2+3)

    Each sub-task gets its own isolated context dict.
    """

    async def _search_circulars(self, entities: dict, raw_text: str) -> list:
        """2-tier search: curated section KB (primary) → FAISS hybrid (fallback).
        WISC: Section-select is ~0.1ms; FAISS is ~5ms fallback."""
        llm_data = parse_llm_extracted(entities)

        sections = entities.get("SECTIONS", [])
        notice_type = llm_data.get("notice_type", "")
        fy = llm_data.get("financial_year", "")

        # ═══ Tier 1: Curated Section KB (primary, ~0.1ms) ═══
        kb_results = []
        if sections:
            kb_results = section_kb.search_by_sections(sections)
            logger.info(f"Section KB: {len(kb_results)} results for sections {sections}")

        # Always check DIN circular (procedural defense)
        din_results = section_kb.search_din()
        for r in din_results:
            if r["doc_id"] not in {x["doc_id"] for x in kb_results}:
                kb_results.append(r)

        # Also fetch Section 75 (procedural requirements) for demand notices
        if notice_type.upper() in ("SCN", "DEMAND", "SHOW CAUSE NOTICE", "DEMAND ORDER"):
            s75 = section_kb.search_by_section("75")
            for r in s75:
                if r["doc_id"] not in {x["doc_id"] for x in kb_results}:
                    kb_results.append(r)

        if kb_results:
            logger.info(f"Curated KB returned {len(kb_results)} entries — skipping FAISS")
            return kb_results[:8]

        # ═══ Tier 2: FAISS Hybrid Search (fallback, ~5ms) ═══
        logger.info("No section KB match — falling back to FAISS hybrid search")
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
                logger.warning(f"FAISS search failed for query '{query}': {e}")

        logger.info(f"FAISS fallback: {len(all_results)} unique results")
        return all_results[:8]

    async def _detect_contradictions(self, ctx: dict) -> dict:
        """Use LLM to detect contradictions in the notice.
        WISC: Receives isolated context (entities, raw_text, notice_annotations)."""
        entities = ctx.get("entities", {})
        llm_data = parse_llm_extracted(entities)

        annotations = ctx.get("notice_annotations", [])
        notice_structure = "Not available"
        if annotations:
            notice_structure = "\n".join([
                f"- [{a.get('role', 'UNKNOWN')}] {a.get('summary', a.get('text_preview', ''))}"
                for a in annotations[:10]
            ])

        prompt = CONTRADICTION_PROMPT.format(
            notice_text=ctx.get("raw_text", "")[:3000],
            sections=", ".join(entities.get("SECTIONS", [])) or "Not extracted",
            notice_type=llm_data.get("notice_type", "Unknown"),
            demand_amount=llm_data.get("demand_amount", "Unknown"),
            fy=llm_data.get("financial_year", "Unknown"),
            notice_structure=notice_structure,
        )

        try:
            result = await llm_router.generate(prompt, risk_level="LOW", json_mode=True, model_type="instant")
            return json.loads(result) if isinstance(result, str) else result
        except Exception as e:
            logger.error(f"Contradiction detection failed: {e}")
            return {"contradictions": [], "overall_notice_quality": "UNKNOWN"}

    async def _analyze_procedural_defects(self, ctx: dict) -> dict:
        """Analyze notice for procedural defects.
        WISC: Receives isolated context (entities, raw_text)."""
        entities = ctx.get("entities", {})
        llm_data = parse_llm_extracted(entities)

        dins = [d.get("value", "") for d in entities.get("DIN", [])]

        prompt = PROCEDURAL_DEFECT_PROMPT.format(
            notice_text=ctx.get("raw_text", "")[:2000],
            sections=", ".join(entities.get("SECTIONS", [])) or "Not extracted",
            dins=", ".join(dins) if dins else "NONE FOUND (potential defect!)",
            notice_date=llm_data.get("notice_date", "Unknown"),
            fy=llm_data.get("financial_year", "Unknown"),
        )

        try:
            result = await llm_router.generate(prompt, risk_level="MEDIUM", json_mode=True, model_type="instant")
            return json.loads(result) if isinstance(result, str) else result
        except Exception as e:
            logger.error(f"Procedural defect analysis failed: {e}")
            return {"defects": [], "procedural_soundness": "UNKNOWN"}

    async def _build_defense_strategy(
        self, ctx: dict, circulars: list,
        contradictions: dict, procedural_defects: dict
    ) -> dict:
        """Build defense strategy combining all findings.
        WISC: Receives isolated context (entities, raw_text, risk_level)."""
        entities = ctx.get("entities", {})
        llm_data = parse_llm_extracted(entities)

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
            risk_level=ctx.get("risk_level", "MEDIUM"),
            contradictions=json.dumps(contradictions.get("contradictions", []), indent=2),
            procedural_defects=json.dumps(procedural_defects.get("defects", []), indent=2),
            circulars=circulars_text,
            notice_text=ctx.get("raw_text", "")[:2000],
        )

        try:
            result = await llm_router.generate(
                prompt,
                risk_level=ctx.get("risk_level", "MEDIUM"),
                json_mode=True,
                model_type="instant"
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
        Main Agent 3 processing. Takes Agent 1+2 output (via WISC selector).
        Returns legal analysis for Agent 4.

        WISC Fan-Out: Steps 1-3 run in parallel, Step 4 runs after.
        """
        logger.info("=== Agent 3: Legal Analyst (WISC Fan-Out) ===")

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

        # ═══════════════════════════════════════════
        # WISC Fan-Out: Run independent sub-tasks in parallel
        # Each gets its own isolated context dict
        # ═══════════════════════════════════════════

        # Build isolated contexts for each sub-task
        contradiction_ctx = _build_contradiction_context(state_dict)
        procedural_ctx = _build_procedural_context(state_dict)

        # Determine which tasks to run in parallel
        parallel_tasks = [
            self._search_circulars(entities, raw_text),
            self._detect_contradictions(contradiction_ctx),
        ]

        run_procedural = risk_level in ("MEDIUM", "HIGH")
        if run_procedural:
            parallel_tasks.append(self._analyze_procedural_defects(procedural_ctx))

        logger.info(
            f"Fan-out: Running {len(parallel_tasks)} sub-tasks sequentially to avoid rate limits..."
        )

        # ═══ Execute sub-tasks sequentially ═══
        results = []
        for task in parallel_tasks:
            try:
                res = await task
                results.append(res)
            except Exception as e:
                results.append(e)

        # Unpack results (handle exceptions gracefully)
        circulars = results[0] if not isinstance(results[0], Exception) else []
        contradictions = results[1] if not isinstance(results[1], Exception) else {
            "contradictions": [], "overall_notice_quality": "UNKNOWN"
        }

        procedural_defects = {"defects": [], "procedural_soundness": "NOT_ANALYZED"}
        if run_procedural:
            procedural_defects = results[2] if not isinstance(results[2], Exception) else {
                "defects": [], "procedural_soundness": "UNKNOWN"
            }

        # Log parallel results
        if isinstance(results[0], Exception):
            logger.error(f"Circular search failed in fan-out: {results[0]}")
        if isinstance(results[1], Exception):
            logger.error(f"Contradiction detection failed in fan-out: {results[1]}")
        if run_procedural and isinstance(results[2], Exception):
            logger.error(f"Procedural defect analysis failed in fan-out: {results[2]}")

        contradiction_count = len(contradictions.get("contradictions", []))
        logger.info(
            f"Fan-out complete. Circulars: {len(circulars)}, "
            f"Contradictions: {contradiction_count}, "
            f"Notice quality: {contradictions.get('overall_notice_quality', 'UNKNOWN')}"
        )
        if run_procedural:
            defect_count = len(procedural_defects.get("defects", []))
            logger.info(
                f"Procedural defects: {defect_count}, "
                f"Soundness: {procedural_defects.get('procedural_soundness', 'UNKNOWN')}"
            )

        # ═══ Step 4: Build defense strategy (sequential — depends on 1+2+3) ═══
        logger.info("Building defense strategy (sequential — depends on fan-out results)...")
        defense_ctx = _build_defense_context(state_dict)
        strategy = await self._build_defense_strategy(
            defense_ctx, circulars, contradictions, procedural_defects
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
