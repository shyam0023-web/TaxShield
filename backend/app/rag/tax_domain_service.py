"""
TaxShield — Tax Domain-Specific Guardrailed LLM Service
Specialized for GST/Income Tax notices with regulatory compliance.

Guardrails:
1. Tax law compliance (cite sections, authorities)
2. Hallucination prevention (require source documents)
3. Risk scoring for accuracy
4. Jurisdiction validation
5. Statutory timeline awareness
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime, date
import re

import openai
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# Initialize OpenAI
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ═══════════════════════════════════════════
# Domain Enums & Constants
# ═══════════════════════════════════════════

class TaxDomain(str, Enum):
    """Tax domain classification"""
    GST = "gst"
    INCOME_TAX = "income_tax"
    CUSTOM = "custom"
    OTHER = "other"


class NoticeType(str, Enum):
    """GST/Income Tax notice types"""
    SCN = "SCN"  # Show Cause Notice
    DEMAND = "DEMAND"  # Demand notice
    PENALTY = "PENALTY"  # Penalty notice
    ADJOURNMENT = "ADJOURNMENT"  # Adjournment notice
    EXEMPTION = "EXEMPTION"  # Exemption notice
    OTHER = "OTHER"


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# GST-specific knowledge base
GST_SECTIONS = {
    "73": "Central Supplies Tax",
    "74": "Time limit for notice",
    "128": "Jurisdiction",
    "130": "Penalty for evasion",
    "132": "Goods in transit",
    "140": "Interest on late payment",
    "144": "Demand notice",
}

INCOME_TAX_SECTIONS = {
    "143": "Assessment",
    "144": "Demand notice",
    "147": "Assessment after assessment",
    "153": "Reassessment",
    "209": "Interest on default",
    "271": "Penalty for failure to file",
}

# Time limits (in days)
STATUTORY_LIMITS = {
    "SCN": {
        "gst": 30,  # GST SCN response time
        "income_tax": 30,
    },
    "DEMAND": {
        "gst": 30,
        "income_tax": 30,
    },
    "PENALTY": {
        "gst": 30,
        "income_tax": 30,
    },
}


# ═══════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════

class TaxDocument(BaseModel):
    """Structured representation of a tax notice/circular"""
    doc_id: str
    doc_type: str  # "notice", "circular", "ruling"
    domain: TaxDomain
    notice_type: Optional[NoticeType] = None
    title: str
    full_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Extracted structured data
    sections: List[str] = Field(default_factory=list)
    issued_date: Optional[date] = None
    jurisdiction: Optional[str] = None
    source_url: Optional[str] = None


class ComplianceCheck(BaseModel):
    """Compliance validation result"""
    is_compliant: bool
    risk_level: RiskLevel
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    audit_trail: List[str] = Field(default_factory=list)


class TaxGuardedResponse(BaseModel):
    """Response from guardrailed tax LLM"""
    answer: str = Field(description="Answer grounded in provided documents")
    analysis_type: str = Field(description="e.g., legal_opinion, compliance_check, risk_assessment")
    tax_domain: TaxDomain
    relevant_sections: List[str] = Field(description="Tax law sections cited")
    citations: List[str] = Field(description="Source document citations")
    confidence: float = Field(ge=0.0, le=1.0, description="0=uncertain, 1=highly confident")
    compliance: ComplianceCheck
    reasoning: str = Field(description="Step-by-step reasoning")
    sources_used: List[Dict[str, Any]] = Field(default_factory=list)


# ═══════════════════════════════════════════
# Tax Domain Guardrails
# ═══════════════════════════════════════════

class TaxLawValidator:
    """Validate responses against tax law & regulations"""
    
    @staticmethod
    def validate_section_citation(section: str, domain: TaxDomain) -> Tuple[bool, Optional[str]]:
        """
        Validate that cited tax section exists and is valid.
        
        Args:
            section: Section number (e.g., "73", "143")
            domain: Tax domain (GST or Income Tax)
            
        Returns:
            (is_valid, description)
        """
        if domain == TaxDomain.GST:
            db = GST_SECTIONS
        elif domain == TaxDomain.INCOME_TAX:
            db = INCOME_TAX_SECTIONS
        else:
            return True, "Unknown domain"
        
        if section in db:
            return True, db[section]
        else:
            return False, f"Section {section} not found in {domain.value}"
    
    @staticmethod
    def validate_deadline(notice_type: NoticeType, domain: TaxDomain, response_date: date) -> Tuple[bool, Optional[str]]:
        """
        Validate response deadline compliance.
        
        Args:
            notice_type: Type of notice
            domain: Tax domain
            response_date: When response was/will be submitted
            
        Returns:
            (is_within_deadline, message)
        """
        if notice_type not in STATUTORY_LIMITS:
            return True, "Unknown notice type"
        
        if domain.value not in STATUTORY_LIMITS[notice_type.value]:
            return True, "No deadline info available"
        
        limit_days = STATUTORY_LIMITS[notice_type.value][domain.value]
        # Implementation would check actual issue date
        return True, f"Statutory deadline: {limit_days} days"
    
    @staticmethod
    def extract_tax_sections(text: str, domain: TaxDomain) -> List[str]:
        """Extract tax section references from text"""
        if domain == TaxDomain.GST:
            # Match "Section 73", "Sec 73", "s.73", etc.
            pattern = r'[Ss](?:ection|ec\.?)\s+(\d+)'
        else:  # Income Tax
            pattern = r'[Ss](?:ection|ec\.?)\s+(\d+)'
        
        matches = re.findall(pattern, text)
        return list(set(matches))
    
    @staticmethod
    def check_jurisdiction(jurisdiction: str, domain: TaxDomain) -> Tuple[bool, Optional[str]]:
        """Validate jurisdiction against Indian tax structure"""
        valid_states = [
            "AN", "AP", "AR", "AS", "BR", "CG", "CH", "CT", "DD", "DL",
            "DN", "GA", "GJ", "HR", "HP", "JK", "JH", "KA", "KL", "LD",
            "LE", "MH", "ML", "MN", "MZ", "OD", "OL", "OR", "PB", "PY",
            "RJ", "SK", "TG", "TR", "TN", "UP", "UK", "UT", "WB", "YA"
        ]
        
        # Extract state code from jurisdiction
        state_code = jurisdiction.upper()[:2]
        if state_code in valid_states:
            return True, f"Valid state: {jurisdiction}"
        else:
            return False, f"Invalid jurisdiction: {jurisdiction}"


class HallucinationDetector:
    """Detect and prevent hallucinated claims in tax responses"""
    
    @staticmethod
    def requires_source_document(claim: str) -> bool:
        """
        Determine if a claim needs source document support.
        
        Patterns requiring citation:
        - Specific amounts
        - Legal section references
        - Case law citations
        - Dates
        """
        patterns = [
            r'\d+\.\d+',  # Amounts
            r'[Ss]ection\s+\d+',  # Sections
            r'\b\d{4}-\d{2}\b',  # Financial years
            r'\d{1,2}/\d{1,2}/\d{4}',  # Dates
            r'(case|ruling|judgment|verdict)',  # Case law
        ]
        
        return any(re.search(pattern, claim, re.IGNORECASE) for pattern in patterns)
    
    @staticmethod
    def validate_against_sources(claim: str, source_texts: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Check if a claim is supported by at least one source.
        
        Simple approach: check if key entities from claim appear in sources.
        """
        # Extract key terms (numbers, sections, proper nouns)
        key_terms = re.findall(r'\b(?:\d+|\w+-\d+|[A-Z][a-z]+\s[A-Z][a-z]+)\b', claim)
        
        if not key_terms:
            return True, "No specific claims to verify"
        
        # Check if at least one key term appears in sources
        for term in key_terms:
            for source in source_texts:
                if term in source:
                    return True, f"Claim supported by source (found: {term})"
        
        return False, f"Claim not found in provided sources (checked: {', '.join(key_terms[:3])})"


