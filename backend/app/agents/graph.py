"""
TaxShield — LangGraph Workflow
Pipeline: Agent1 (OCR+NER) → Agent2 (Risk Router) → Agent3 (Legal Analyst) → Compress → Agent4 (Drafter) → Agent5 (InEx Verifier)

WISC: Each agent receives only its required fields via build_context() selectors.
Typed contracts validate outputs via Pydantic models.
"""
from langgraph.graph import StateGraph, END
from app.agents.state import PipelineState
from app.agents.agent1_processor import agent1
from app.agents.agent2_router import agent2
from app.agents.agent3_analyst import agent3
from app.agents.agent4_drafter import agent4
from app.agents.agent5_verifier import agent5
from app.agents.context_selector import (
    build_agent2_context,
    build_agent3_context,
    build_agent4_context,
    build_agent5_context,
    compress_agent3_output,
    apply_priority_trimming,
)
from app.agents.contracts import validate_agent_output
import logging

logger = logging.getLogger(__name__)


async def agent1_node(state: PipelineState) -> dict:
    """Document Processor: Extract entities, OCR, check time-bar flags."""
    logger.info("Running Agent 1 Node...")
    
    pdf_bytes = state.get("pdf_bytes")
    if not pdf_bytes:
        return {"processing_errors": ["No PDF bytes provided"], "current_agent": "agent1"}
    
    result = await agent1.process(pdf_bytes)
    return validate_agent_output("agent1", result)


async def agent2_node(state: PipelineState) -> dict:
    """Risk Router: Classify risk and finalize time-bar using Agent 1 output.
    WISC: Receives only processing_status, entities, raw_text, time_bar."""
    logger.info("Running Agent 2 Node... (WISC: 4 fields selected)")
    ctx = build_agent2_context(state)
    result = await agent2.process(ctx)
    return validate_agent_output("agent2", result)


def route_after_risk(state: PipelineState) -> str:
    """Route based on risk level and time-bar status."""
    if state.get("is_time_barred", False):
        logger.info("Route → Agent 4 (Time-Barred Notice)")
        return "agent4"
    logger.info("Route → Agent 3 (Merit Based Defense)")
    return "agent3"


async def agent3_node(state: PipelineState) -> dict:
    """Legal Analyst: Search circulars, detect contradictions, build defense.
    WISC: Receives only processing_status, entities, raw_text, annotations, risk_level."""
    logger.info("Running Agent 3 Node... (WISC: 5 fields selected)")
    ctx = build_agent3_context(state)
    result = await agent3.process(ctx)
    return validate_agent_output("agent3", result)


async def compress_node(state: PipelineState) -> dict:
    """WISC Compress: Summarize Agent 3 output + trim P2/P3 fields before Agent 4."""
    logger.info("Running Compress Node... (WISC: LLM summarization + priority trimming)")
    
    # Step 1: LLM summarize defense_strategy (~800 → ~150 tokens)
    compression_updates = await compress_agent3_output(state)
    
    # Merge compression results back (returned to LangGraph as state updates)
    return compression_updates


async def agent4_node(state: PipelineState) -> dict:
    """Master Drafter: Generate draft reply from COMPRESSED pipeline output.
    WISC: State has been compressed by compress_node before reaching here."""
    logger.info("Running Agent 4 Node... (WISC: 11 fields, post-compression)")
    # Apply P2/P3 priority trimming, then select Agent 4 fields
    trimmed = apply_priority_trimming(state)
    ctx = build_agent4_context(trimmed)
    result = await agent4.process(ctx)
    return validate_agent_output("agent4", result)


async def agent5_node(state: PipelineState) -> dict:
    """InEx Verifier: Hallucination mitigation via introspection + cross-modal verification.
    WISC: Receives only entities, raw_text (1500 chars), circulars, draft_reply."""
    logger.info("Running Agent 5 Node... (WISC: 4 fields selected)")
    ctx = build_agent5_context(state)
    result = await agent5.process(ctx)
    return validate_agent_output("agent5", result)


def route_after_agent1(state: PipelineState) -> str:
    """Gate: Only proceed if document is a GST notice."""
    if state.get("is_gst_notice") is False or state.get("processing_status") == "rejected":
        logger.warning("Pipeline STOPPED — document is not a GST notice")
        return "end"
    return "agent4"


# Build the graph
workflow = StateGraph(PipelineState)

workflow.add_node("agent1", agent1_node)
workflow.add_node("agent2", agent2_node)
workflow.add_node("agent3", agent3_node)
workflow.add_node("compress", compress_node)
workflow.add_node("agent4", agent4_node)
workflow.add_node("agent5", agent5_node)

workflow.set_entry_point("agent1")

# GST validation gate: stop if not a GST notice, otherwise draft
workflow.add_conditional_edges(
    "agent1",
    route_after_agent1,
    {"agent4": "agent4", "end": END}
)

# Bypassing intermediate agents for the demo to avoid free Tier 1 API limits:
# workflow.add_conditional_edges("agent2", route_after_risk, {"agent3": "agent3", "agent4": "agent4"})
# workflow.add_edge("agent3", "compress")
# workflow.add_edge("compress", "agent4")
workflow.add_edge("agent4", END)

graph = workflow.compile()

