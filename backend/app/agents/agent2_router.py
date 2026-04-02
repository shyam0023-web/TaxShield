"""
TaxShield — Agent 2: Risk Router
Classifies risk and makes section-aware time-bar decision.
Routes to Agent 3 with appropriate tool set.
"""
from app.llm.router import llm_router
from app.tools.timebar import TimeBarCalculator
from app.utils import parse_llm_extracted
import json
import logging

logger = logging.getLogger(__name__)

class Agent2Router:
    """
    Risk Router Agent.
    1. Makes FINAL time-bar decision (section-aware)
    2. Classifies risk: LOW / MEDIUM / HIGH
    3. Determines tool set for Agent 3
    """
    
    # Import time limits from timebar (single source of truth — Issue 6A)
    SECTION_TIME_LIMITS = TimeBarCalculator.SECTION_LIMITS
    
    # Tool sets by risk level
    TOOL_SETS = {
        "LOW":    ["select_template", "search_circulars"],
        "MEDIUM": ["request_document", "ask_client_question", "search_circulars",
                    "search_case_laws", "summarize_case_law", "detect_contradictions",
                    "build_defense_strategy"],
        "HIGH":   ["request_document", "ask_client_question", "search_circulars",
                    "search_case_laws", "summarize_case_law", "detect_contradictions",
                    "analyze_procedural_defects", "build_defense_strategy",
                    "assess_story_strength"]
    }
    
    def check_time_bar_with_section(self, entities: dict, time_bar_flag: dict) -> dict:
        """
        Section-aware time-bar check. This is the FINAL decision.
        Agent 1 only flagged potential time-bar — this agent decides.
        
        Key insight: Section 73 = 3 years, Section 74 = 5 years.
        Getting this wrong means killing a valid notice → client gets ex-parte order.
        """
        sections = entities.get("SECTIONS", [])
        
        # Determine applicable time limit
        time_limit = 3  # default to strictest
        applicable_section = "73"
        
        for section in sections:
            # Clean section number
            sec_num = section.split("(")[0].strip()
            if sec_num in self.SECTION_TIME_LIMITS:
                limit = self.SECTION_TIME_LIMITS[sec_num]
                if limit > time_limit:
                    time_limit = limit
                    applicable_section = sec_num
        
        years_elapsed = time_bar_flag.get("years_elapsed", 0)
        is_time_barred = years_elapsed > time_limit
        
        return {
            "is_time_barred": is_time_barred,
            "applicable_section": applicable_section,
            "time_limit_years": time_limit,
            "years_elapsed": years_elapsed,
            "reasoning": f"Section {applicable_section} -> {time_limit} year limit. Elapsed: {years_elapsed} years."
        }
    
    async def classify_risk(self, entities: dict, raw_text: str) -> dict:
        """
        Classify risk using LLM + rules.
        LOW: scrutiny, <₹5L, single issue
        MEDIUM: ₹5L-50L, multiple issues
        HIGH: >₹50L, prosecution, penalty
        """
        # Parse demand amount from entities
        llm_data = parse_llm_extracted(entities)
        
        prompt = f"""Classify this GST notice risk level based on the extracted data.

Return JSON EXACTLY in this format:
{{
    "risk_level": "LOW|MEDIUM|HIGH",
    "risk_score": 0.5,
    "reasoning": "brief explanation",
    "urgency": "NORMAL|URGENT|CRITICAL"
}}

Classification rules:
- LOW: Scrutiny notice (Sec 61), demand < ₹5 lakh, single straightforward issue
- MEDIUM: Demand ₹5-50 lakh, complex facts, ITC mismatch, multiple issues
- HIGH: Demand > ₹50 lakh, penalty u/s 122-138, prosecution u/s 132, 
        search/seizure, arrest provisions, fraud allegations (Sec 74)

Notice entities:
- Sections: {entities.get("SECTIONS", [])}
- Notice type: {llm_data.get("notice_type", "Unknown")}
- Demand amount: {llm_data.get("demand_amount", "Unknown")}
- Penalty: {llm_data.get("penalty_amount", 0)}

First 1000 chars of notice:
{raw_text[:1000]}
"""
        try:
            # Route through the central LLM Router (Flash/Pro/Groq fallback)
            # Use LOW risk for classification to use Gemini Flash (fast)
            result = await llm_router.generate(prompt, risk_level="LOW", json_mode=True)
            return json.loads(result) if isinstance(result, str) else result
        except Exception as e:
            logger.error(f"Risk classification failed: {e}")
            return {
                "risk_level": "MEDIUM",
                "risk_score": 0.6,
                "reasoning": f"Fallback to MEDIUM due to LLM error: {str(e)}",
                "urgency": "NORMAL",
                "_warning": f"⚠ Risk analysis used MEDIUM default — LLM error: {str(e)}"
            }
    
    async def process(self, state_dict: dict) -> dict:
        """
        Main Agent 2 processing function. Takes Agent 1 output from state.
        Returns updates for the global PipelineState.
        """
        logger.info("=== Agent 2: Risk Router ===")
        
        # Check Agent 1 processing status
        processing_status = state_dict.get("processing_status", "unknown")
        
        if processing_status == "failed":
            logger.error("Agent 1 failed — cannot route. Returning UNKNOWN risk.")
            return {
                "current_agent": "agent2",
                "risk_level": "UNKNOWN",
                "risk_reasoning": f"Agent 1 failed: {state_dict.get('error', 'unknown error')}",
                "processing_errors": state_dict.get("processing_errors", []),
            }
        
        if processing_status == "partial":
            logger.warning(f"Agent 1 partial — some steps failed: {state_dict.get('processing_errors', [])}")
        
        entities = state_dict.get("entities", {})
        raw_text = state_dict.get("raw_text", "")
        time_bar_flag = state_dict.get("time_bar", {})
        
        if not entities or not raw_text:
            logger.warning("Agent 2 got empty entities/text. Skipping routing tools.")
            return {"current_agent": "agent2", "risk_level": "UNKNOWN"}
        
        # Step 1: Section-aware time-bar (FINAL decision)
        time_bar_result = self.check_time_bar_with_section(entities, time_bar_flag)
        logger.info(f"Time-bar decision: {time_bar_result['is_time_barred']} (Reason: {time_bar_result['reasoning']})")
        
        # Step 2: Risk classification via LLM
        risk = await self.classify_risk(entities, raw_text)
        risk_level = risk.get("risk_level", "MEDIUM")
        logger.info(f"Classified Risk: {risk_level} (Score: {risk.get('risk_score')})")
        
        # Step 3: Select tool set for Agent 3
        tools = self.TOOL_SETS.get(risk_level, self.TOOL_SETS["MEDIUM"])
        
        # Issue 7: Collect warnings from fallback paths
        warnings = state_dict.get("processing_warnings", []) or []
        if risk.get("_warning"):
            warnings.append(risk["_warning"])
        
        # Return state dictionary updates
        return {
            "current_agent": "agent2",
            "risk_level": risk_level,
            "risk_score": float(risk.get("risk_score", 0.5)),
            "risk_reasoning": risk.get("reasoning", "No reasoning provided"),
            "deadline": {"urgency": risk.get("urgency", "NORMAL")},
            "is_time_barred": time_bar_result["is_time_barred"],
            "time_bar_detail": time_bar_result,
            "assigned_tools": tools,
            "processing_warnings": warnings,
        }

agent2 = Agent2Router()
