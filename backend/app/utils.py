"""
TaxShield — Shared Entity Parsing Utilities
DRY helpers for parsing LLM-extracted data from pipeline state.

These patterns were duplicated 8+ times across agents — consolidated here
so there's exactly one place to fix JSON parsing bugs.
"""
import json
import logging

logger = logging.getLogger(__name__)


def parse_llm_extracted(entities: dict) -> dict:
    """Safely parse the llm_extracted field from entities.
    
    The NER agent sometimes returns llm_extracted as a JSON string
    instead of a dict (depends on LLM response format). This helper
    normalizes it to always return a dict.
    
    Args:
        entities: The entities dict from pipeline state
        
    Returns:
        Parsed dict (never None, never a string)
    """
    if not isinstance(entities, dict):
        return {}
    
    llm_data = entities.get("llm_extracted", {})
    
    if isinstance(llm_data, str):
        try:
            llm_data = json.loads(llm_data)
        except (json.JSONDecodeError, TypeError):
            logger.warning("parse_llm_extracted: Failed to parse llm_extracted string as JSON")
            llm_data = {}
    
    if not isinstance(llm_data, dict):
        return {}
    
    return llm_data


def parse_demand_amount(llm_data: dict) -> float:
    """Parse demand amount from llm_extracted data.
    
    Handles both formats:
    - {"demand_amount": {"igst": 0, "cgst": 0, "sgst": 0, "total": 12345}}
    - {"demand_amount": 12345}
    
    Args:
        llm_data: Parsed llm_extracted dict (use parse_llm_extracted first)
        
    Returns:
        Demand amount as float (0.0 if not found or unparseable)
    """
    raw_demand = llm_data.get("demand_amount")
    
    if isinstance(raw_demand, dict):
        try:
            return float(raw_demand.get("total", 0) or 0)
        except (ValueError, TypeError):
            return 0.0
    elif isinstance(raw_demand, (int, float)):
        return float(raw_demand)
    
    return 0.0
