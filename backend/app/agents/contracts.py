"""
TaxShield — WISC Typed Output Contracts
Pydantic models defining the exact output schema for each agent.

Benefits:
- Compile-time documentation of what each agent produces
- Runtime validation catches malformed outputs before they pollute downstream agents
- Typed contracts ensure agent compatibility across pipeline updates
"""
from pydantic import BaseModel, Field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# Agent 1: Document Processor Output
# ═══════════════════════════════════════════

class Agent1Output(BaseModel):
    """Output contract for Agent 1 (Document Processor)."""
    current_agent: str = "agent1"
    processing_status: str = Field(
        description="'complete', 'partial', or 'failed'"
    )
    raw_text: str = Field(default="", description="OCR-extracted notice text")
    entities: dict = Field(
        default_factory=dict,
        description="Extracted entities: GSTIN, SECTIONS, DIN, llm_extracted"
    )
    notice_annotations: list = Field(
        default_factory=list,
        description="Paragraph-level annotations with role (HEADER/FACTS/DEMAND/etc.)"
    )
    time_bar: dict = Field(
        default_factory=dict,
        description="Preliminary time-bar flag from Agent 1"
    )
    ocr_metadata: dict = Field(
        default_factory=dict,
        description="OCR engine used, confidence score"
    )
    redacted_fields: list = Field(
        default_factory=list,
        description="List of PII fields that were redacted"
    )
    processing_errors: list = Field(
        default_factory=list,
        description="List of non-fatal errors during processing"
    )


# ═══════════════════════════════════════════
# Agent 2: Risk Router Output
# ═══════════════════════════════════════════

class Agent2Output(BaseModel):
    """Output contract for Agent 2 (Risk Router)."""
    current_agent: str = "agent2"
    risk_level: str = Field(
        description="LOW, MEDIUM, HIGH, or UNKNOWN"
    )
    risk_score: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Numeric risk score 0.0-1.0"
    )
    risk_reasoning: str = Field(
        default="", description="Why this risk level was assigned"
    )
    is_time_barred: bool = Field(
        default=False,
        description="Final time-bar decision (section-aware)"
    )
    time_bar_detail: dict = Field(
        default_factory=dict,
        description="Section, time limit, years elapsed, reasoning"
    )
    deadline: dict = Field(
        default_factory=dict,
        description="Urgency classification"
    )
    assigned_tools: list = Field(
        default_factory=list,
        description="Tool set for Agent 3 based on risk level"
    )


# ═══════════════════════════════════════════
# Agent 3: Legal Analyst Output
# ═══════════════════════════════════════════

class Agent3Output(BaseModel):
    """Output contract for Agent 3 (Legal Analyst)."""
    current_agent: str = "agent3"
    retrieved_circulars: list = Field(
        default_factory=list,
        description="List of {doc_id, text, score} from RAG search"
    )
    defense_strategy: str = Field(
        default="",
        description="JSON string of defense strategy (pre-compression)"
    )
    contradictions: dict = Field(
        default_factory=dict,
        description="Contradictions found in the notice"
    )
    procedural_defects: dict = Field(
        default_factory=dict,
        description="Procedural defects found"
    )
    notice_quality: str = Field(
        default="UNKNOWN",
        description="STRONG, MODERATE, WEAK, or UNKNOWN"
    )
    procedural_soundness: str = Field(
        default="NOT_ANALYZED",
        description="SOUND, QUESTIONABLE, DEFECTIVE, or NOT_ANALYZED"
    )


# ═══════════════════════════════════════════
# Agent 4: Master Drafter Output
# ═══════════════════════════════════════════

class Agent4Output(BaseModel):
    """Output contract for Agent 4 (Master Drafter)."""
    current_agent: str = "agent4"
    draft_reply: str = Field(
        default="",
        description="Full draft reply text"
    )
    draft_type: str = Field(
        default="",
        description="'time_barred' or 'merit_based'"
    )
    draft_error: Optional[str] = Field(
        default=None,
        description="Error message if draft generation failed"
    )


# ═══════════════════════════════════════════
# Agent 5: InEx Verifier Output
# ═══════════════════════════════════════════

class VerificationIssue(BaseModel):
    """Single verification issue found by Agent 5."""
    stage: str = Field(description="citation_grounding|self_consistency|adversarial_challenge")
    issue: str = Field(description="Description of the issue")
    severity: str = Field(description="critical|warning|info")
    location: str = Field(default="N/A", description="Where in the draft")
    suggestion: str = Field(default="", description="How to fix it")


class Agent5Output(BaseModel):
    """Output contract for Agent 5 (InEx Verifier)."""
    current_agent: str = "agent5"
    verification_status: str = Field(
        description="'passed', 'needs_review', 'failed', or 'skipped'"
    )
    verification_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Aggregate verification score"
    )
    verification_issues: list = Field(
        default_factory=list,
        description="List of issue dicts from all 3 stages"
    )
    accuracy_report: dict = Field(
        default_factory=dict,
        description="Detailed report with per-stage scores"
    )
    citation_report: dict = Field(
        default_factory=dict,
        description="Citation grounding results"
    )


# ═══════════════════════════════════════════
# Validation Helper
# ═══════════════════════════════════════════

def validate_agent_output(agent_name: str, output: dict) -> dict:
    """
    Validate an agent's output against its typed contract.
    
    If validation fails, logs a warning but returns the raw output
    (graceful degradation — don't crash the pipeline on schema mismatch).
    """
    models = {
        "agent1": Agent1Output,
        "agent2": Agent2Output,
        "agent3": Agent3Output,
        "agent4": Agent4Output,
        "agent5": Agent5Output,
    }
    
    model = models.get(agent_name)
    if not model:
        logger.warning(f"No output contract defined for {agent_name}")
        return output
    
    try:
        validated = model(**output)
        logger.debug(f"{agent_name} output validated against contract ✓")
        return validated.model_dump()
    except Exception as e:
        logger.warning(
            f"{agent_name} output validation failed (graceful degradation): {e}. "
            f"Raw output keys: {list(output.keys())}"
        )
        return output
