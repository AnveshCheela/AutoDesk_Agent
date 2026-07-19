"""
Embedding service using sentence-transformers.
Uses the all-MiniLM-L6-v2 model for fast, high-quality 384-dim embeddings.
"""

import logging
from typing import List
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Module-level singleton — loaded once, reused everywhere
_model: SentenceTransformer | None = None
MODEL_NAME = "all-MiniLM-L6-v2"


def get_model() -> SentenceTransformer:
    """Lazy-load and return the singleton embedding model."""
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Embedding model loaded successfully.")
    return _model


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of text strings.

    Args:
        texts: List of strings to embed.

    Returns:
        List of embedding vectors (each a list of floats).
    """
    if not texts:
        return []

    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return embeddings.tolist()


def generate_single_embedding(text: str) -> List[float]:
    """
    Generate an embedding for a single text string.

    Args:
        text: The string to embed.

    Returns:
        Embedding vector as a list of floats.
    """
    model = get_model()
    embedding = model.encode(text, show_progress_bar=False, convert_to_numpy=True)
    return embedding.tolist()
