"""
TaxShield — Agent 5: InEx Verifier (Strengthened)
Hallucination Mitigation via Introspection and Cross-Modal Verification.

5-stage pipeline:
  1. Citation Grounding (Ex)    — regex verifies section/circular references
  2. Multi-Sample Consistency (In) — SelfCheckGPT: generate alt draft, compare claims
  3. Chain-of-Verification (In)    — CoVe: generate questions, answer from KB, compare
  4. Self-Consistency (In)         — extract claims, detect internal contradictions
  5. Adversarial Challenge (In)    — LLM plays devil's advocate to find holes

Scoring weights: Citation=0.25, MultiSample=0.20, CoVe=0.20, Consistency=0.15, Adversarial=0.20
"""
import asyncio
import json
import re
import logging

from app.llm.router import llm_router
from app.agents.prompt_loader import load_prompt
from app.utils import parse_llm_extracted
from app.retrieval.section_kb import section_kb

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# Load prompts from markdown files
# ═══════════════════════════════════════════

CONSISTENCY_PROMPT = load_prompt("consistency_check.md")
ADVERSARIAL_PROMPT = load_prompt("adversarial_challenge.md")
MULTI_SAMPLE_DRAFT_PROMPT = load_prompt("multi_sample_draft.md")
MULTI_SAMPLE_COMPARE_PROMPT = load_prompt("multi_sample_compare.md")
COVE_QUESTIONS_PROMPT = load_prompt("cove_questions.md")
COVE_VERIFY_PROMPT = load_prompt("cove_verify.md")

# Scoring weights
WEIGHTS = {
    "citation_grounding": 0.25,
    "multi_sample": 0.20,
    "cove": 0.20,
    "self_consistency": 0.15,
    "adversarial": 0.20,
}


