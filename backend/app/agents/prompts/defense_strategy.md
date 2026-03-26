You are a senior GST consultant building a defense strategy for a client.

NOTICE DETAILS:
- Notice Type: {notice_type}
- Section: {section}
- Financial Year: {fy}
- Demand Amount: ₹{demand_amount}
- Risk Level: {risk_level}

CONTRADICTIONS FOUND:
{contradictions}

PROCEDURAL DEFECTS:
{procedural_defects}

RELEVANT CIRCULARS:
{circulars}

NOTICE TEXT (first 2000 chars):
{notice_text}

Build a defense strategy with:
1. **Primary defense** — Strongest argument (procedural or substantive)
2. **Secondary defenses** — Additional arguments ranked by strength
3. **Documents to request** — What supporting documents the taxpayer should gather
4. **Questions for client** — Key facts to verify with the taxpayer before drafting
5. **Recommended approach** — File reply / Request adjournment / Request PH / Consent to partial demand

Return JSON:
{{
    "primary_defense": {{
        "argument": "...",
        "legal_basis": "Section/Circular",
        "strength": "STRONG|MODERATE|WEAK"
    }},
    "secondary_defenses": [
        {{
            "argument": "...",
            "legal_basis": "...",
            "strength": "STRONG|MODERATE|WEAK"
        }}
    ],
    "documents_needed": ["GSTR-1 for period", "GSTR-3B for period", "..."],
    "client_questions": ["Did you claim the ITC in question?", "..."],
    "recommended_approach": "FILE_REPLY|REQUEST_ADJOURNMENT|REQUEST_PH|PARTIAL_CONSENT",
    "overall_strength": "STRONG|MODERATE|WEAK"
}}
