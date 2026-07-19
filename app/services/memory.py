"""
Conversation Memory Service using Redis.

Stores and retrieves chat history for each session to enable multi-turn conversations.
"""

import json
import logging
from typing import List, Dict

import redis
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Redis client
try:
    redis_client = redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,  # Automatically decode bytes to strings
    )
    # Test connection
    redis_client.ping()
    logger.info("Connected to Redis successfully.")
except Exception as e:
    logger.warning(f"Failed to connect to Redis: {e}. Falling back to in-memory store.")
    redis_client = None

import os

# Fallback persistent JSON store if Redis is unavailable
FALLBACK_FILE = "data/history.json"
_memory_store = {}

def _load_fallback():
    global _memory_store
    if os.path.exists(FALLBACK_FILE):
        try:
            with open(FALLBACK_FILE, "r") as f:
                _memory_store = json.load(f)
        except Exception:
            _memory_store = {}

def _save_fallback():
    os.makedirs("data", exist_ok=True)
    with open(FALLBACK_FILE, "w") as f:
        json.dump(_memory_store, f)

# Load it initially
if not redis_client:
    _load_fallback()


def _get_session_key(session_id: str) -> str:
    """Prefix session IDs to avoid key collisions in Redis."""
    return f"autodesk:session:{session_id}"


def get_conversation_history(session_id: str, limit: int = 10) -> List[Dict]:
    """
    Retrieve the recent conversation history for a session.
    """
    if redis_client:
        try:
            key = _get_session_key(session_id)
            raw_messages = redis_client.lrange(key, 0, -1)
            history = [json.loads(msg) for msg in raw_messages]
            return history[-limit:] if limit > 0 else history
        except Exception as e:
            logger.error(f"Error reading from Redis: {e}")
            return []
    else:
        # Use fallback
        return _memory_store.get(session_id, [])[-limit:]


def append_to_history(session_id: str, messages: List[Dict], max_history: int = 20):
    """
    Append new messages to the session's conversation history.
    """
    if not messages:
        return

    if redis_client:
        try:
            key = _get_session_key(session_id)
            json_messages = [json.dumps(msg) for msg in messages]
            redis_client.rpush(key, *json_messages)
            redis_client.ltrim(key, -max_history, -1)
            redis_client.expire(key, 86400)
            
        except Exception as e:
            logger.error(f"Error writing to Redis: {e}")
    else:
        # Use fallback
        if session_id not in _memory_store:
            _memory_store[session_id] = []
        _memory_store[session_id].extend(messages)
        _memory_store[session_id] = _memory_store[session_id][-max_history:]
        _save_fallback()


def clear_history(session_id: str):
    """Clear the conversation history for a session."""
    if redis_client:
        try:
            redis_client.delete(_get_session_key(session_id))
        except Exception as e:
            logger.error(f"Error deleting from Redis: {e}")
    else:
        if session_id in _memory_store:
            del _memory_store[session_id]
            _save_fallback()