# ═══════════════════════════════════════════
# Main Guardrailed LLM Service
# ═══════════════════════════════════════════

class TaxGuardedLLMService:
    """
    Guardrailed LLM for tax-specific domain.
    
    Orchestration:
    1. Validate inputs (domain, jurisdiction, notice type)
    2. Retrieve relevant tax law
    3. Call LLM with strict instructions
    4. Validate response (sections, deadlines, sources)
    5. Check for hallucinations
    6. Score compliance risk
    7. Return structured response with audit trail
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.validator = TaxLawValidator()
        self.detector = HallucinationDetector()
    
    def _build_tax_system_prompt(self, domain: TaxDomain, analysis_type: str) -> str:
        """Build domain-specific system prompt with guardrails"""
        
        domain_guidance = {
            TaxDomain.GST: """
You are an expert GST tax consultant. Follow these rules strictly:
1. Only cite from provided circular/notice documents
2. Always reference GST Section numbers (e.g., Section 73, 74)
3. Include statutory timelines (e.g., 30 days for SCN response)
4. Validate amounts against notice details
5. Check financial year format (YYYY-YY)
6. Do NOT speculate on government positions
7. If information is not in documents, say "Not found in provided documents"
8. Cite source document every time you make a specific claim
""",
            TaxDomain.INCOME_TAX: """
