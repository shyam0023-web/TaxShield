"""
TaxShield — WISC Context Selectors & Compressors
Each agent gets ONLY the state fields it needs. No more, no less.

Includes:
- build_*_context(): Select fields per agent (WISC Select)
- compress_agent3_output(): LLM summarization at Agent 3→4 handoff (WISC Compress)
- apply_priority_trimming(): P0-P3 field clearing (WISC Compress)
"""
import json
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# WISC Priority Levels
# ═══════════════════════════════════════════
# P0 (never removed):  System prompt, agent instructions
# P1 (compress last):  entity_summary, risk_level, draft, time_bar_status
# P2 (compress early): Full contradiction JSON, procedural defects detail
# P3 (clear first):    Raw OCR text beyond budget, full RAG scores, FAISS distances


# ═══════════════════════════════════════════
# COMPRESSION: LLM Summarization
# ═══════════════════════════════════════════

from app.agents.prompt_loader import load_prompt

SUMMARIZE_DEFENSE_PROMPT = load_prompt("summarize_defense.md")


async def compress_agent3_output(state: dict) -> dict:
    """
    WISC Compress: Summarize Agent 3's defense strategy via LLM before Agent 4.
    
    Reduces defense_strategy from ~800 tokens (full JSON) to ~150 tokens (summary).
    Also applies P2/P3 priority trimming to clear noise fields.
    
    Returns a dict of state updates to merge back into pipeline state.
    """
    defense_strategy = state.get("defense_strategy", "")
    
    if not defense_strategy or defense_strategy == "Cannot analyze — document processing failed.":
        logger.info("Compress: No defense strategy to summarize.")
        return {}
    
    # Parse defense strategy JSON
    try:
        if isinstance(defense_strategy, str):
            strategy_data = json.loads(defense_strategy)
        else:
            strategy_data = defense_strategy
    except (json.JSONDecodeError, TypeError):
        logger.warning("Compress: Defense strategy is not valid JSON, keeping as-is.")
        return {}
    
    original_len = len(defense_strategy) if isinstance(defense_strategy, str) else len(json.dumps(strategy_data))
    
    # LLM summarization
    try:
        from app.llm.router import llm_router
        
        prompt = SUMMARIZE_DEFENSE_PROMPT.format(
            defense_json=json.dumps(strategy_data, indent=2)[:2000]
        )
        
        summary = await llm_router.generate(prompt, risk_level="LOW")
        compressed_len = len(summary)
        
        reduction = round((1 - compressed_len / max(original_len, 1)) * 100)
        logger.info(
            f"Compress: Defense strategy {original_len} → {compressed_len} chars "
            f"({reduction}% reduction)"
        )
        
        return {"defense_strategy": summary}
        
    except Exception as e:
        logger.warning(f"Compress: LLM summarization failed, keeping original: {e}")
        return {}


def apply_priority_trimming(state: dict) -> dict:
    """
    WISC Compress: Clear P3 fields and compress P2 fields.
    
    Called before building Agent 4's context to reduce noise.
    Returns a cleaned copy of the state — does NOT mutate the original.
    
    P3 (clear):
    - raw_text beyond 3000 chars (Agent 4 prompt uses max 3000)
    - Full RAG result scores/metadata
    - notice_annotations beyond first 10 items
    
    P2 (compress):
    - contradictions: keep only summary, drop per-item detail
    - procedural_defects: keep only summary, drop per-item detail
    """
    trimmed = dict(state)
    
    # ─── P3: Clear noise fields ───
    raw_text = trimmed.get("raw_text", "")
    if len(raw_text) > 3000:
        trimmed["raw_text"] = raw_text[:3000]
        logger.debug(f"P3 trim: raw_text {len(raw_text)} → 3000 chars")
    
    # Trim circular text to key_ruling length (~100 chars each)
    circulars = trimmed.get("retrieved_circulars", [])
    if circulars:
        trimmed["retrieved_circulars"] = [
            {"doc_id": c.get("doc_id", ""), "text": c.get("text", "")[:300]}
            for c in circulars
        ]
        logger.debug(f"P3 trim: {len(circulars)} circulars trimmed to 300 chars each")
    
    # Trim annotations to first 10
    annotations = trimmed.get("notice_annotations", [])
    if len(annotations) > 10:
        trimmed["notice_annotations"] = annotations[:10]
        logger.debug(f"P3 trim: annotations {len(annotations)} → 10")
    
    # ─── P2: Compress detail fields to summaries ───
    contradictions = trimmed.get("contradictions", {})
    if isinstance(contradictions, dict) and contradictions.get("contradictions"):
        items = contradictions["contradictions"]
        summary = f"{len(items)} contradictions found. Quality: {contradictions.get('overall_notice_quality', 'UNKNOWN')}. "
        summary += "Key issues: " + "; ".join(
            item.get("description", "")[:80] for item in items[:3]
        )
        trimmed["contradictions"] = {"summary": summary}
        logger.debug(f"P2 compress: contradictions {len(items)} items → summary string")
    
    return trimmed


