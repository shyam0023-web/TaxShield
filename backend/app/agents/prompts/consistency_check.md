You are a legal verification assistant. Given a draft reply to a GST notice,
extract the KEY LEGAL CLAIMS made in the draft. For each claim, output a JSON array of objects:

[
  {{"claim": "...", "section_cited": "...", "type": "procedural|substantive|factual"}}
]

DRAFT REPLY:
{draft_text}

Output ONLY valid JSON array. No markdown fences.