class Agent5Verifier:
    """
    InEx Verification Agent (Strengthened).

    Stage 1 (Ex):  Citation grounding — regex against known sections + KB
    Stage 2 (In):  Multi-sample consistency — SelfCheckGPT-style
    Stage 3 (In):  Chain-of-Verification — generate & answer verification Qs from KB
    Stage 4 (In):  Self-consistency — claim extraction + contradiction detection
    Stage 5 (In):  Adversarial challenge — LLM as opposing counsel
    """

    async def process(self, state_dict: dict) -> dict:
        """Run all 5 verification stages on the draft reply."""
        logger.info("=== Agent 5: InEx Verifier (5-stage) ===")

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

        entities = state_dict.get("entities", {})
        raw_text = state_dict.get("raw_text", "")[:1500]
        circulars = state_dict.get("retrieved_circulars", [])

        # ═══ Stage 1: Citation Grounding (synchronous, no LLM) ═══
        logger.info("Stage 1: Citation Grounding")
        citation_result = self._check_citations(draft_reply, circulars, entities)

        # ═══ Stages 2-5: Run in parallel (all use LLM) ═══
        # ═══ Stages 2-5: Run sequentially to avoid 30 Req/Min Rate Limits ═══
        logger.info("Stages 2-5: Running sequentially to respect Groq rate limits")

        stage_2 = await self._multi_sample_consistency(draft_reply, raw_text, entities, circulars)
        stage_3 = await self._chain_of_verification(draft_reply, entities)
        stage_4 = await self._check_consistency(draft_reply)
        stage_5 = await self._adversarial_challenge(draft_reply, raw_text, circulars)

        # ═══ Aggregate with weighted scoring ═══
        all_stages = {
            "citation_grounding": citation_result,
            "multi_sample": stage_2,
            "cove": stage_3,
            "self_consistency": stage_4,
            "adversarial": stage_5,
        }

        issues = []
        weighted_score = 0.0
        for name, result in all_stages.items():
            issues.extend(result.get("issues", []))
            weighted_score += result.get("score", 0.5) * WEIGHTS.get(name, 0.2)

        final_score = min(1.0, max(0.0, weighted_score))
        critical_count = sum(1 for i in issues if i.get("severity") == "critical")
        warning_count = sum(1 for i in issues if i.get("severity") == "warning")

        if critical_count > 0:
            status = "failed"
        elif warning_count > 3 or final_score < 0.6:
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
                "stages": {name: {k: v for k, v in r.items() if k != "issues"}
                           for name, r in all_stages.items()},
                "critical_issues": critical_count,
                "total_issues": len(issues),
            },
            "citation_report": citation_result,
        }

    # ═══════════════════════════════════════════
    # Stage 1: Citation Grounding (External)
    # ═══════════════════════════════════════════

    def _check_citations(self, draft: str, circulars: list, entities: dict) -> dict:
        """Check that legal sections/circulars cited in the draft are grounded in source docs."""
        issues = []

        cited_sections = set(re.findall(r'[Ss]ection\s+(\d+(?:\(\d+\))?)', draft))
        cited_circulars = set(re.findall(r'[Cc]ircular\s+(?:No\.?\s*)?(\d+/\d+)', draft))

        known_sections = set()
        if isinstance(entities, dict):
            for sec in entities.get("SECTIONS", []):
                known_sections.add(sec)
            llm_data = parse_llm_extracted(entities)
            if isinstance(llm_data, dict):
                for sec in llm_data.get("sections_referenced", []):
                    known_sections.add(str(sec))

        standard_sections = {
            "2", "7", "9", "10", "16", "17", "29", "37", "39", "44",
            "49", "50", "54", "61", "63", "65", "66", "67", "68",
            "73", "74", "75", "107", "112", "122", "125", "129", "130",
        }

        # Also check against curated KB sections
        kb_sections = set(section_kb.get_all_sections())

        for sec in cited_sections:
            base_sec = sec.split("(")[0]
            if base_sec not in known_sections and base_sec not in standard_sections and base_sec not in kb_sections:
                issues.append({
                    "stage": "citation_grounding",
                    "issue": f"Section {sec} cited but not found in notice, standard CGST sections, or curated KB",
                    "severity": "warning",
                    "location": f"Section {sec} reference",
                    "suggestion": "Verify this section applies to the case",
                })

        retrieved_ids = set()
        for circ in circulars:
            retrieved_ids.add(circ.get("doc_id", ""))

        for circ_ref in cited_circulars:
            if not any(circ_ref in rid for rid in retrieved_ids):
                issues.append({
                    "stage": "citation_grounding",
                    "issue": f"Circular {circ_ref} cited but not found in knowledge base",
                    "severity": "critical",
                    "location": f"Circular {circ_ref} reference",
                    "suggestion": "Remove this citation or verify it exists",
                })

        case_law_patterns = re.findall(
            r'(?:in|per|see)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\s+v\.?\s+[A-Z][\w\s]+)', draft
        )
        if case_law_patterns:
            for case in case_law_patterns[:3]:
                issues.append({
                    "stage": "citation_grounding",
                    "issue": f"Potential case law citation: '{case.strip()}' — cannot verify",
                    "severity": "critical",
                    "location": "Case law reference",
                    "suggestion": "Remove unverifiable case law — only cite CGST Act sections",
                })

        total_citations = len(cited_sections) + len(cited_circulars)
        if total_citations == 0:
            score = 0.8
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
    # Stage 2: Multi-Sample Consistency (SelfCheckGPT)
    # ═══════════════════════════════════════════

    async def _multi_sample_consistency(self, draft: str, notice_summary: str,
                                         entities: dict, circulars: list) -> dict:
        """Generate an alternative draft independently, then compare claims.
        Claims that appear in only one draft are flagged as low-confidence."""
        issues = []

        try:
            # Step 1: Generate alternative draft
            circulars_text = ", ".join([c.get("doc_id", "") for c in circulars]) if circulars else "None"
            entities_summary = json.dumps({
                "sections": entities.get("SECTIONS", []),
                "notice_type": entities.get("llm_extracted", {}).get("notice_type", "unknown")
                    if isinstance(entities.get("llm_extracted"), dict) else "unknown",
            })

            alt_prompt = MULTI_SAMPLE_DRAFT_PROMPT.format(
                notice_summary=notice_summary[:1500],
                entities=entities_summary,
                circulars=circulars_text,
            )
            alt_draft = await llm_router.generate(alt_prompt, risk_level="LOW", model_type="instant")

            # Step 2: Compare claims between original and alternative
            compare_prompt = MULTI_SAMPLE_COMPARE_PROMPT.format(
                draft_a=draft[:3000],
                draft_b=alt_draft[:3000],
            )
            raw = await llm_router.generate(compare_prompt, risk_level="LOW", json_mode=True, model_type="instant")

            try:
                comparisons = json.loads(raw)
                if not isinstance(comparisons, list):
                    comparisons = []
            except (json.JSONDecodeError, TypeError):
                comparisons = []

            # Flag low-confidence claims
            low_confidence = [c for c in comparisons if c.get("confidence") == "LOW"]
            high_confidence = [c for c in comparisons if c.get("confidence") == "HIGH"]

            for claim in low_confidence:
                issues.append({
                    "stage": "multi_sample_consistency",
                    "issue": f"Low-confidence claim: {claim.get('claim', 'unknown')} (Section {claim.get('section', '?')})",
                    "severity": "warning",
                    "location": f"Section {claim.get('section', '?')}",
                    "suggestion": claim.get("reason", "Verify this claim independently"),
                })

            total = len(comparisons)
            if total == 0:
                score = 0.7  # Couldn't extract claims — moderate confidence
            else:
                score = len(high_confidence) / total

            logger.info(f"Multi-sample: {len(high_confidence)} HIGH, {len(low_confidence)} LOW out of {total} claims")

            return {
                "score": round(score, 2),
                "high_confidence_claims": len(high_confidence),
                "low_confidence_claims": len(low_confidence),
                "total_claims_compared": total,
                "issues": issues,
            }

        except Exception as e:
            logger.warning(f"Multi-sample consistency failed (non-fatal): {e}")
            return {
                "score": 0.5,
                "high_confidence_claims": 0,
                "low_confidence_claims": 0,
                "total_claims_compared": 0,
                "issues": [{
                    "stage": "multi_sample_consistency",
                    "issue": f"Multi-sample check could not be completed: {str(e)}",
                    "severity": "info",
                    "location": "N/A",
                    "suggestion": "Manual review recommended",
                }],
            }

    # ═══════════════════════════════════════════
    # Stage 3: Chain-of-Verification (CoVe)
    # ═══════════════════════════════════════════

    async def _chain_of_verification(self, draft: str, entities: dict) -> dict:
        """CoVe: generate verification questions → answer from KB → compare to draft.
        Uses curated KB as ground truth, NOT the LLM's parametric memory."""
        issues = []

        try:
            # Step 1: Generate verification questions
            q_prompt = COVE_QUESTIONS_PROMPT.format(draft_text=draft[:4000])
            raw_questions = await llm_router.generate(q_prompt, risk_level="LOW", json_mode=True, model_type="instant")

            try:
                questions = json.loads(raw_questions)
                if not isinstance(questions, list):
                    questions = []
            except (json.JSONDecodeError, TypeError):
                questions = []

            if not questions:
                return {"score": 0.7, "questions_generated": 0, "verified": 0,
                        "refuted": 0, "unverifiable": 0, "issues": []}

            # Step 2: Gather relevant KB content for answering the questions
            sections = entities.get("SECTIONS", [])
            kb_results = section_kb.search_by_sections(sections) if sections else []

            # Also do a broad query search if we have few KB results
            if len(kb_results) < 2:
                kb_results.extend(section_kb.search_by_query("limitation period demand notice"))

            # Compile KB text for the verifier
            kb_content = "\n\n---\n\n".join([
                f"### {r.get('title', r.get('doc_id', 'Unknown'))}\n{r.get('full_text', r.get('text', ''))[:1000]}"
                for r in kb_results[:5]
            ])

            if not kb_content.strip():
                kb_content = "No curated KB content available for these sections."

            # Step 3: Answer questions from KB and compare to draft
            v_prompt = COVE_VERIFY_PROMPT.format(
                kb_content=kb_content[:6000],
                questions_json=json.dumps(questions[:6]),
            )
            raw_verdicts = await llm_router.generate(v_prompt, risk_level="LOW", json_mode=True, model_type="instant")

            try:
                verdicts = json.loads(raw_verdicts)
                if not isinstance(verdicts, list):
                    verdicts = []
            except (json.JSONDecodeError, TypeError):
                verdicts = []

            # Score based on verdicts
            verified = sum(1 for v in verdicts if v.get("verdict") == "VERIFIED")
            refuted = sum(1 for v in verdicts if v.get("verdict") == "REFUTED")
            unverifiable = sum(1 for v in verdicts if v.get("verdict") == "UNVERIFIABLE")

            for v in verdicts:
                if v.get("verdict") == "REFUTED":
                    issues.append({
                        "stage": "chain_of_verification",
                        "issue": f"CoVe REFUTED: {v.get('question', 'unknown')}",
                        "severity": "critical",
                        "location": v.get("draft_claim", "N/A"),
                        "suggestion": v.get("explanation", "Verify against CGST Act"),
                    })
                elif v.get("verdict") == "UNVERIFIABLE":
                    issues.append({
                        "stage": "chain_of_verification",
                        "issue": f"CoVe UNVERIFIABLE: {v.get('question', 'unknown')}",
                        "severity": "info",
                        "location": v.get("draft_claim", "N/A"),
                        "suggestion": "Claim could not be verified against curated KB",
                    })

            total = len(verdicts)
            if total == 0:
                score = 0.7
            else:
                score = (verified + unverifiable * 0.5) / total

            logger.info(f"CoVe: {verified} verified, {refuted} refuted, {unverifiable} unverifiable")

            return {
                "score": round(score, 2),
                "questions_generated": len(questions),
                "verified": verified,
                "refuted": refuted,
                "unverifiable": unverifiable,
                "issues": issues,
            }

        except Exception as e:
            logger.warning(f"Chain-of-verification failed (non-fatal): {e}")
            return {
                "score": 0.5,
                "questions_generated": 0,
                "verified": 0, "refuted": 0, "unverifiable": 0,
                "issues": [{
                    "stage": "chain_of_verification",
                    "issue": f"CoVe check could not be completed: {str(e)}",
                    "severity": "info",
                    "location": "N/A",
                    "suggestion": "Manual review recommended",
                }],
            }

    # ═══════════════════════════════════════════
    # Stage 4: Self-Consistency Check
    # ═══════════════════════════════════════════

    async def _check_consistency(self, draft: str) -> dict:
        """Extract key claims from the draft and check for internal contradictions."""
        issues = []

        try:
            prompt = CONSISTENCY_PROMPT.format(draft_text=draft[:4000])
            raw = await llm_router.generate(prompt, risk_level="LOW", json_mode=True, model_type="instant")

            try:
                claims = json.loads(raw)
                if not isinstance(claims, list):
                    claims = []
            except (json.JSONDecodeError, TypeError):
                claims = []

            section_claims = {}
            for claim in claims:
                sec = claim.get("section_cited", "")
                if sec:
                    section_claims.setdefault(sec, []).append(claim.get("claim", ""))

            for sec, claim_list in section_claims.items():
                if len(claim_list) > 1:
                    combined = " ".join(claim_list).lower()
                    contradiction_pairs = [
                        ("applicable", "not applicable"),
                        ("liable", "not liable"),
                        ("time-barred", "within limitation"),
                        ("valid", "invalid"),
                        ("mandatory", "optional"),
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
    # Stage 5: Adversarial Challenge
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

            raw = await llm_router.generate(prompt, risk_level="LOW", json_mode=True, model_type="instant")

            try:
                adv_issues = json.loads(raw)
                if not isinstance(adv_issues, list):
                    adv_issues = []
            except (json.JSONDecodeError, TypeError):
                adv_issues = []

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
