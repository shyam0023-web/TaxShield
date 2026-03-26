You are a GST procedural law expert. Analyze this notice for procedural defects 
that could invalidate or weaken it.

NOTICE TEXT (first 2000 chars):
{notice_text}

ENTITIES:
- Sections: {sections}
- DINs found: {dins}
- Notice Date: {notice_date}
- Financial Year: {fy}

Check for these procedural defects under CGST Act:
1. **DIN requirement** (Circular 128/47/2019): Every communication must have a DIN. No DIN = invalid.
2. **Proper officer** (Section 2(91)): Was the notice issued by the proper officer?
3. **Opportunity of hearing** (Section 75(4)): Was personal hearing offered before adverse order?
4. **Time limit compliance**: Was the notice issued within the statutory time limit?
5. **Proper service** (Section 169): Was the notice properly served?
6. **Pre-SCN intimation** (Section 73(5)/74(5)): Was pre-notice intimation given?
7. **Demand computation**: Does the notice show detailed computation or just a lump-sum demand?
8. **Reasons recorded**: Are reasons for demand clearly stated?

Return JSON:
{{
    "defects": [
        {{
            "type": "NO_DIN|IMPROPER_OFFICER|NO_HEARING_OFFERED|TIME_LIMIT|SERVICE_DEFECT|NO_INTIMATION|NO_COMPUTATION|NO_REASONS",
            "description": "...",
            "legal_basis": "Section/Circular reference",
            "severity": "FATAL|SERIOUS|MINOR",
            "defense_value": "How to argue this in reply"
        }}
    ],
    "procedural_soundness": "SOUND|QUESTIONABLE|DEFECTIVE"
}}
