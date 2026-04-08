# TaxShield Guardrailed RAG — API Integration Guide

**This guide shows how to integrate the new tax-domain RAG system into your existing TaxShield architecture.**

---

## Quick Start (5 Minutes)

### 1. Import Components

```python
from app.rag import (
    # Domain-specific
    TaxDomain, NoticeType, RiskLevel,
    tax_llm_service,
    
    # PDF/OCR
    pdf_processor,
    
    # Report generation
    report_generator,
)
```

### 2. Process Notice with Full Pipeline

```python
# Upload notice PDF
pdf_bytes = await request.file.read()

# 1. Extract text + structure
extraction = await pdf_processor.process_pdf(pdf_bytes)
full_text = extraction["full_text"]
tax_metadata = extraction["tax_metadata"]

# 2. Analyze with tax guardrails
from app.rag.tax_domain_service import TaxDocument

doc = TaxDocument(
    doc_id="notice_" + uuid.uuid4().hex[:8],
    doc_type="notice",
    domain=TaxDomain.GST,
    notice_type=tax_metadata.get("notice_type"),
    title="GST Notice",
    full_text=full_text,
    jurisdiction=tax_metadata.get("jurisdiction"),
)

# Full guardrailed analysis
guardrailed_response = await tax_llm_service.analyze_document(
    document=doc,
    domain=TaxDomain.GST,
    analysis_type="legal_opinion",
)

# 3. Generate context-aware report
context = await report_generator.analyzer.analyze_document_context(
    full_text,
    f"Notice Analysis: {tax_metadata.get('notice_type', 'Unknown')}"
)

report = await report_generator.generate_notice_analysis(context)
```

---

## API Endpoints (New/Enhanced)

### POST `/api/rag/upload_notice`

Upload notice with full analysis pipeline.

**Request:**
```json
{
  "file": "<binary PDF>",
  "analysis_type": "legal_opinion"  // or compliance_report, defense_strategy
}
```

**Response:**
```json
{
  "doc_id": "notice_abc123",
  "extraction": {
    "full_text": "...",
    "notice_type": "SCN",
    "demand_amount": 100000,
    "response_deadline": "2024-02-15",
    "tax_sections": ["73", "74"],
    "quality_metrics": {
      "ocr_confidence": 0.95,
      "is_digital_pdf": true
    }
  },
  "guardrailed_analysis": {
    "answer": "Based on the notice...",
    "relevant_sections": ["73", "74"],
    "confidence": 0.92,
    "compliance": {
      "is_compliant": true,
      "risk_level": "MEDIUM",
      "issues": ["Potential time bar"],
      "audit_trail": [...]
    }
  },
  "report": {
    "report_type": "notice_analysis",
    "executive_summary": "This is a SCN...",
    "key_findings": ["Section 74 time bar likely applies"],
    "action_items": [...]
  }
}
```

### POST `/api/rag/analyze/{doc_id}`

Generate specific report type for uploaded notice.

**Request:**
```json
{
  "analysis_type": "defense_strategy"  // notice_analysis, compliance_report, defense_strategy, legal_opinion, risk_assessment
}
```

**Response:**
```json
{
  "report_type": "defense_strategy",
  "title": "Defense Strategy: GST SCN",
  "sections": [
    {
      "heading": "Procedural Defenses",
      "content": "Section 74 time bar: Notice issued...",
      "analysis_type": "analysis"
    }
  ],
  "key_findings": [
    "Section 74 - 3 year time bar applies",
    "Notice may be invalid"
  ],
  "action_items": [
    {
      "action": "File response highlighting time bar",
      "priority": "CRITICAL",
      "deadline": "2024-02-15"
    }
  ]
}
```

### GET `/api/rag/notice/{doc_id}`

Retrieve full notice analysis with all components.

**Response:**
```json
{
  "doc_id": "notice_abc123",
  "original_text": "...",
  "structure": {
    "header": "...",
    "body_paragraphs": [...],
    "footer": "..."
  },
  "extractions": {
    "notice_type": "SCN",
    "demand_amount": 100000,
    "sections": ["73", "74"],
    "dates": {...}
  },
  "analyses": {
    "guardrailed": {...},
    "reports": [...]
  }
}
```

---

## Domain-Specific Guardrails

### Tax Law Validation

```python
from app.rag.tax_domain_service import TaxLawValidator

validator = TaxLawValidator()

# Validate section citation
is_valid, msg = validator.validate_section_citation("73", TaxDomain.GST)
# → (True, "Central Supplies Tax")

is_valid, msg = validator.validate_section_citation("999", TaxDomain.GST)
# → (False, "Section 999 not found in gst")

# Validate jurisdiction
is_valid, msg = validator.check_jurisdiction("MH", TaxDomain.GST)
# → (True, "Valid state: MH (Maharashtra)")

# Extract tax sections from text
sections = validator.extract_tax_sections(text, TaxDomain.GST)
# → ["73", "74", "140"]
```

### Hallucination Detection

