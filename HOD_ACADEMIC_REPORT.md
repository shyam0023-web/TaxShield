# Mathematical & Methodological Framework: TaxShield AI

This document provides the formal academic specifications, mathematical models, and algorithmic definitions that govern the TaxShield Agentic Processing Pipeline.

## 1. Methodology / Approach

TaxShield utilizes a **Multi-Agent Directed Acyclic Graph (DAG) architecture** combined with **Retrieval-Augmented Generation (RAG)** to parse, verify, and generate legal responses. 

Unlike traditional zero-shot LLM wrappers, the approach is pipelined into discrete, verifiable stages:
1.  **Deterministic Extraction (Agent 1):** Optical Character Recognition (OCR) combined with token-classification NER to extract strictly typed entities (GSTIN, Financial Year, Demand Amount).
2.  **Stochastic Triage (Agent 2 & 3):** LLMs operating at lower temperatures (`T = 0.1`) evaluate legal merits and assess procedural/time-barring risks.
3.  **Vector Retrieval:** A hybrid BM25 + dense vector semantic search against a corpus of GST laws and circulars to ground the LLM context.
4.  **Generative Drafting (Agent 4):** A high-parameter foundation model synthesizes the extracted entities and retrieved law into a coherent legal defense.

---

## 2. Mathematical Model

The TaxShield pipeline can be mathematically modeled as a Markov Decision Process (MDP) or a deterministic state-transition graph.

Let the initial legal Notice be defined as $N = (T, M)$ where $T$ is the raw text matrix and $M$ is the embedded metadata.

The state vector at time $t$ is $S_t$. The pipeline computes a sequence of transformations:

1. **Information Extraction (NER mapping):**
   $$E = f_\text{NER}(T) \rightarrow \{e_1, e_2, ..., e_n\}$$
   Where $E$ is the set of strictly defined entities (e.g., $e_\text{amount}$, $e_\text{date}$).

2. **Semantic Retrieval (RAG):**
   Given a query vector $\vec{q}$ (derived from $E$) and a document chunk vector $\vec{d_i}$, the similarity score is calculated using cosine similarity:
   $$\text{sim}(\vec{q}, \vec{d_i}) = \frac{\vec{q} \cdot \vec{d_i}}{||\vec{q}|| \times ||\vec{d_i}||}$$
   The top-$K$ documents $D_K$ are retrieved where $\text{sim}(\vec{q}, \vec{d_i}) \geq \tau$ (threshold).

3. **Generation:**
   The probability distribution of the drafted legal reply tokens $Y = (y_1, y_2, ..., y_m)$ given the context $X = (E \cup D_K)$:
   $$P(Y | X) = \prod_{i=1}^{m} P(y_i | y_{<i}, X)$$

---

## 3. Formal Algorithm Pseudocode

```text
Algorithm: Dynamic Agentic Legal Drafting (TaxShield Pipeline)
Input: raw_pdf_binary
Output: verified_legal_draft

1. Initialize PipelineState S 
2. S.raw_text ← OCR_Extract(raw_pdf_binary)
3. S.entities ← LLM_NER_Extract(S.raw_text)

4. function Agent2_Risk_Assessment(S):
5.     if S.entities.date < time_limit:
6.         S.is_time_barred ← True
7.         return RouteTo(Agent4) 
8.     else:
9.         S.risk_level ← CalculateRisk(S.entities)
10.        return RouteTo(Agent3)

11. function Agent3_Legal_Search(S):
12.     Q ← GenerateQueries(S.entities)
13.     S.retrieved_case_law ← VectorDB.Search(Q, top_k=5)
14.     return RouteTo(Agent4)

15. function Agent4_Master_Drafter(S):
16.     Prompt_Context ← {S.entities, S.retrieved_case_law, S.user_instructions}
17.     try:
18.         S.draft_reply ← LLM_Generate(Prompt_Context)
19.     except RateLimitError:
20.         S.draft_error ← "API Limit Reached"
21.     return S

22. ExecuteGraph(S)
```

---

## 4. Model Evaluation Equations

To ensure the statistical validity of the RAG (Retrieval-Augmented Generation) pipeline, the following metrics are calculated against a golden dataset of notices.

### A. Mean Reciprocal Rank (MRR)
Used to evaluate how high the *first* perfectly relevant legal circular appears in the search results.
$$ \text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i} $$
*(Where $\text{rank}_i$ is the position of the first relevant document for query $i$.)*

### B. Recall@K
Measures the proportion of relevant documents successfully retrieved within the top $K$ results.
$$ \text{Recall@K} = \frac{\text{Relevant Documents Retrieved in Top } K}{\text{Total Relevant Documents}} $$

### C. Normalized Discounted Cumulative Gain (NDCG)
Used to evaluate the *ranking quality* of retrieved legal clauses, penalizing highly relevant clauses that appear too low in the result list.
$$ \text{DCG}_p = \sum_{i=1}^{p} \frac{rel_i}{\log_2(i + 1)} $$
$$ \text{NDCG}_p = \frac{\text{DCG}_p}{\text{IDCG}_p} $$
*(Where $\text{IDCG}_p$ is the Ideal DCG if documents were sorted perfectly by relevance).*

---

## 5. Error Handling & Recovery Logic

The pipeline implements mathematical backoff and graceful degradation mechanisms to prevent system failure.

1. **Exponential Backoff for Rate Limits (429 Errors):**
   If the LLM endpoint rejects a request due to token exhaustion, the router implements exponential backoff.
   $$ \text{Wait Time} = \min(\text{base} \times 2^{retry\_count}, \text{max\_wait}) + \text{jitter} $$

2. **Graceful Degradation (Fallback Strategy):**
   - **OCR Failure:** If high-accuracy semantic OCR fails, the system falls back to regex-based text stripping via `PyMuPDF`.
   - **LLM NER Failure:** If the 8B Parameter model hallucinates JSON boundaries during extraction, the system falls back to fuzzy Regex parsing string-matching against GSTIN formats (`\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}`).

3. **State Rollback in LangGraph:**
   If Agent 4 (Drafter) throws an unhandled exception, the Directed Acyclic Graph intercepts the fault boundary and mutates the SQLite state matrix:
   ```python
   # State Mutation upon Failure
   if draft_error:
       notice.status = "error"
       notice.error_message = draft_error
       notice.draft_reply = null
   ```
   This prevents the frontend from displaying cached illusions of success (Ghost States).
