"""
TaxShield — Intelligent Context-Aware Report Generator
Reads document context first, analyzes sections, then generates tailored reports.
NOT template-based. Generative based on document content.
"""
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from datetime import datetime, date

import openai
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Initialize OpenAI
openai_client = openai.OpenAI()


class ReportType(str, Enum):
    """Types of reports generated"""
    NOTICE_ANALYSIS = "notice_analysis"  # Analyze uploaded notice
    COMPLIANCE_REPORT = "compliance_report"  # Compliance assessment
    DEFENSE_STRATEGY = "defense_strategy"  # Build defense against notice
    LEGAL_OPINION = "legal_opinion"  # Provide legal opinion
    RISK_ASSESSMENT = "risk_assessment"  # Risk scoring


class Section(BaseModel):
    """Identified section of document"""
    title: Optional[str]
    content: str
    role: str  # "header", "facts", "demand", "law", "conclusion"
    page_range: Optional[Tuple[int, int]] = None
    confidence: float = 0.8


class DocumentContext(BaseModel):
    """Full context extracted from document"""
    document_id: str
    title: str
    full_text: str
    notice_type: str
    issued_date: Optional[date]
    sections: List[Section]
    metadata: Dict[str, Any]
    
    # Extracted fields
    demand_amount: Optional[float] = None
    response_deadline: Optional[date] = None
    issuing_officer: Optional[str] = None
    jurisdiction: Optional[str] = None
    tax_sections: List[str] = Field(default_factory=list)
    key_entities: Dict[str, List[str]] = Field(default_factory=dict)


class ReportSection(BaseModel):
    """Individual section of a generated report"""
    heading: str
    content: str
    analysis_type: str  # "summary", "analysis", "action_item"
    confidence: float = 0.8
    sources: List[str] = Field(default_factory=list)


class GeneratedReport(BaseModel):
    """Complete generated report"""
    report_type: ReportType
    title: str
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    document_id: str
    sections: List[ReportSection]
    executive_summary: str
    key_findings: List[str]
    action_items: List[Dict[str, Any]]
    audit_trail: List[str] = Field(default_factory=list)


class ContextAnalyzer:
    """
    Analyze document to extract full context before report generation.
    
    Understands:
    - Notice structure (facts, demand, timeline)
    - Legal implications
    - Risk factors
    - Key amounts and dates
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
    
    async def analyze_document_context(self, full_text: str, document_title: str) -> DocumentContext:
        """
        Use LLM to understand document context deeply.
        
        Args:
            full_text: Full document text
            document_title: Document title
            
        Returns:
            Structured DocumentContext
        """
        logger.info(f"Analyzing document context: {document_title}")
        
        # Build analysis prompt
        analysis_prompt = f"""Analyze this tax document and extract ALL context:

TITLE: {document_title}

TEXT:
{full_text[:3000]}

