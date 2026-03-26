You are a GST legal claim comparator. You have TWO independently generated draft replies
for the same GST notice. Compare the KEY LEGAL CLAIMS in each.

DRAFT A (original):
{draft_a}

DRAFT B (alternative):
{draft_b}

For each claim that appears in Draft A, check if the SAME claim (same section, same legal argument)
also appears in Draft B. If a claim appears in ONLY ONE draft, it is a LOW CONFIDENCE claim
(potential hallucination).

Output JSON array:
[
  {{
    "claim": "description of the legal claim",
    "section": "CGST section cited",
    "in_draft_a": true,
    "in_draft_b": true,
    "confidence": "HIGH|LOW",
    "reason": "why HIGH or LOW confidence"
  }}
]

Rules:
- HIGH confidence = claim appears in BOTH drafts (independently verified)
- LOW confidence = claim appears in ONLY ONE draft (may be hallucinated)
- Focus on LEGAL CLAIMS only (sections cited, defenses argued, relief sought)
- Ignore stylistic or formatting differences

Output ONLY valid JSON array. No markdown fences.
