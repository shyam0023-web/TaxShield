"""
TaxShield — RAG (Retrieval Augmented Generation) Module
Domain-specific RAG for tax documents with OCR+PDF support and intelligent reporting.

Components:
- tax_domain_service: GST/IT-specific LLM guardrails
- ocr_processor: Enhanced PDF/OCR extraction with structure analysis
- report_generator: Context-aware report generation (not templates)
- vector_store: FAISS-backed document indexing
- rag_service: General-purpose guardrailed LLM calling
"""

from .vector_store import VectorStore, chunk_text, EMBEDDING_DIM
from .rag_service import (
    call_embedding_api,
    call_llm_with_guard,
    moderate_input,
    GuardedAnswer,
    ChunkMetadata,
)
from .tax_domain_service import (
    TaxGuardedLLMService,
    TaxLawValidator,
    HallucinationDetector,
    TaxDomain,
    NoticeType,
    RiskLevel,
    tax_llm_service,
)
from .ocr_processor import (
    EnhancedPDFProcessor,
    TaxDocumentParser,
    pdf_processor,
)
from .report_generator import (
    IntelligentReportGenerator,
    ContextAnalyzer,
    ReportType,
    report_generator,
)

__all__ = [
    # Vector store
    "VectorStore",
    "chunk_text",
    "EMBEDDING_DIM",
    # General RAG
    "call_embedding_api",
    "call_llm_with_guard",
    "moderate_input",
    "GuardedAnswer",
    # Tax domain
    "TaxGuardedLLMService",
    "TaxLawValidator",
    "HallucinationDetector",
    "TaxDomain",
    "NoticeType",
    "RiskLevel",
    "tax_llm_service",
    # PDF/OCR
    "EnhancedPDFProcessor",
    "TaxDocumentParser",
    "pdf_processor",
    # Reporting
    "IntelligentReportGenerator",
    "ContextAnalyzer",
    "ReportType",
    "report_generator",
]
