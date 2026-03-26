"""
TaxShield — Agent 5: InEx Verifier
Hallucination Mitigation via Introspection and Cross-Modal Verification.

Three stages:
  1. Citation Grounding — verify every legal reference against retrieved docs
  2. Self-Consistency  — re-generate key claims and flag contradictions
  3. Adversarial Challenge — LLM plays devil's advocate to find holes

Runs after Agent 4 (Drafter), populates accuracy_report and citation_report.
"""
import json
import re
import logging

from app.llm.router import llm_router
from app.agents.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# Load prompts from markdown files (WISC: procedural memory)
# ═══════════════════════════════════════════

CONSISTENCY_PROMPT = load_prompt("consistency_check.md")
ADVERSARIAL_PROMPT = load_prompt("adversarial_challenge.md")


class Agent5Verifier:
    """
    InEx Verification Agent.

    Stage 1 (Introspection): Citation grounding against retrieved documents
    Stage 2 (Introspection): Self-consistency via claim extraction + cross-check
    Stage 3 (Cross-Modal):   Adversarial challenge from opposing perspective
    """

    async def process(self, state_dict: dict) -> dict:
        """Run all three verification stages on the draft reply."""
        logger.info("=== Agent 5: InEx Verifier ===")

        draft_reply = state_dict.get("draft_reply", "")
        if not draft_reply:
            logger.warning("No draft to verify — skipping InEx")
            return {
                "current_agent": "agent5",
                "verification_status": "skipped",
                "verification_score": 0.0,
                "verification_issues": [],
                "accuracy_report": {"status": "skipped", "reason": "no_draft"},
                "citation_report": {"status": "skipped"},
            }

        issues = []
        scores = []

        # ═══ Stage 1: Citation Grounding ═══
        logger.info("Stage 1: Citation Grounding")
        citation_result = self._check_citations(
            draft_reply,
            state_dict.get("retrieved_circulars", []),
            state_dict.get("entities", {}),
        )
        issues.extend(citation_result["issues"])
        scores.append(citation_result["score"])

        # ═══ Stage 2: Self-Consistency ═══
        logger.info("Stage 2: Self-Consistency Check")
        consistency_result = await self._check_consistency(draft_reply)
        issues.extend(consistency_result["issues"])
        scores.append(consistency_result["score"])

        # ═══ Stage 3: Adversarial Challenge ═══
        logger.info("Stage 3: Adversarial Challenge")
        adversarial_result = await self._adversarial_challenge(
            draft_reply,
            state_dict.get("raw_text", "")[:1500],
            state_dict.get("retrieved_circulars", []),
        )
        issues.extend(adversarial_result["issues"])
        scores.append(adversarial_result["score"])

        # ═══ Aggregate ═══
        final_score = sum(scores) / len(scores) if scores else 0.0
        critical_count = sum(1 for i in issues if i.get("severity") == "critical")
        warning_count = sum(1 for i in issues if i.get("severity") == "warning")

        if critical_count > 0:
            status = "failed"
        elif warning_count > 2:
            status = "needs_review"
        elif final_score >= 0.7:
            status = "passed"
        else:
            status = "needs_review"

        logger.info(
            f"InEx Verification: score={final_score:.2f}, status={status}, "
            f"issues={len(issues)} (critical={critical_count}, warnings={warning_count})"
        )

        return {
            "current_agent": "agent5",
            "verification_status": status,
            "verification_score": round(final_score, 2),
            "verification_issues": issues,
            "accuracy_report": {
                "status": status,
                "score": round(final_score, 2),
                "stages": {
                    "citation_grounding": citation_result,
                    "self_consistency": consistency_result,
                    "adversarial_challenge": adversarial_result,
                },
                "critical_issues": critical_count,
                "total_issues": len(issues),
            },
            "citation_report": citation_result,
        }

    # ═══════════════════════════════════════════
    # Stage 1: Citation Grounding
    # ═══════════════════════════════════════════

    def _check_citations(self, draft: str, circulars: list, entities: dict) -> dict:
        """Check that legal sections/circulars cited in the draft are grounded in source docs."""
        issues = []

        # Extract section references from draft (e.g., "Section 73", "Section 16(4)")
        cited_sections = set(re.findall(r'[Ss]ection\s+(\d+(?:\(\d+\))?)', draft))

        # Extract circular references from draft
        cited_circulars = set(re.findall(r'[Cc]ircular\s+(?:No\.?\s*)?(\d+/\d+)', draft))

        # Check sections against entities
        known_sections = set()
        if isinstance(entities, dict):
            for sec in entities.get("SECTIONS", []):
                known_sections.add(sec)
            llm_data = entities.get("llm_extracted", {})
            if isinstance(llm_data, str):
                try:
                    llm_data = json.loads(llm_data)
                except (json.JSONDecodeError, TypeError):
                    llm_data = {}
            if isinstance(llm_data, dict):
                for sec in llm_data.get("sections_referenced", []):
                    known_sections.add(str(sec))

        # Well-known CGST sections that are always valid
        standard_sections = {
            "2", "7", "9", "10", "16", "17", "29", "37", "39", "44",
            "49", "50", "54", "61", "63", "65", "66", "67", "68",
            "73", "74", "75", "107", "112", "122", "125", "129", "130",
        }

        # Flag sections not in source entities AND not standard
        for sec in cited_sections:
            base_sec = sec.split("(")[0]
            if base_sec not in known_sections and base_sec not in standard_sections:
                issues.append({
                    "stage": "citation_grounding",
                    "issue": f"Section {sec} cited but not found in notice or standard CGST sections",
                    "severity": "warning",
                    "location": f"Section {sec} reference",
                    "suggestion": "Verify this section applies to the case",
                })

        # Check circulars against retrieved docs
        retrieved_ids = set()
        for circ in circulars:
            doc_id = circ.get("doc_id", "")
            retrieved_ids.add(doc_id)

        for circ_ref in cited_circulars:
            if not any(circ_ref in rid for rid in retrieved_ids):
                issues.append({
                    "stage": "citation_grounding",
                    "issue": f"Circular {circ_ref} cited but not found in knowledge base",
                    "severity": "critical",
                    "location": f"Circular {circ_ref} reference",
                    "suggestion": "Remove this citation or verify it exists",
                })

        # Check for fabricated case law (the prompt says "do NOT fabricate", but verify)
        case_law_patterns = re.findall(
            r'(?:in|per|see)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\s+v\.?\s+[A-Z][\w\s]+)', draft
        )
        if case_law_patterns:
            for case in case_law_patterns[:3]:
                issues.append({
                    "stage": "citation_grounding",
                    "issue": f"Potential case law citation found: '{case.strip()}' — cannot verify against knowledge base",
                    "severity": "critical",
                    "location": "Case law reference",
                    "suggestion": "Remove unverifiable case law citation — only cite CGST Act sections",
                })

        # Compute score
        total_citations = len(cited_sections) + len(cited_circulars)
        if total_citations == 0:
            score = 0.8  # No citations to check — moderate confidence
        else:
            critical_ratio = sum(1 for i in issues if i["severity"] == "critical") / max(total_citations, 1)
            score = max(0.0, 1.0 - critical_ratio)

        return {
            "score": round(score, 2),
            "sections_cited": list(cited_sections),
            "circulars_cited": list(cited_circulars),
            "grounded_count": total_citations - sum(1 for i in issues if i["severity"] == "critical"),
            "total_cited": total_citations,
            "issues": issues,
        }

    # ═══════════════════════════════════════════
    # Stage 2: Self-Consistency Check
    # ═══════════════════════════════════════════

    async def _check_consistency(self, draft: str) -> dict:
        """Extract key claims from the draft and check for internal contradictions."""
        issues = []

        try:
            prompt = CONSISTENCY_PROMPT.format(draft_text=draft[:4000])
            raw = await llm_router.generate(prompt, risk_level="LOW", json_mode=True)

            # Parse claims
            try:
                claims = json.loads(raw)
                if not isinstance(claims, list):
                    claims = []
            except (json.JSONDecodeError, TypeError):
                claims = []

            # Check for contradictions: same section cited for opposite conclusions
            section_claims = {}
            for claim in claims:
                sec = claim.get("section_cited", "")
                if sec:
                    section_claims.setdefault(sec, []).append(claim.get("claim", ""))

            for sec, claim_list in section_claims.items():
                if len(claim_list) > 1:
                    # Check if claims seem contradictory (simple heuristic)
                    combined = " ".join(claim_list).lower()
                    contradiction_pairs = [
                        ("applicable", "not applicable"),
                        ("liable", "not liable"),
                        ("time-barred", "within limitation"),
                    ]
                    for pos, neg in contradiction_pairs:
                        if pos in combined and neg in combined:
                            issues.append({
                                "stage": "self_consistency",
                                "issue": f"Contradictory claims about Section {sec}: both '{pos}' and '{neg}' stated",
                                "severity": "critical",
                                "location": f"Section {sec} arguments",
                                "suggestion": "Reconcile contradictory positions",
                            })

            score = 1.0 if not issues else max(0.3, 1.0 - (len(issues) * 0.25))

            return {
                "score": round(score, 2),
                "claims_extracted": len(claims),
                "contradictions_found": len(issues),
                "issues": issues,
            }

        except Exception as e:
            logger.warning(f"Self-consistency check failed (non-fatal): {e}")
            return {
                "score": 0.5,
                "claims_extracted": 0,
                "contradictions_found": 0,
                "issues": [{
                    "stage": "self_consistency",
                    "issue": f"Consistency check could not be completed: {str(e)}",
                    "severity": "info",
                    "location": "N/A",
                    "suggestion": "Manual review recommended",
                }],
            }

    # ═══════════════════════════════════════════
    # Stage 3: Adversarial Challenge
    # ═══════════════════════════════════════════

    async def _adversarial_challenge(self, draft: str, notice_summary: str, circulars: list) -> dict:
        """Play devil's advocate — find weaknesses from the opposing side."""
        issues = []

        circulars_text = ", ".join([c.get("doc_id", "unknown") for c in circulars]) if circulars else "None available"

        try:
            prompt = ADVERSARIAL_PROMPT.format(
                notice_summary=notice_summary[:1500],
                draft_text=draft[:4000],
                circulars_available=circulars_text,
            )

            raw = await llm_router.generate(prompt, risk_level="LOW", json_mode=True)

            try:
                adv_issues = json.loads(raw)
                if not isinstance(adv_issues, list):
                    adv_issues = []
            except (json.JSONDecodeError, TypeError):
                adv_issues = []

            # Convert to our format
            for item in adv_issues:
                issues.append({
                    "stage": "adversarial_challenge",
                    "issue": item.get("issue", "Unknown issue"),
                    "severity": item.get("severity", "info"),
                    "location": item.get("location", "N/A"),
                    "suggestion": item.get("suggestion", "Review manually"),
                })

            critical_count = sum(1 for i in issues if i.get("severity") == "critical")
            warning_count = sum(1 for i in issues if i.get("severity") == "warning")
            score = max(0.0, 1.0 - (critical_count * 0.3) - (warning_count * 0.1))

            return {
                "score": round(score, 2),
                "challenges_found": len(issues),
                "issues": issues,
            }

        except Exception as e:
            logger.warning(f"Adversarial challenge failed (non-fatal): {e}")
            return {
                "score": 0.5,
                "challenges_found": 0,
                "issues": [{
                    "stage": "adversarial_challenge",
                    "issue": f"Adversarial check could not be completed: {str(e)}",
                    "severity": "info",
                    "location": "N/A",
                    "suggestion": "Manual review recommended",
                }],
            }


# Singleton
agent5 = Agent5Verifier()
