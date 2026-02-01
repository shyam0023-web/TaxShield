"""Jinja2 prompt templates for LLM"""
DRAFTING_PROMPT = """
You are a GST legal expert. Draft a reply to this notice:
Notice: {notice_text}
Relevant Laws: {relevant_laws}
Write a professional legal reply.
"""
AUDIT_PROMPT = """
Check this draft for accuracy:
Draft: {draft_reply}
Source Laws: {relevant_laws}
Are all citations correct? Reply YES or NO with reason.
"""
