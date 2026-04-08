"""
Supabase PostgreSQL Client for TaxShield
Handles all database operations with async support
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
from supabase import create_client, Client
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Async Supabase client wrapper for TaxShield database operations"""
    
    def __init__(self):
        self.url: str = os.getenv("SUPABASE_URL", "")
        self.service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
        self.anon_key: str = os.getenv("SUPABASE_KEY", "")
        self.client: Optional[Client] = None
        self.is_connected: bool = False
        
    async def connect(self) -> bool:
        """Initialize Supabase connection on app startup"""
        try:
            if not self.url or not self.service_key:
                logger.warning("⚠️ Supabase credentials missing. Falling back to SQLite.")
                return False
                
            # Use service_role key for admin operations
            self.client = create_client(self.url, self.service_key)
            
            # Test connection (Supabase Python client is synchronous)
            result = self.client.table("reports").select("id").limit(1).execute()
            
            self.is_connected = True
            logger.info("✅ Connected to Supabase PostgreSQL")
            return True
            
        except Exception as e:
            logger.error(f"❌ Supabase connection failed: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close Supabase connection on app shutdown"""
        if self.client:
            logger.info("Disconnecting from Supabase...")
            self.client = None
    
    # ==================== REPORTS TABLE ====================
    
    async def get_reports(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch all reports from Supabase"""
        try:
            if not self.is_connected:
                logger.warning("⚠️ Supabase not connected")
                return []
            
            result = self.client.table("reports").select("*").limit(limit).execute()
            return result.data if result.data else []
        except APIError as e:
            logger.error(f"Error fetching reports: {e}")
            return []
    
    async def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single report by ID"""
        try:
            if not self.is_connected:
                return None
            
            result = self.client.table("reports").select("*").eq("id", report_id).single().execute()
            return result.data
        except APIError as e:
            logger.error(f"Error fetching report {report_id}: {e}")
            return None
    
    async def create_report(self, report_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new report"""
        try:
            if not self.is_connected:
                return None
            
            # Add timestamps
            report_data["created_at"] = datetime.utcnow().isoformat()
            report_data["updated_at"] = datetime.utcnow().isoformat()
            
            result = self.client.table("reports").insert(report_data).execute()
            return result.data[0] if result.data else None
        except APIError as e:
            logger.error(f"Error creating report: {e}")
            return None
    
    async def update_report(self, report_id: str, report_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing report"""
        try:
            if not self.is_connected:
                return None
            
            report_data["updated_at"] = datetime.utcnow().isoformat()
            
            result = self.client.table("reports").update(report_data).eq("id", report_id).execute()
            return result.data[0] if result.data else None
        except APIError as e:
            logger.error(f"Error updating report {report_id}: {e}")
            return None
    
    async def delete_report(self, report_id: str) -> bool:
        """Delete a report"""
        try:
            if not self.is_connected:
                return False
            
            self.client.table("reports").delete().eq("id", report_id).execute()
            return True
        except APIError as e:
            logger.error(f"Error deleting report {report_id}: {e}")
            return False
    
    # ==================== REFINEMENTS TABLE ====================
    
    async def get_refinements(self, report_id: str) -> List[Dict[str, Any]]:
        """Fetch all refinements for a report"""
        try:
            if not self.is_connected:
                return []
            
            result = self.client.table("refinements").select("*").eq("report_id", report_id).execute()
            return result.data if result.data else []
        except APIError as e:
            logger.error(f"Error fetching refinements for {report_id}: {e}")
            return []
    
    async def create_refinement(self, refinement_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Save a report refinement"""
        try:
            if not self.is_connected:
                return None
            
            refinement_data["created_at"] = datetime.utcnow().isoformat()
            
            result = self.client.table("refinements").insert(refinement_data).execute()
            return result.data[0] if result.data else None
        except APIError as e:
            logger.error(f"Error creating refinement: {e}")
            return None
    
    # ==================== DOCUMENTS TABLE ====================
    
    async def get_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch all documents"""
        try:
            if not self.is_connected:
                return []
            
            result = self.client.table("documents").select("*").limit(limit).execute()
            return result.data if result.data else []
        except APIError as e:
            logger.error(f"Error fetching documents: {e}")
            return []
    
    async def create_document(self, doc_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new document record"""
        try:
            if not self.is_connected:
                return None
            
            doc_data["created_at"] = datetime.utcnow().isoformat()
            
            result = self.client.table("documents").insert(doc_data).execute()
            return result.data[0] if result.data else None
        except APIError as e:
            logger.error(f"Error creating document: {e}")
            return None
    
    # ==================== NOTICES TABLE ====================
    
    async def get_notices(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch all tax notices"""
        try:
            if not self.is_connected:
                return []
            
            result = self.client.table("notices").select("*").limit(limit).execute()
            return result.data if result.data else []
        except APIError as e:
            logger.error(f"Error fetching notices: {e}")
            return []
    
    async def create_notice(self, notice_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new tax notice record"""
        try:
            if not self.is_connected:
                return None
            
            notice_data["created_at"] = datetime.utcnow().isoformat()
            
            result = self.client.table("notices").insert(notice_data).execute()
            return result.data[0] if result.data else None
        except APIError as e:
            logger.error(f"Error creating notice: {e}")
            return None
    
    # ==================== SEARCH & FILTERS ====================
    
    async def search_reports_by_type(self, report_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search reports by type"""
        try:
            if not self.is_connected:
                return []
            
            result = self.client.table("reports").select("*").eq("report_type", report_type).limit(limit).execute()
            return result.data if result.data else []
        except APIError as e:
            logger.error(f"Error searching reports by type: {e}")
            return []
    
    async def search_reports_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search reports by status"""
        try:
            if not self.is_connected:
                return []
            
            result = self.client.table("reports").select("*").eq("status", status).limit(limit).execute()
            return result.data if result.data else []
        except APIError as e:
            logger.error(f"Error searching reports by status: {e}")
            return []
    
    # ==================== PGVECTOR RAG SUPPORT ====================
    
    async def get_or_create_document(self, doc_id: str, title: str, content_text: str, 
                                     source_url: Optional[str] = None, 
                                     metadata: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Get existing document or create new one"""
        try:
            if not self.is_connected:
                return None
            
            # Try to get existing
            result = self.client.table("documents").select("*").eq("doc_id", doc_id).single().execute()
            if result.data:
                return result.data
            
            # Create new
            doc_data = {
                "doc_id": doc_id,
                "title": title,
                "content_text": content_text,
                "source_url": source_url,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
            }
            result = self.client.table("documents").insert(doc_data).execute()
            return result.data[0] if result.data else None
        except APIError as e:
            logger.error(f"Error getting/creating document {doc_id}: {e}")
            return None
    
    async def add_document_chunk(self, document_id: int, chunk_index: int, chunk_text: str,
                                 embedding: List[float], embedding_model: str = "text-embedding-3-small",
                                 bm25_metadata: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Store document chunk with pgvector embedding"""
        try:
            if not self.is_connected:
                return None
            
            chunk_data = {
                "document_id": document_id,
                "chunk_index": chunk_index,
                "chunk_text": chunk_text,
                "embedding": embedding,  # pgvector will serialize this
                "embedding_model": embedding_model,
                "bm25_metadata": bm25_metadata or {},
                "created_at": datetime.utcnow().isoformat(),
            }
            result = self.client.table("document_chunks").insert(chunk_data).execute()
            return result.data[0] if result.data else None
        except APIError as e:
            logger.error(f"Error adding document chunk: {e}")
            return None
    
    async def search_chunks_by_embedding(self, embedding: List[float], 
                                        limit: int = 5,
                                        similarity_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Search document chunks using pgvector cosine similarity"""
        try:
            if not self.is_connected:
                return []
            
            # Call the pgvector search function we created in SQL
            # This uses the cosine distance operator (<=>)
            result = self.client.rpc(
                "search_chunks_by_embedding",
                {
                    "query_embedding": embedding,
                    "match_count": limit,
                    "similarity_threshold": similarity_threshold,
                }
            ).execute()
            
            return result.data if result.data else []
        except APIError as e:
            logger.error(f"Error searching chunks by embedding: {e}")
            return []
    
    async def get_document_chunks(self, document_id: int) -> List[Dict[str, Any]]:
        """Fetch all chunks for a specific document"""
        try:
            if not self.is_connected:
                return []
            
            result = self.client.table("document_chunks").select("*").eq("document_id", document_id).order("chunk_index", desc=False).execute()
            return result.data if result.data else []
        except APIError as e:
            logger.error(f"Error fetching document chunks: {e}")
            return []
    
    async def delete_document_chunks(self, doc_id: str) -> int:
        """Delete all chunks for a document (via SQL function)"""
        try:
            if not self.is_connected:
                return 0
            
            result = self.client.rpc("delete_document_chunks", {"doc_id": doc_id}).execute()
            return result.data if result.data else 0
        except APIError as e:
            logger.error(f"Error deleting document chunks: {e}")
            return 0
    
    async def log_rag_query(self, query_text: str, query_embedding: List[float],
                           results_count: int, top_chunks_used: List[Dict] = None,
                           llm_response_id: Optional[str] = None,
                           response_confidence: float = 0.5) -> Optional[Dict[str, Any]]:
        """Log RAG query for audit trail and analytics"""
        try:
            if not self.is_connected:
                return None
            
            query_data = {
                "query_text": query_text,
                "query_embedding": query_embedding,
                "results_count": results_count,
                "top_chunks_used": top_chunks_used or [],
                "llm_response_id": llm_response_id,
                "response_confidence": response_confidence,
                "created_at": datetime.utcnow().isoformat(),
            }
            result = self.client.table("rag_queries").insert(query_data).execute()
            return result.data[0] if result.data else None
        except APIError as e:
            logger.warning(f"Failed to log RAG query (non-critical): {e}")
            return None

# Global instance
supabase_client = SupabaseClient()