# ═══════════════════════════════════════════
# SELECT: Per-Agent Context Builders
# ═══════════════════════════════════════════

def build_agent2_context(state: dict) -> dict:
    """
    Agent 2 (Risk Router) needs:
    - processing_status: to check if Agent 1 succeeded
    - entities: for section-aware time-bar + risk classification
    - raw_text: first 1000 chars for risk classification prompt
    - time_bar: Agent 1's preliminary time-bar flag
    """
    ctx = {
        "processing_status": state.get("processing_status", "unknown"),
        "entities": state.get("entities", {}),
        "raw_text": state.get("raw_text", ""),
        "time_bar": state.get("time_bar", {}),
    }
    logger.debug(
        f"Agent 2 context: {len(ctx)} fields, "
        f"raw_text={len(ctx['raw_text'])} chars"
    )
    return ctx


def build_agent3_context(state: dict) -> dict:
    """
    Agent 3 (Legal Analyst) needs:
    - processing_status: to check upstream health
    - entities: for circular search queries + contradiction detection
    - raw_text: first 3000 chars for LLM analysis prompts
    - notice_annotations: paragraph roles for contradiction detection
    - risk_level: determines which analyses to run (procedural = MEDIUM+HIGH only)
    """
    ctx = {
        "processing_status": state.get("processing_status", "unknown"),
        "entities": state.get("entities", {}),
        "raw_text": state.get("raw_text", ""),
        "notice_annotations": state.get("notice_annotations", []),
        "risk_level": state.get("risk_level", "MEDIUM"),
    }
    logger.debug(
        f"Agent 3 context: {len(ctx)} fields, "
        f"raw_text={len(ctx['raw_text'])} chars"
    )
    return ctx


def build_agent4_context(state: dict) -> dict:
    """
    Agent 4 (Master Drafter) — receives COMPRESSED state.
    
    Called AFTER compress_agent3_output() and apply_priority_trimming().
    - defense_strategy: LLM-summarized (~150 tokens, not ~800)
    - contradictions: P2-compressed to summary string
    - raw_text: P3-trimmed to 3000 chars
    - retrieved_circulars: P3-trimmed to 300 chars each
    """
    ctx = {
        "processing_status": state.get("processing_status", "unknown"),
        "entities": state.get("entities", {}),
        "raw_text": state.get("raw_text", ""),
        "notice_annotations": state.get("notice_annotations", []),
        "risk_level": state.get("risk_level", "MEDIUM"),
        "risk_reasoning": state.get("risk_reasoning", ""),
        "is_time_barred": state.get("is_time_barred", False),
        "time_bar_detail": state.get("time_bar_detail", {}),
        "retrieved_circulars": state.get("retrieved_circulars", []),
        "defense_strategy": state.get("defense_strategy", ""),
        "contradictions": state.get("contradictions", {}),
        "user_instructions": state.get("user_instructions", ""),
    }
    logger.debug(
        f"Agent 4 context: {len(ctx)} fields, "
        f"raw_text={len(ctx['raw_text'])} chars, "
        f"circulars={len(ctx['retrieved_circulars'])}, "
        f"defense_strategy={len(str(ctx['defense_strategy']))} chars"
    )
    return ctx


def build_agent5_context(state: dict) -> dict:
    """
    Agent 5 (InEx Verifier) needs:
    - entities: to cross-check entity values in the draft
    - raw_text: truncated to 1500 chars as notice summary for adversarial prompt
    - retrieved_circulars: to verify cited circulars exist in KB
    - draft_reply: the draft to verify
    """
    ctx = {
        "entities": state.get("entities", {}),
        "raw_text": state.get("raw_text", "")[:1500],
        "retrieved_circulars": state.get("retrieved_circulars", []),
        "draft_reply": state.get("draft_reply", ""),
    }
    logger.debug(
        f"Agent 5 context: {len(ctx)} fields, "
        f"raw_text={len(ctx['raw_text'])} chars, "
        f"draft={len(ctx['draft_reply'])} chars"
    )
    return ctx

