"""Test script to verify RAG search quality."""
from app.services.rag import search_knowledge_base

queries = [
    "How do I reset my password?",
    "What laptops can I request?",
    "VPN not working, how to fix?",
    "How to report a phishing email?",
]

for q in queries:
    print(f"\n{'='*60}")
    print(f"QUERY: {q}")
    print('='*60)
    results = search_knowledge_base(q, top_k=3)
    for i, r in enumerate(results, 1):
        score = r["relevance_score"]
        source = r["metadata"]["source"]
        section = r["metadata"].get("section", "N/A")
        snippet = r["text"][:150].replace("\n", " ")
        print(f"  [{i}] Score: {score:.4f} | Source: {source} | Section: {section}")
        print(f"      {snippet}...")
    print()
