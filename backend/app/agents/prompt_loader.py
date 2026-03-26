"""
TaxShield — Prompt Loader
Loads prompt templates from markdown files in the prompts/ directory.
Keeps prompts version-controlled and editable without touching Python code.
"""
import os
import logging

logger = logging.getLogger(__name__)

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def load_prompt(filename: str) -> str:
    """
    Load a prompt template from a markdown file.
    
    Args:
        filename: Name of the file in the prompts/ directory (e.g., "contradiction.md")
    
    Returns:
        The prompt template string with {placeholders} preserved.
    
    Raises:
        FileNotFoundError: If the prompt file doesn't exist.
    """
    filepath = os.path.join(PROMPTS_DIR, filename)
    
    if not os.path.exists(filepath):
        logger.error(f"Prompt file not found: {filepath}")
        raise FileNotFoundError(f"Prompt file not found: {filepath}")
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()
    
    logger.debug(f"Loaded prompt '{filename}' ({len(content)} chars)")
    return content
