"""
TaxShield — Ingestion
Purpose: 2-bucket structuring (legal_principle + procedure) before embedding
Status: PARTIALLY IMPLEMENTED — needs 2-bucket logic
"""
import json
import os
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class LegalDocument:
    doc_id: str
    title: str
    text: str
    section_ref: str
    metadata: Dict

def load_circulars(data_dir: str = "data/circulars") -> List[LegalDocument]:
    documents = []
    
    if not os.path.exists(data_dir):
        if os.path.exists(os.path.join("backend", data_dir)):
            data_dir = os.path.join("backend", data_dir)
        else:
            return []

    for filename in sorted(os.listdir(data_dir)):
        if filename.endswith(".json"):
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    doc = LegalDocument(
                        doc_id=data.get("doc_id", "UNKNOWN"),
                        title=data.get("title", ""),
                        text=data.get("text", ""),
                        section_ref=data.get("section_ref", ""),
                        metadata={"valid_from": data.get("valid_from"), "keywords": data.get("keywords", [])}
                    )
                    documents.append(doc)
            except Exception:
                continue
                
    return documents

if __name__ == "__main__":
    docs = load_circulars("data/circulars")
    print(f"✅ Loaded {len(docs)} circulars")
