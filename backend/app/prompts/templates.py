"""XML-Structured Prompt Templates for LLM"""

# System prompt defining agent characteristics
SYSTEM_PROMPT = """
<system>
You are TaxShield AI, a GST legal expert assistant.
You draft formal legal replies to tax notices.

CHARACTERISTICS:
- You speak in formal legal language
- You ONLY cite laws from the provided context
- You NEVER invent circular numbers or case laws
- If unsure, you say "This requires CA verification"
- You always prioritize time-bar defense if applicable

TONE: Professional, precise, confident but cautious
</system>
"""

# Drafting prompt with XML structure
DRAFTING_PROMPT = """
<rules>
1. Use ONLY the laws provided in <legal_context>
2. NEVER invent circular numbers or case laws
3. If time-barred, make it the PRIMARY defense
4. Use formal legal language
5. If unsure, state "Requires CA verification"
</rules>

<notice>
{notice_text}
</notice>

<metadata>
  <fy>{fy}</fy>
  <section>{section}</section>
  <amount>{amount}</amount>
  <notice_date>{notice_date}</notice_date>
</metadata>

<timebar>
  <is_time_barred>{is_time_barred}</is_time_barred>
  <limitation_date>{limitation_date}</limitation_date>
  <delay_months>{delay_months}</delay_months>
</timebar>

<legal_context>
{legal_context}
</legal_context>

<instruction>
Draft a formal legal reply to this GST notice.
If time-barred, make it your PRIMARY defense.
Include specific circular citations from the legal_context.
</instruction>

<output_format>
Respond with a structured reply containing:
- Salutation to the authority
- Subject line referencing the notice
- Primary defense argument
- Supporting legal points with citations
- Formal closing
</output_format>
"""

# Audit prompt for verification
AUDIT_PROMPT = """
<task>
Verify the accuracy of this draft reply against the source laws.
</task>

<draft>
{draft_reply}
</draft>

<source_laws>
{legal_context}
</source_laws>

<checklist>
1. Are all cited circular numbers present in source_laws?
2. Are the legal claims accurate?
3. Is the time-bar calculation correct (if mentioned)?
4. Are there any invented or hallucinated citations?
</checklist>

<output>
Reply with:
- VALID: if all citations are correct
- INVALID: [list of issues] if problems found
</output>
"""
