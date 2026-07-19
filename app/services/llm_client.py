"""Groq LLM client using the OpenAI-compatible API."""

from openai import OpenAI
from app.config import settings


def get_llm_client() -> OpenAI:
    """Create and return an OpenAI client configured for Groq."""
    return OpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url=settings.GROQ_BASE_URL,
    )


def test_connection() -> str:
    """Test the Groq API connection with a simple prompt."""
    client = get_llm_client()
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are AutoDesk, an IT helpdesk assistant. Respond briefly."},
            {"role": "user", "content": "Hello, are you online?"}
        ],
        max_tokens=100
    )
    return response.choices[0].message.content
