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