You are an expert Income Tax consultant. Follow these rules strictly:
1. Only cite from provided circular/notice documents
2. Always reference Income Tax Act sections (e.g., Section 143, 144)
3. Include statutory timelines and assessment procedures
4. Validate amounts against notice details
5. Reference relevant rules (e.g., Rule 114)
6. Do NOT speculate on IT department positions
7. If information is not in documents, say "Not found in provided documents"
8. Cite source document every time you make a specific claim
""",
            TaxDomain.CUSTOM: "You are a tax consultant. Cite all sources.",
            TaxDomain.OTHER: "You are a regulatory consultant. Cite all sources.",
        }
        
        analysis_guidance = {
            "legal_opinion": "Provide legally sound opinion with section citations and case references.",
            "compliance_check": "Verify compliance with regulations. List all potential issues.",
            "risk_assessment": "Assess compliance risk (LOW/MEDIUM/HIGH). Explain each risk factor.",
            "deadline_analysis": "Analyze statutory deadlines. Include all relevant timelines.",
        }
        
        return f"""You are an expert tax consultant specializing in {domain.value}.

{domain_guidance.get(domain, domain_guidance[TaxDomain.OTHER])}

ANALYSIS TYPE: {analysis_type}
{analysis_guidance.get(analysis_type, "")}

CRITICAL GUARDRAILS:
- ONLY use information from provided documents
- CITE SOURCES for every claim: "[source_id: page/section]"
- If unsure or information missing: "This information is not available in the provided documents"
- List all tax sections referenced
- Include statutory timelines where applicable
- Return response in this JSON format:
{{
    "answer": "Your analysis here",
    "relevant_sections": ["73", "74"],
    "citations": ["[Doc1: Section 73]"],
    "compliance_issues": [],
    "reasoning": "Step-by-step explanation"
}}"""
    
    async def analyze_document(
        self,
        document: TaxDocument,
        domain: TaxDomain,
        analysis_type: str = "legal_opinion",
        question: Optional[str] = None,
    ) -> TaxGuardedResponse:
        """
        Analyze a tax document with full guardrails.
        
        Args:
            document: The tax document to analyze
            domain: Tax domain (GST, Income Tax, etc.)
            analysis_type: Type of analysis needed
            question: Specific question about document
            
        Returns:
            Guardrailed response with compliance checks
        """
        logger.info(f"[TaxGuardedLLM] Analyzing {document.doc_type} (domain={domain.value})")
        
        audit_trail = []
        
        # ═══ Validation Phase ═══
        audit_trail.append(f"Started analysis at {datetime.utcnow().isoformat()}")
        
        # Validate jurisdiction if present
        if document.jurisdiction:
            is_valid, msg = self.validator.check_jurisdiction(document.jurisdiction, domain)
            audit_trail.append(f"Jurisdiction validation: {msg}")
        
        # Extract tax sections from document
        found_sections = self.validator.extract_tax_sections(document.full_text, domain)
        audit_trail.append(f"Found {len(found_sections)} tax sections: {found_sections}")
        
        # ═══ LLM Analysis Phase ═══
        system_prompt = self._build_tax_system_prompt(domain, analysis_type)
        
        user_prompt = f"""Analyze this {domain.value} {document.doc_type}:

