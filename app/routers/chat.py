"""
Chat and knowledge base API routes.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

router = APIRouter(prefix="/api", tags=["chat"])


# ============================================
# Request / Response Models
# ============================================
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    trace: list = []


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: Optional[int] = Field(default=3, ge=1, le=10)


class SearchResult(BaseModel):
    text: str
    metadata: Dict
    relevance_score: float


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    count: int


class IngestResponse(BaseModel):
    status: str
    message: str = ""
    documents_loaded: int = 0
    chunks_created: int = 0
    chunks_stored: int = 0
    existing_chunks: int = 0


# ============================================
# Chat Endpoint
# ============================================
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint for the AutoDesk Agent."""
    from app.services.agent import run_agent
    from app.services.memory import get_conversation_history, append_to_history

    session_id = request.session_id or "demo-session"

    try:
        # Load conversation history (last 10 messages)
        history = get_conversation_history(session_id, limit=10)

        # Run the agentic reasoning loop
        result = run_agent(
            user_message=request.message,
            conversation_history=history,
        )

        final_response = result["response"]

        # Save the new interaction to memory
        append_to_history(session_id, [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": final_response}
        ])

        return ChatResponse(
            response=final_response,
            session_id=session_id,
            trace=result.get("trace", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 50):
    """Get the conversation history for a specific session."""
    from app.services.memory import get_conversation_history
    try:
        history = get_conversation_history(session_id, limit=limit)
        return {"session_id": session_id, "messages": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")


@router.delete("/chat/history/{session_id}")
async def delete_chat_history(session_id: str):
    """Delete the conversation history for a specific session."""
    from app.services.memory import clear_history
    try:
        clear_history(session_id)
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete history: {str(e)}")


# ============================================
# Knowledge Base Endpoints
# ============================================
@router.post("/kb/ingest", response_model=IngestResponse)
async def ingest_knowledge_base(force: bool = False):
    """
    Ingest documents into the knowledge base.
    Set force=True to clear and re-ingest all documents.
    """
    from app.services.rag import ingest_documents

    try:
        result = ingest_documents(force=force)
        return IngestResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/kb/search", response_model=SearchResponse)
async def search_knowledge_base(request: SearchRequest):
    """
    Search the knowledge base for relevant document chunks.
    """
    from app.services.rag import search_knowledge_base as search_kb

    try:
        results = search_kb(query=request.query, top_k=request.top_k)
        return SearchResponse(
            query=request.query,
            results=[SearchResult(**r) for r in results],
            count=len(results),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/kb/stats")
async def knowledge_base_stats():
    """Get statistics about the knowledge base."""
    from app.services.rag import get_collection

    try:
        collection = get_collection()
        return {
            "collection_name": collection.name,
            "document_count": collection.count(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
