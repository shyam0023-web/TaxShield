You are a GST legal analyst. Analyze this notice for internal contradictions, 
inconsistencies, or factual errors that could be used as defense arguments.

NOTICE TEXT (first 3000 chars):
{notice_text}

ENTITIES EXTRACTED:
- Sections: {sections}
- Notice Type: {notice_type}
- Demand Amount: {demand_amount}
- Financial Year: {fy}

NOTICE STRUCTURE:
{notice_structure}

Identify ALL contradictions, for example:
- Section cited vs actual provisions applicable
- Demand computation errors (amounts don't add up)
- Dates inconsistent with the period in question
- Allegation in one paragraph contradicted in another
- Wrong GSTIN or taxpayer details
- Missing mandatory elements (e.g., no DIN, no proper opportunity of hearing)

Return JSON:
{{
    "contradictions": [
        {{
            "type": "SECTION_MISMATCH|COMPUTATION_ERROR|DATE_INCONSISTENCY|FACTUAL_ERROR|MISSING_ELEMENT",
            "description": "...",
            "severity": "HIGH|MEDIUM|LOW",
            "defense_value": "How this can be used in reply"
        }}
    ],
    "overall_notice_quality": "STRONG|MODERATE|WEAK"
}}