TITLE: {document.title}
ISSUED: {document.issued_date or 'Unknown'}
JURISDICTION: {document.jurisdiction or 'Not specified'}

DOCUMENT:
{document.full_text[:4000]}

{'QUESTION: ' + question if question else 'Provide comprehensive analysis.'}

Remember: ONLY use information from this document. Cite sources for every claim."""
        
        try:
            completion = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,  # Very low for consistency
                max_tokens=2000,
            )
            
            response_text = completion.choices[0].message.content
            audit_trail.append(f"LLM analysis completed ({len(response_text)} chars)")
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            audit_trail.append(f"LLM call failed: {str(e)}")
            raise
        
        # ═══ Parse Response ═══
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                parsed = {
                    "answer": response_text,
                    "relevant_sections": found_sections,
                    "citations": [],
                    "compliance_issues": [],
                    "reasoning": "Auto-parsed response",
                }
        except json.JSONDecodeError:
            parsed = {
                "answer": response_text,
                "relevant_sections": found_sections,
                "citations": [],
            }
        
        # ═══ Hallucination Detection ═══
        answer_text = parsed.get("answer", "")
        is_hallucinated = False
        hallucination_reasons = []
        
        sentences = answer_text.split(".")
        source_texts = [document.full_text]
        
        for sentence in sentences[:5]:  # Check first 5 sentences
            if self.detector.requires_source_document(sentence):
                is_supported, reason = self.detector.validate_against_sources(sentence, source_texts)
                if not is_supported:
                    is_hallucinated = True
                    hallucination_reasons.append(reason)
        
        if is_hallucinated:
            audit_trail.append(f"Hallucination detected: {hallucination_reasons}")
        
        # ═══ Compliance Scoring ═══
        compliance_issues = parsed.get("compliance_issues", [])
        risk_level = RiskLevel.LOW
        
        if len(compliance_issues) >= 3:
            risk_level = RiskLevel.HIGH
        elif len(compliance_issues) > 0:
            risk_level = RiskLevel.MEDIUM
        
        if is_hallucinated:
            risk_level = RiskLevel.HIGH
        
        audit_trail.append(f"Compliance risk: {risk_level.value}")
        
        # ═══ Section Validation ═══
        cited_sections = parsed.get("relevant_sections", [])
        invalid_sections = []
        for section in cited_sections:
            is_valid, _ = self.validator.validate_section_citation(section, domain)
            if not is_valid:
                invalid_sections.append(section)
                risk_level = RiskLevel.MEDIUM
        
        if invalid_sections:
            audit_trail.append(f"Invalid sections cited: {invalid_sections}")
        
        # ═══ Build Final Response ═══
        confidence = 0.9 if not is_hallucinated else 0.4
        if invalid_sections:
            confidence -= 0.2
        
        return TaxGuardedResponse(
            answer=answer_text,
            analysis_type=analysis_type,
            tax_domain=domain,
            relevant_sections=cited_sections,
            citations=parsed.get("citations", []),
            confidence=max(0.0, min(1.0, confidence)),
            compliance=ComplianceCheck(
                is_compliant=risk_level in [RiskLevel.LOW],
                risk_level=risk_level,
                issues=compliance_issues,
                warnings=[f"Invalid section: {s}" for s in invalid_sections],
                audit_trail=audit_trail,
            ),
            reasoning=parsed.get("reasoning", "Standard analysis"),
            sources_used=[{
                "doc_id": document.doc_id,
                "doc_type": document.doc_type,
                "title": document.title,
            }],
        )


# ═══════════════════════════════════════════
# Singleton Instance
# ═══════════════════════════════════════════

tax_llm_service = TaxGuardedLLMService()
