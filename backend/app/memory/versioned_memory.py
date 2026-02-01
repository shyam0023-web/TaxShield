"""Append-only versioned memory for agents"""
from typing import List, Dict
from datetime import datetime
class VersionedMemory:
    def __init__(self):
        self.entries: List[Dict] = []
    
    def append(self, agent: str, data: Dict):
        # TODO: Add entry with timestamp
        pass
    
    def get_history(self):
        return self.entries
