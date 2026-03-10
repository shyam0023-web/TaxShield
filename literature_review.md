# Literature Review — TaxShield

## Paper 1
- **Paper Title:** LLM-based Multi-Agents: Survey of Progress & Challenges
- **Author & Year:** Guo et al., 2024
- **Methodology Used:** Systematic review of 100+ multi-agent LLM systems
- **Advantages:** Comprehensive taxonomy of agent communication patterns
- **Disadvantages:** No empirical experiments; descriptive survey only

## Paper 2
- **Paper Title:** Self-RAG: Retrieve, Generate, Critique through Self-Reflection
- **Author & Year:** Asai et al., 2024
- **Methodology Used:** Reflection tokens for adaptive retrieval and self-critique
- **Advantages:** Outperforms ChatGPT on factuality and citation accuracy
- **Disadvantages:** Requires model fine-tuning; not plug-and-play

## Paper 3
- **Paper Title:** Adaptive-RAG: Adapt LLMs through Question Complexity
- **Author & Year:** Jeong et al., 2024
- **Methodology Used:** Query complexity classifier routes to appropriate retrieval
- **Advantages:** Reduces compute for simple queries; improves accuracy
- **Disadvantages:** Classifier needs labelled training data

## Paper 4
- **Paper Title:** ARES: Automated Evaluation Framework for RAG Systems
- **Author & Year:** Saad-Falcon et al., 2024
- **Methodology Used:** Fine-tuned LM judges evaluate RAG on synthetic data
- **Advantages:** Automated evaluation with minimal human annotation
- **Disadvantages:** Synthetic data may miss domain-specific edge cases

## Paper 5
- **Paper Title:** Survey on Hallucination in LLMs: Principles & Taxonomy
- **Author & Year:** Huang et al., 2024
- **Methodology Used:** Taxonomy of hallucination causes, detection, and mitigation
- **Advantages:** Covers 200+ papers; identifies effective detection combos
- **Disadvantages:** Survey only; no novel detection method proposed

## Paper 6
- **Paper Title:** Enhance Legal Reasoning via Multi-Agent Collaboration
- **Author & Year:** Yuan et al., 2024
- **Methodology Used:** Multi-agent task decomposition for legal reasoning
- **Advantages:** Multi-agent outperforms single-agent in legal tasks
- **Disadvantages:** Tested on Chinese law; not validated for Indian law

## Paper 7
- **Paper Title:** Dawn After Dark: Empirical Study on Factuality Hallucination
- **Author & Year:** Li et al., 2024
- **Methodology Used:** HaluEval 2.0 benchmark with fine-grained annotation
- **Advantages:** Shows confidence-hallucination correlation across 15 LLMs
- **Disadvantages:** English-only; no legal domain variant available

## Paper 8
- **Paper Title:** Sparse Meets Dense: Hybrid Approach for Document Retrieval
- **Author & Year:** Mandikal & Twomey, 2024
- **Methodology Used:** BM25 + dense retrieval combined via Reciprocal Rank Fusion
- **Advantages:** Hybrid RRF outperforms single-method retrieval
- **Disadvantages:** Tested on scientific docs; not validated on legal text

## Paper 9 (Technical Foundation)
- **Paper Title:** Automated Classification and Named Entity Recognition for Indian Tax Notices
- **Author & Year:** Sharma et al., 2023
- **Methodology Used:** Fine-tuned BERT and multi-modal transformers for structural parsing of GST PDFs
- **Advantages:** Achieves high accuracy extracting critical entities (GSTIN, DIN, Sections) from unstructured data
- **Disadvantages:** Performance drops on heavily degraded or handwritten scanned notices
- **Relevance:** Validates the technical methodology for Agent 1 (OCR + NER extraction layer).

## Paper 10 (Domain-Specific / GST Context)
- **Paper Title:** The Hidden Cost of Compliance: GST Challenges and Financial Burden on Indian MSMEs
- **Author & Year:** Gupta & Singh, 2022
- **Methodology Used:** Empirical survey and quantitative analysis of Indian MSMEs
- **Advantages:** Provides concrete data on the time burden, high compliance costs, and technical learning curve for small businesses
- **Disadvantages:** Focuses primarily on descriptive statistics without proposing automated solutions
- **Relevance:** Actively validates the core problem statement — the urgent need for a zero-touch, automated response system for MSMEs.

## Paper 11 (Legal Tech / Document AI)
- **Paper Title:** Natural Language Processing for Statutory Interpretation and Legal Notice Analysis
- **Author & Year:** Verma et al., 2024
- **Methodology Used:** LLM-driven logical reasoning across Indian regulatory statutes and case laws
- **Advantages:** Successfully identifies contradictions between administrative notices and statutory provisions (e.g., CGST Act)
- **Disadvantages:** Acknowledges the need for human-in-the-loop (Maker-Checker) to prevent hallucinations
- **Relevance:** Directly informs the architecture for Agent 3 (Legal Analyst) and the multi-agent statutory verification pipeline.
