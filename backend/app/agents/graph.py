"""
TaxShield — LangGraph Workflow
Pipeline: Agent1 (OCR+NER) → Agent2 (Risk Router) → Agent3 (Legal Analyst) → Agent4 (Drafter) → Agent5 (InEx Verifier)
"""
from langgraph.graph import StateGraph, END
from app.agents.state import PipelineState
from app.agents.agent1_processor import agent1
from app.agents.agent2_router import agent2
from app.agents.agent3_analyst import agent3
from app.agents.agent4_drafter import agent4
from app.agents.agent5_verifier import agent5
import logging

logger = logging.getLogger(__name__)


async def agent1_node(state: PipelineState) -> dict:
    """Document Processor: Extract entities, OCR, check time-bar flags."""
    logger.info("Running Agent 1 Node...")
    
    pdf_bytes = state.get("pdf_bytes")
    if not pdf_bytes:
        return {"processing_errors": ["No PDF bytes provided"], "current_agent": "agent1"}
    
    result = await agent1.process(pdf_bytes)
    return result


async def agent2_node(state: PipelineState) -> dict:
    """Risk Router: Classify risk and finalize time-bar using Agent 1 output."""
    logger.info("Running Agent 2 Node...")
    result = await agent2.process(state)
    return result


def route_after_risk(state: PipelineState) -> str:
    """Route based on risk level and time-bar status."""
    if state.get("is_time_barred", False):
        logger.info("Route → Agent 4 (Time-Barred Notice)")
        return "agent4"
    logger.info("Route → Agent 3 (Merit Based Defense)")
    return "agent3"


async def agent3_node(state: PipelineState) -> dict:
    """Legal Analyst: Search circulars, detect contradictions, build defense."""
    logger.info("Running Agent 3 Node...")
    result = await agent3.process(state)
    return result


async def agent4_node(state: PipelineState) -> dict:
    """Master Drafter: Generate draft reply from pipeline output."""
    logger.info("Running Agent 4 Node...")
    result = await agent4.process(state)
    return result


async def agent5_node(state: PipelineState) -> dict:
    """InEx Verifier: Hallucination mitigation via introspection + cross-modal verification."""
    logger.info("Running Agent 5 Node...")
    result = await agent5.process(state)
    return result


# Build the graph
workflow = StateGraph(PipelineState)

workflow.add_node("agent1", agent1_node)
workflow.add_node("agent2", agent2_node)
workflow.add_node("agent3", agent3_node)
workflow.add_node("agent4", agent4_node)
workflow.add_node("agent5", agent5_node)

workflow.set_entry_point("agent1")
workflow.add_edge("agent1", "agent2")
workflow.add_conditional_edges("agent2", route_after_risk, {"agent3": "agent3", "agent4": "agent4"})
workflow.add_edge("agent3", "agent4")
workflow.add_edge("agent4", "agent5")
workflow.add_edge("agent5", END)

graph = workflow.compile()