Extract and return as JSON:
{{
    "notice_type": "SCN/Demand/Penalty/etc",
    "key_facts": ["fact1", "fact2"],
    "main_demand": {{"amount": 0, "description": ""}},
    "sections_referenced": ["73", "74"],
    "response_deadline_days": 30,
    "tax_year": "2019-20",
    "key_dates": {{"issued": "2024-01-15", "deadline": "2024-02-15"}},
    "jurisdiction": "state_code",
    "officer_details": {{"name": "", "designation": ""}},
    "main_issues": ["issue1", "issue2"],
    "document_structure": {{"has_facts": true, "has_demand": true, "has_relief": false}}
}}"""
        
        try:
            completion = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract document context. Return ONLY valid JSON."},
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
            )
            
            response_text = completion.choices[0].message.content
            context_data = json.loads(response_text)
            
        except Exception as e:
            logger.error(f"Context analysis failed: {e}")
            context_data = {
                "notice_type": "UNKNOWN",
                "key_facts": [],
                "main_demand": {"amount": 0},
            }
        
        # Build DocumentContext
        return DocumentContext(
            document_id="doc_" + str(hash(full_text))[:8],
            title=document_title,
            full_text=full_text,
            notice_type=context_data.get("notice_type", "UNKNOWN"),
            demand_amount=context_data.get("main_demand", {}).get("amount"),
            tax_sections=context_data.get("sections_referenced", []),
            key_entities={
                "facts": context_data.get("key_facts", []),
                "issues": context_data.get("main_issues", []),
            },
            metadata=context_data,
            sections=[],  # Would be populated from document structure analysis
        )


class IntelligentReportGenerator:
    """
    Generate context-aware reports.
    
    NOT template-based. Reads document context first, then generates:
    - Notice analysis (what does notice mean?)
    - Compliance report (are we compliant?)
    - Defense strategy (how to respond?)
    - Legal opinion (what's the law?)
    - Risk assessment (what are risks?)
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.analyzer = ContextAnalyzer(model)
    
    async def generate_notice_analysis(self, context: DocumentContext) -> GeneratedReport:
        """
        Generate analysis of uploaded notice.
        
        Answers:
        - What is this notice about?
        - What does it demand?
        - What's the timeline?
        - What are implications?
        """
        logger.info(f"Generating notice analysis for {context.document_id}")
        
        audit_trail = ["Started notice analysis"]
        
        # Build context-aware prompt
        prompt = f"""You are an expert GST/tax consultant. Analyze this notice and provide detailed insights.

DOCUMENT: {context.title}
TYPE: {context.notice_type}
DEMAND: ₹{context.demand_amount or 0:,.2f}
TIMELINE: {context.response_deadline or 'Not specified'}

KEY CONTEXT:
- Tax sections: {', '.join(context.tax_sections)}
- Key facts: {', '.join(context.key_entities.get('facts', [])[:5])}
- Main issues: {', '.join(context.key_entities.get('issues', [])[:5])}

DOCUMENT EXCERPT:
{context.full_text[:2000]}

Generate a comprehensive notice analysis with these sections:
1. NOTICE SUMMARY: What is this notice demanding?
2. NOTICE STRUCTURE: How is the notice organized?
3. KEY AMOUNTS: What are the financial implications?
4. RESPONSE DEADLINE: When must we respond?
5. LEGAL BASIS: What law sections are cited?
6. CRITICAL DATES: What dates matter?
7. NEXT STEPS: What should be done?

Return as JSON:
{{
    "notice_summary": "...",
    "structure_analysis": "...",
    "financial_impact": {{"demand": 0, "breakdown": {{}}}},
    "timeline": {{"response_by": "2024-02-15", "days_remaining": 30}},
    "legal_basis": ["Section 73", "Section 74"],
    "critical_issues": ["issue1"],
    "recommended_actions": ["action1"]
}}"""
        
        try:
            completion = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a tax expert. Provide analysis grounded in the notice."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2000,
            )
            
            response_text = completion.choices[0].message.content
            analysis_data = json.loads(response_text)
            audit_trail.append("LLM analysis completed")
            
        except Exception as e:
            logger.error(f"Analysis generation failed: {e}")
            audit_trail.append(f"Error in analysis: {str(e)}")
            analysis_data = {
                "notice_summary": f"Unable to analyze: {str(e)}",
                "structure_analysis": "",
                "recommended_actions": [],
            }
        
        # Build report sections
        report_sections = [
            ReportSection(
                heading="Notice Summary",
                content=analysis_data.get("notice_summary", ""),
                analysis_type="summary",
            ),
            ReportSection(
                heading="Notice Structure",
                content=analysis_data.get("structure_analysis", ""),
                analysis_type="analysis",
            ),
            ReportSection(
                heading="Financial Impact",
                content=f"Demand: ₹{context.demand_amount or 0:,.2f}",
                analysis_type="analysis",
            ),
            ReportSection(
                heading="Timeline",
                content=f"Response deadline: {context.response_deadline or 'Not specified'}",
                analysis_type="summary",
            ),
        ]
        
        # Build action items
        action_items = [
            {
                "action": action,
                "priority": "HIGH" if i == 0 else "MEDIUM",
                "deadline": str(context.response_deadline or "ASAP"),
            }
            for i, action in enumerate(analysis_data.get("recommended_actions", [])[:5])
        ]
        
        return GeneratedReport(
            report_type=ReportType.NOTICE_ANALYSIS,
            title=f"Analysis: {context.title}",
            document_id=context.document_id,
            sections=report_sections,
            executive_summary=analysis_data.get("notice_summary", ""),
            key_findings=analysis_data.get("critical_issues", []),
            action_items=action_items,
            audit_trail=audit_trail,
        )
    
    async def generate_compliance_report(self, context: DocumentContext) -> GeneratedReport:
        """
        Generate compliance assessment.
        
        Evaluates:
        - Compliance with tax law
        - Potential liability
        - Risk factors
        - Mitigation strategies
        """
        logger.info(f"Generating compliance report for {context.document_id}")
        
        audit_trail = ["Started compliance analysis"]
        
        prompt = f"""As a tax compliance expert, assess compliance implications.

NOTICE: {context.title}
TYPE: {context.notice_type}
AMOUNT: ₹{context.demand_amount or 0:,.2f}
SECTIONS: {', '.join(context.tax_sections)}

DOCUMENT:
{context.full_text[:2000]}

Provide compliance assessment:
1. COMPLIANCE GAPS: What compliance issues exist?
2. LIABILITY ASSESSMENT: What's the potential liability?
3. RISK FACTORS: What increases our risk?
4. MITIGATION: How to mitigate?
5. COMPLIANCE IMPROVEMENTS: Future preventive steps

Return as JSON:
{{
    "compliance_status": "COMPLIANT/NON-COMPLIANT/UNCERTAIN",
    "compliance_gaps": ["gap1"],
    "liability_estimate": {{"min": 0, "max": 0, "likely": 0}},
    "risk_score": 0.75,
    "risk_factors": ["factor1"],
    "mitigation_steps": ["step1"],
    "preventive_measures": ["measure1"]
}}"""
        
        try:
            completion = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a compliance expert. Assess tax compliance risks."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2000,
            )
            
            response_text = completion.choices[0].message.content
            report_data = json.loads(response_text)
            audit_trail.append("Compliance analysis completed")
            
        except Exception as e:
            logger.error(f"Compliance report failed: {e}")
            report_data = {"compliance_status": "UNKNOWN", "risk_factors": []}
        
        report_sections = [
            ReportSection(
                heading="Compliance Status",
                content=report_data.get("compliance_status", "UNKNOWN"),
                analysis_type="summary",
            ),
            ReportSection(
                heading="Compliance Gaps",
                content="\n".join(report_data.get("compliance_gaps", [])),
                analysis_type="analysis",
            ),
            ReportSection(
                heading="Risk Assessment",
                content=f"Risk Score: {report_data.get('risk_score', 0):.1%}",
                analysis_type="analysis",
            ),
            ReportSection(
                heading="Mitigation Strategy",
                content="\n".join(report_data.get("mitigation_steps", [])),
                analysis_type="action_item",
            ),
        ]
        
        return GeneratedReport(
            report_type=ReportType.COMPLIANCE_REPORT,
            title=f"Compliance Report: {context.title}",
            document_id=context.document_id,
            sections=report_sections,
            executive_summary=f"Compliance Status: {report_data.get('compliance_status')}",
            key_findings=report_data.get("risk_factors", []),
            action_items=[
                {"action": step, "priority": "HIGH", "deadline": "ASAP"}
                for step in report_data.get("mitigation_steps", [])
            ],
            audit_trail=audit_trail,
        )
    
    async def generate_defense_strategy(self, context: DocumentContext) -> GeneratedReport:
        """
        Generate defense strategy against notice.
        
        Develops:
        - Procedural defenses (time bar, jurisdiction)
        - Substantive defenses (facts, law)
        - Supporting documents
        - Response timeline
        """
        logger.info(f"Generating defense strategy for {context.document_id}")
        
        audit_trail = ["Started defense strategy"]
        
        prompt = f"""As a tax defense specialist, develop a defense strategy against this notice.

NOTICE: {context.title}
TYPE: {context.notice_type}
AMOUNT: ₹{context.demand_amount or 0:,.2f}
DEADLINE: {context.response_deadline or 'Not specified'}

FACTS IN NOTICE:
{', '.join(context.key_entities.get('facts', []))}

ISSUES:
{', '.join(context.key_entities.get('issues', []))}

Develop comprehensive defense:
1. PROCEDURAL DEFENSES: Time bar, jurisdiction, notice defects
2. SUBSTANTIVE DEFENSES: Facts vs claims, law analysis
3. KEY ARGUMENTS: Strongest points to make
4. SUPPORTING DOCUMENTS: What documents help?
5. RESPONSE STRATEGY: How to respond?

Return as JSON:
{{
    "procedural_defenses": ["defense1"],
    "substantive_defenses": ["defense2"],
    "key_arguments": ["argument1"],
    "supporting_documents": ["doc_type"],
    "response_strategy": "strategy description",
    "timeline": {{"prepare": 7, "submit": 21}},
    "estimated_success_rate": 0.65
}}"""
        
        try:
            completion = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a tax defense expert. Build a strong defense."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2500,
            )
            
            response_text = completion.choices[0].message.content
            strategy_data = json.loads(response_text)
            audit_trail.append("Defense strategy created")
            
        except Exception as e:
            logger.error(f"Defense strategy failed: {e}")
            strategy_data = {"procedural_defenses": [], "key_arguments": []}
        
        report_sections = [
            ReportSection(
                heading="Procedural Defenses",
                content="\n".join(strategy_data.get("procedural_defenses", [])),
                analysis_type="analysis",
            ),
            ReportSection(
                heading="Key Legal Arguments",
                content="\n".join(strategy_data.get("key_arguments", [])),
                analysis_type="analysis",
            ),
            ReportSection(
                heading="Response Strategy",
                content=strategy_data.get("response_strategy", ""),
                analysis_type="action_item",
            ),
            ReportSection(
                heading="Supporting Documentation",
                content="\n".join(strategy_data.get("supporting_documents", [])),
                analysis_type="action_item",
            ),
        ]
        
        return GeneratedReport(
            report_type=ReportType.DEFENSE_STRATEGY,
            title=f"Defense Strategy: {context.title}",
            document_id=context.document_id,
            sections=report_sections,
            executive_summary=f"Estimated Success Rate: {strategy_data.get('estimated_success_rate', 0):.0%}",
            key_findings=strategy_data.get("key_arguments", []),
            action_items=[
                {
                    "action": "Prepare response",
                    "priority": "CRITICAL",
                    "deadline": f"{strategy_data.get('timeline', {}).get('prepare', 7)} days",
                }
            ],
            audit_trail=audit_trail,
        )


# ═══════════════════════════════════════════
# Singleton Instance
# ═══════════════════════════════════════════

report_generator = IntelligentReportGenerator()
