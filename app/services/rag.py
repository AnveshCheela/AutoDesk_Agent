"""
RAG (Retrieval-Augmented Generation) pipeline.

Handles:
  1. Loading markdown documents from disk
  2. Chunking them by section (header-based splitting)
  3. Generating embeddings and storing in ChromaDB
  4. Similarity search for user queries
"""

import os
import re
import logging
from typing import List, Dict, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.services.embeddings import generate_embeddings, generate_single_embedding

logger = logging.getLogger(__name__)

# ============================================
# ChromaDB Client (Singleton)
# ============================================
_chroma_client: Optional[chromadb.ClientAPI] = None
_collection: Optional[chromadb.Collection] = None

COLLECTION_NAME = "autodesk_knowledge_base"


def get_chroma_client() -> chromadb.ClientAPI:
    """Get or create the persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        persist_dir = os.path.abspath(settings.CHROMA_PERSIST_DIR)
        os.makedirs(persist_dir, exist_ok=True)
        logger.info(f"Initializing ChromaDB at: {persist_dir}")
        _chroma_client = chromadb.PersistentClient(path=persist_dir)
    return _chroma_client


def get_collection() -> chromadb.Collection:
    """Get or create the knowledge base collection."""
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},  # cosine similarity
        )
        logger.info(f"ChromaDB collection '{COLLECTION_NAME}' ready. "
                     f"Current document count: {_collection.count()}")
    return _collection


# ============================================
# Document Loading
# ============================================
def load_documents(docs_dir: str = None) -> List[Dict[str, str]]:
    """
    Load all markdown files from the docs directory.

    Returns:
        List of dicts with 'filename', 'path', and 'content' keys.
    """
    if docs_dir is None:
        # Default: project_root/docs/
        project_root = Path(__file__).parent.parent.parent
        docs_dir = str(project_root / "docs")

    docs = []
    docs_path = Path(docs_dir)

    if not docs_path.exists():
        logger.warning(f"Docs directory not found: {docs_dir}")
        return docs

    for md_file in sorted(docs_path.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        docs.append({
            "filename": md_file.name,
            "path": str(md_file),
            "content": content,
        })
        logger.info(f"Loaded document: {md_file.name} ({len(content)} chars)")

    logger.info(f"Total documents loaded: {len(docs)}")
    return docs


# ============================================
# Chunking
# ============================================
def chunk_document(doc: Dict[str, str], max_chunk_size: int = 500) -> List[Dict]:
    """
    Split a document into chunks by markdown sections (## headers).

    Each chunk contains the section header + its body text.
    If a section is too long, it's split further by paragraphs.

    Args:
        doc: Dict with 'filename', 'path', 'content'.
        max_chunk_size: Maximum characters per chunk before paragraph splitting.

    Returns:
        List of chunk dicts with 'text', 'metadata' keys.
    """
    content = doc["content"]
    filename = doc["filename"]

    # Extract the document title (first # heading)
    title_match = re.match(r"^#\s+(.+)", content, re.MULTILINE)
    doc_title = title_match.group(1).strip() if title_match else filename

    # Split by ## headings (keep the heading with its content)
    sections = re.split(r"(?=^##\s)", content, flags=re.MULTILINE)

    chunks = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Extract section heading
        heading_match = re.match(r"^##\s+(.+)", section)
        section_heading = heading_match.group(1).strip() if heading_match else doc_title

        # Clean the section text
        section_text = section.strip()

        # Skip very short sections (like just the document header metadata)
        if len(section_text) < 30:
            continue

        if len(section_text) <= max_chunk_size:
            # Section fits in one chunk
            chunks.append({
                "text": section_text,
                "metadata": {
                    "source": filename,
                    "document_title": doc_title,
                    "section": section_heading,
                },
            })
        else:
            # Split by paragraphs (double newline)
            paragraphs = re.split(r"\n\n+", section_text)
            current_chunk = ""

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                if len(current_chunk) + len(para) + 2 <= max_chunk_size:
                    current_chunk += ("\n\n" + para) if current_chunk else para
                else:
                    if current_chunk:
                        chunks.append({
                            "text": current_chunk,
                            "metadata": {
                                "source": filename,
                                "document_title": doc_title,
                                "section": section_heading,
                            },
                        })
                    current_chunk = para

            # Don't forget the last accumulated chunk
            if current_chunk:
                chunks.append({
                    "text": current_chunk,
                    "metadata": {
                        "source": filename,
                        "document_title": doc_title,
                        "section": section_heading,
                    },
                })

    logger.info(f"Chunked '{filename}' into {len(chunks)} chunks")
    return chunks


def chunk_all_documents(docs: List[Dict[str, str]]) -> List[Dict]:
    """Chunk all loaded documents."""
    all_chunks = []
    for doc in docs:
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)
    logger.info(f"Total chunks across all documents: {len(all_chunks)}")
    return all_chunks


# ============================================
# Ingestion (Embed + Store)
# ============================================
def ingest_documents(docs_dir: str = None, force: bool = False) -> Dict:
    """
    Full ingestion pipeline: load → chunk → embed → store in ChromaDB.

    Args:
        docs_dir: Path to the docs directory. Defaults to project_root/docs/.
        force: If True, clear existing collection and re-ingest.

    Returns:
        Dict with ingestion stats.
    """
    collection = get_collection()

    # Check if already ingested (skip if not forced)
    existing_count = collection.count()
    if existing_count > 0 and not force:
        logger.info(f"Collection already has {existing_count} chunks. "
                     "Skipping ingestion. Use force=True to re-ingest.")
        return {
            "status": "skipped",
            "message": "Documents already ingested",
            "existing_chunks": existing_count,
        }

    # Clear if re-ingesting
    if force and existing_count > 0:
        logger.info("Force re-ingestion: clearing existing collection...")
        client = get_chroma_client()
        client.delete_collection(COLLECTION_NAME)
        # Reset the singleton so it gets re-created
        global _collection
        _collection = None
        collection = get_collection()

    # 1. Load documents
    docs = load_documents(docs_dir)
    if not docs:
        return {"status": "error", "message": "No documents found"}

    # 2. Chunk
    chunks = chunk_all_documents(docs)
    if not chunks:
        return {"status": "error", "message": "No chunks generated"}

    # 3. Generate embeddings
    logger.info(f"Generating embeddings for {len(chunks)} chunks...")
    texts = [chunk["text"] for chunk in chunks]
    embeddings = generate_embeddings(texts)

    # 4. Store in ChromaDB
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas = [chunk["metadata"] for chunk in chunks]

    # ChromaDB has a batch limit, so we add in batches
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch_end = min(i + batch_size, len(chunks))
        collection.add(
            ids=ids[i:batch_end],
            embeddings=embeddings[i:batch_end],
            documents=texts[i:batch_end],
            metadatas=metadatas[i:batch_end],
        )

    logger.info(f"Ingestion complete. Stored {len(chunks)} chunks in ChromaDB.")

    return {
        "status": "success",
        "documents_loaded": len(docs),
        "chunks_created": len(chunks),
        "chunks_stored": collection.count(),
    }


# ============================================
# Similarity Search
# ============================================
def search_knowledge_base(query: str, top_k: int = None) -> List[Dict]:
    """
    Search the knowledge base for chunks relevant to the query.

    Args:
        query: The user's search query.
        top_k: Number of top results to return.

    Returns:
        List of result dicts with 'text', 'metadata', 'distance' keys.
    """
    if top_k is None:
        top_k = settings.TOP_K_RESULTS

    collection = get_collection()

    if collection.count() == 0:
        logger.warning("Knowledge base is empty. Run ingestion first.")
        return []

    # Generate query embedding
    query_embedding = generate_single_embedding(query)

    # Search ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    # Format results
    search_results = []
    if results and results["documents"] and results["documents"][0]:
        for i in range(len(results["documents"][0])):
            search_results.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
                "relevance_score": round(1 - results["distances"][0][i], 4),
            })

    logger.info(f"Search for '{query[:50]}...' returned {len(search_results)} results")
    return search_results
