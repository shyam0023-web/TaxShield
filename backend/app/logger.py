import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the LogRecord.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if available
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
            
        return json.dumps(log_record)

def setup_logger(name: str = "TaxShield") -> logging.Logger:
    """
    Sets up a structured logger that outputs JSON to stdout.
    """
    logger = logging.getLogger(name)
    
    # clear existing handlers
    if logger.handlers:
        logger.handlers.clear()
        
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    logger.addHandler(handler)
    
    return logger

# Create global logger instance
logger = setup_logger()