```python
from app.rag.tax_domain_service import HallucinationDetector

detector = HallucinationDetector()

# Check if claim needs source
requires_source = detector.requires_source_document("Section 73 applies")
# → True

requires_source = detector.requires_source_document("This seems reasonable")
# → False

# Validate claim against sources
claim = "Tax demand is ₹1,00,000"
sources = ["The total demand including interest is ₹1,00,000"]

is_supported, reason = detector.validate_against_sources(claim, sources)
# → (True, "Claim supported by source (found: 1,00,000)")
```

---

## Report Generation Examples

### 1. Notice Analysis Report

```python
context = await report_generator.analyzer.analyze_document_context(full_text, title)
report = await report_generator.generate_notice_analysis(context)

# Analyzes:
# - What is this notice about?
# - What does it demand?
# - What's the timeline?
# - What are implications?
# - What are next steps?

# Output includes:
# - Notice summary
# - Structure analysis
# - Financial impact
# - Timeline
# - Key issues
# - Recommended actions
```

### 2. Compliance Report

```python
report = await report_generator.generate_compliance_report(context)

# Assesses:
# - Compliance status
# - Compliance gaps
# - Liability estimate
# - Risk score
# - Risk factors
# - Mitigation steps
# - Preventive measures
```

### 3. Defense Strategy

```python
report = await report_generator.generate_defense_strategy(context)

# Develops:
# - Procedural defenses (time bar, jurisdiction)
# - Substantive defenses (facts, law)
# - Key arguments
# - Supporting documents needed
# - Response timeline
# - Estimated success rate
```

---

## Integration with Existing Agents

### Option A: Replace Agent4 (Drafter)

**Old Way (Blackbox LangGraph):**
```python
# app/agents/agent4_drafter.py
async def process(state_dict):
    # LangGraph blackbox
    draft = await agent4.invoke(state_dict)
    return draft
```

**New Way (Transparent RAG):**
```python
from app.rag import report_generator

async def process(state_dict):
    # Get notice text from upstream
    full_text = state_dict.get("raw_text", "")
    
    # Generate context-aware response
    context = await report_generator.analyzer.analyze_document_context(
        full_text,
        "Defense Reply"
    )
    
    # Generate defense strategy
    strategy_report = await report_generator.generate_defense_strategy(context)
    
    # Convert to draft format
    draft_reply = f"""{strategy_report.executive_summary}

## Procedural Defenses
{strategy_report.sections[0].content}

## Substantive Arguments
{strategy_report.sections[1].content}

## Required Actions
{json.dumps(strategy_report.action_items, indent=2)}
"""
    
    state_dict["draft_reply"] = draft_reply
    state_dict["draft_analysis"] = strategy_report.dict()
    return state_dict
```

### Option B: Add as Parallel Analysis

```python
# app/routes/notices.py - NEW ENDPOINT
from app.rag import tax_llm_service, report_generator

@router.post("/notices/{notice_id}/rag-analysis")
async def get_rag_analysis(notice_id: str, analysis_type: str = "legal_opinion"):
    """
    Get guardrailed RAG analysis alongside existing pipeline.
    """
    notice = await db.get_notice(notice_id)
    
    # Use RAG system
    from app.rag.tax_domain_service import TaxDocument, TaxDomain
    
    doc = TaxDocument(
        doc_id=notice_id,
        doc_type="notice",
        domain=TaxDomain.GST,
        notice_type=notice.notice_type,
        title=notice.filename,
        full_text=notice.notice_text,
        jurisdiction=notice.jurisdiction,
        sections=notice.sections,
    )
    
    # Get guardrailed analysis
    response = await tax_llm_service.analyze_document(
        document=doc,
        domain=TaxDomain.GST,
        analysis_type=analysis_type,
    )
    
    # Get context-aware report
    context = await report_generator.analyzer.analyze_document_context(
        notice.notice_text,
        notice.filename,
    )
    
    report = await report_generator.generate_notice_analysis(context)
    
    return {
        "notice_id": notice_id,
        "guardrailed_analysis": response.dict(),
        "context_aware_report": report.dict(),
    }
```

---

## Configuration Examples

### GST Notice Analysis

```python
from app.rag import TaxDomain, tax_llm_service, TaxDocument

# For GST notices
doc = TaxDocument(
    doc_id="gst_scn_2024",
    doc_type="notice",
    domain=TaxDomain.GST,
    title="GST SCN",
    full_text="...",
    metadata={"revenue_code": "0821"}
)

response = await tax_llm_service.analyze_document(
    document=doc,
    domain=TaxDomain.GST,
    analysis_type="compliance_check",
)

# Response includes:
# - GST-specific sections (73, 74, 140)
# - VAT compliance assessment
# - Input tax credit issues
# - Jurisdiction validation
```

### Income Tax Notice Analysis

