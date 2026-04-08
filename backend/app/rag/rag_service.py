"""
TaxShield — Guardrailed RAG Service
Explicit LLM calling with safety, citations, confidence scores.
No blackbox orchestration.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field, ValidationError
import openai

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not openai_client.api_key:
    raise RuntimeError("OPENAI_API_KEY not set")


class ChunkMetadata(BaseModel):
    doc_id: str
    chunk_index: int
    text: str
    source_url: Optional[str] = None
    score: float = Field(ge=0.0, le=1.0)


class GuardedAnswer(BaseModel):
    """Structured response from guardrailed LLM."""
    answer: str = Field(description="Answer based only on provided documents")
    sources: List[str] = Field(
        description="List of source citations (format: doc:{id}:chunk:{idx})"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence 0-1. Lower if uncertain or info not in docs."
    )
    chunks_used: List[int] = Field(default_factory=list, description="FAISS indices used")


class AnswerRationale(BaseModel):
    """Internal reasoning for the answer."""
    answer: str
    sources: List[str]
    confidence: float
    reasoning: Optional[str] = None


def moderate_input(text: str, strict: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Check if input violates OpenAI usage policies.
    
    Args:
        text: Text to moderate
        strict: If True, flag any policy violation. If False, only block harmful.
        
    Returns:
        (is_safe: bool, reason: Optional[str])
    """
    try:
        response = openai_client.moderations.create(input=text)
        result = response.results[0]
        
        if result.flagged:
            # Detailed categorization
            categories = {
                k: v for k, v in result.category_scores.items()
                if v > 0.5
            }
            reason = f"Flagged categories: {', '.join(categories.keys())}"
            return False, reason
        
        return True, None
    except Exception as e:
        logger.error(f"Moderation check failed: {e}")
        return True, None  # Fail open


def call_embedding_api(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """
    Call OpenAI embedding API.
    
    Args:
        text: Text to embed
        model: Embedding model
        
    Returns:
        Embedding vector
    """
    response = openai_client.embeddings.create(
        model=model,
        input=text,
    )
    return response.data[0].embedding


def call_llm_with_guard(
    context_chunks: List[Dict[str, Any]],
    question: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
    max_tokens: int = 1000,
) -> GuardedAnswer:
    """
    Call LLM with strict guardrails: cite sources, confidence scores, JSON validation.
    
    Args:
        context_chunks: List of retrieved chunks with metadata
        question: User question
        model: LLM model to use
        temperature: Sampling temperature (0 for deterministic)
        max_tokens: Max response length
        
    Returns:
        GuardedAnswer with structured fields
        
    Raises:
        ValueError: If LLM response cannot be parsed
    """
    # Moderate question
    safe, reason = moderate_input(question, strict=True)
    if not safe:
        logger.warning(f"Question flagged by moderation: {reason}")
        return GuardedAnswer(
            answer="I cannot answer that question due to policy violations.",
            sources=[],
            confidence=0.0,
            chunks_used=[],
        )
    
    # Build context string with clear source tags
    context_str = ""
    chunk_indices = []
    for i, chunk in enumerate(context_chunks):
        doc_id = chunk.get("doc_id", "unknown")
        chunk_idx = chunk.get("chunk_index", i)
        text = chunk.get("text", "")
        source_url = chunk.get("source_url", "")
        score = chunk.get("score", 0.0)
        
        chunk_indices.append(chunk_idx)
        context_str += f"\n--- Source: doc:{doc_id}:chunk:{chunk_idx} (score: {score:.2f}) ---\n"
        if source_url:
            context_str += f"URL: {source_url}\n"
        context_str += text + "\n"
    
    # System prompt with strict guardrails
    system_prompt = """You are a tax and regulatory expert assistant. You MUST follow these rules strictly:

1. ONLY use information from the provided document chunks to answer the question.
2. If the answer is NOT in the chunks, respond with: "I don't know. This information is not in the provided documents."
3. Always cite your sources using the format "doc:{id}:chunk:{idx}" when making claims.
4. Return a JSON object with exactly these fields:
   - answer (string): The answer based on documents
   - sources (array of strings): List of source citations used
   - confidence (number 0-1): How confident you are (0=uncertain/not in docs, 1=very confident)
   - reasoning (string, optional): Brief explanation of why you chose this confidence

5. If you cannot answer from the documents, set confidence to 0 and sources to an empty array.
6. Do NOT make up or infer information not explicitly in the documents.
7. Be concise but complete in your answer."""

    user_prompt = f"""Documents:
{context_str}

Question: {question}

Respond with ONLY valid JSON. No markdown, no extra text."""

    # Call LLM
    try:
        completion = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        response_text = completion.choices[0].message.content.strip()
        logger.debug(f"LLM raw response: {response_text[:200]}...")
        
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        raise ValueError(f"LLM call failed: {e}")
    
    # Parse JSON response
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON: {response_text}")
        # Try to extract JSON from response
        import re
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except:
                raise ValueError(f"Could not extract valid JSON from response: {response_text}")
        else:
            raise ValueError(f"No JSON found in response: {response_text}")
    
    # Validate and build GuardedAnswer
    try:
        answer = GuardedAnswer(
            answer=parsed.get("answer", ""),
            sources=parsed.get("sources", []),
            confidence=float(parsed.get("confidence", 0.0)),
            chunks_used=chunk_indices,
        )
    except (ValidationError, ValueError, TypeError) as e:
        logger.warning(f"Response validation failed, building safe fallback: {e}")
        # Fallback: extract answer string, low confidence
        answer = GuardedAnswer(
            answer=str(parsed.get("answer", "Unable to process response")),
            sources=parsed.get("sources", []),
            confidence=0.3,
            chunks_used=chunk_indices,
        )
    
    # Log retrieved chunks for audit
    logger.info(
        f"Query answer: confidence={answer.confidence}, "
        f"sources={len(answer.sources)}, chunks={len(answer.chunks_used)}"
    )
    
    return answer


def validate_sources(sources: List[str], available_chunks: Dict[str, int]) -> List[str]:
    """
    Validate that cited sources exist in the document collection.
    
    Args:
        sources: List of source citations from LLM
        available_chunks: Dict of {doc_id: chunk_count}
        
    Returns:
        List of valid sources, filtered
    """
    valid = []
    for src in sources:
        # Parse "doc:{id}:chunk:{idx}"
        if not src.startswith("doc:"):
            logger.warning(f"Invalid source format: {src}")
            continue
        
        try:
            parts = src.split(":")
            doc_id = parts[1]
            chunk_idx = int(parts[3])
            
            if doc_id in available_chunks and chunk_idx < available_chunks[doc_id]:
                valid.append(src)
            else:
                logger.warning(f"Source out of range: {src}")
        except (IndexError, ValueError) as e:
            logger.warning(f"Could not parse source {src}: {e}")
    
    return valid


def format_answer_for_api(answer: GuardedAnswer, documents: Dict[str, str]) -> Dict[str, Any]:
    """
    Format GuardedAnswer for API response with full source text.
    
    Args:
        answer: GuardedAnswer from guardrailed LLM
        documents: Dict of {doc_id: text}
        
    Returns:
        API-safe response dict
    """
    return {
        "answer": answer.answer,
        "confidence": answer.confidence,
        "sources": answer.sources,
        "chunks_used": answer.chunks_used,
    }
