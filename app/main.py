from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(
    title="AutoDesk Agent",
    description="An agentic IT helpdesk assistant powered by Grok",
    version="1.0.0"
)

# Mount static files for the frontend
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
async def startup_event():
    """Auto-ingest documents into the knowledge base on server start."""
    from app.services.rag import ingest_documents
    logger = logging.getLogger("startup")
    logger.info("AutoDesk Agent starting up...")
    result = ingest_documents()
    logger.info(f"Knowledge base status: {result}")


@app.get("/")
async def root():
    """Serve the frontend chat UI."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "AutoDesk Agent API is running. Frontend not found."}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "AutoDesk Agent"}


# API routes
from app.routers import chat
app.include_router(chat.router)