```python
# For Income Tax notices
doc = TaxDocument(
    doc_id="it_notice_2024",
    doc_type="notice",
    domain=TaxDomain.INCOME_TAX,
    title="IT Assessment Notice",
    full_text="...",
)

response = await tax_llm_service.analyze_document(
    document=doc,
    domain=TaxDomain.INCOME_TAX,
    analysis_type="legal_opinion",
)

# Response includes:
# - Income Tax specific sections (143, 144, 147)
# - Assessment procedure analysis
# - Rule references
# - Jurisdiction checks
```

---

## Error Handling & Fallbacks

```python
from app.rag import tax_llm_service, report_generator

try:
    # Analysis with guardrails
    response = await tax_llm_service.analyze_document(doc, domain)
    
except ValueError as e:
    # Guardrail violation (e.g., hallucination detected)
    logger.warning(f"Guardrail violation: {e}")
    return {
        "status": "warning",
        "message": "Analysis flagged for review",
        "reason": str(e),
        "confidence": 0.3,
    }

except Exception as e:
    # LLM failure - fallback to simple extraction
    logger.error(f"Analysis failed: {e}")
    return {
        "status": "error",
        "message": "Could not perform full analysis",
        "fallback": "Using basic extraction only",
        "extracted_data": {
            "notice_type": detect_notice_type(full_text),
            "sections": extract_sections(full_text),
        }
    }
```

---

## Performance & Cost

### Processing Time

| Component | Time | Notes |
|-----------|------|-------|
| PDF Extraction | 0.5-2s | Depends on pages & scanned vs. native |
| OCR (if needed) | 2-5s | Surya OCR on CPU |
| LLM Analysis | 2-5s | OpenAI API latency |
| Report Generation | 2-4s | Multiple LLM calls |
| **Total** | **7-16s** | Per notice end-to-end |

### Cost per Notice

```
PDF Extraction:  Free (local)
OCR (Surya):     Free (local)
LLM Analysis:    $0.03-0.10 (gpt-4o-mini)
Report Gen:      $0.05-0.15 (multiple calls)
─────────────────────────────
Total per notice: $0.08-0.25 (~₹6-20)
```

---

## Monitoring & Logging

```python
# All operations logged automatically
logger.info(f"[RAG] Processing notice: {doc_id}")
logger.debug(f"[RAG] Found sections: {sections}")
logger.warning(f"[RAG] Hallucination detected: {reason}")
logger.error(f"[RAG] Analysis failed: {error}")

# Audit trail in response
response.compliance.audit_trail = [
    "Started analysis at 2024-04-06T10:30:00",
    "Jurisdiction validation: Valid state MH",
    "Found 5 tax sections: ['73', '74', '140']",
    "Hallucination check: Passed",
    "Compliance risk: MEDIUM",
]
```

---

## Testing Examples

### Unit Test

```python
import pytest
from app.rag import TaxLawValidator, HallucinationDetector, TaxDomain

def test_section_validation():
    validator = TaxLawValidator()
    
    # Valid section
    is_valid, msg = validator.validate_section_citation("73", TaxDomain.GST)
    assert is_valid == True
    assert "Central" in msg
    
    # Invalid section
    is_valid, msg = validator.validate_section_citation("999", TaxDomain.GST)
    assert is_valid == False
    assert "not found" in msg

def test_hallucination_detection():
    detector = HallucinationDetector()
    
    claim = "₹1,00,000 demand"
    sources = ["The total demand is ₹1,00,000"]
    
    is_supported, _ = detector.validate_against_sources(claim, sources)
    assert is_supported == True
```

### Integration Test

```python
@pytest.mark.asyncio
async def test_full_pipeline():
    # Load test PDF
    with open("test_notice.pdf", "rb") as f:
        pdf_bytes = f.read()
    
    # Process
    extraction = await pdf_processor.process_pdf(pdf_bytes)
    assert extraction["full_text"]
    assert extraction["tax_metadata"]["notice_type"]
    
    # Analyze
    doc = TaxDocument(..., full_text=extraction["full_text"])
    response = await tax_llm_service.analyze_document(doc, TaxDomain.GST)
    
    # Verify guardrails
    assert response.confidence >= 0.0
    assert response.confidence <= 1.0
    assert response.compliance.audit_trail
    
    # Generate report
    context = await report_generator.analyzer.analyze_document_context(...)
    report = await report_generator.generate_notice_analysis(context)
    
    assert report.sections
    assert report.action_items
```

---

## Next Steps

1. **Deploy tax-domain service**
   - Test with 50+ real notices
   - Validate guardrails
   - Measure accuracy

2. **Integrate with Agent4 (Drafter)**
   - Replace blackbox LangGraph
   - Use context-aware reports
   - Test output quality

3. **Monitor production**
   - Track hallucination rate
   - Measure report usefulness
   - Collect CA feedback

4. **Continuous improvement**
   - Fine-tune prompts by domain
   - Add more guardrails
   - Expand to more notice types

---

**Version:** 1.0  
**Date:** 2024-04-06  
**Status:** Ready for Integration  
**Support:** See RAG_RESEARCH_DOCUMENTATION.md for details
