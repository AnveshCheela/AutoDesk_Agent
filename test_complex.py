"""Test complex multi-tool scenarios."""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_query(message, session_id="test-complex"):
    print(f"\n{'='*60}")
    print(f"USER: {message}")
    print('='*60)

    r = requests.post(f"{BASE_URL}/api/chat", json={
        "message": message,
        "session_id": session_id,
    })

    if r.status_code != 200:
        print(f"ERROR: HTTP {r.status_code} - {r.text}")
        return

    data = r.json()
    print(f"\nAGENT RESPONSE:\n{data['response']}")
    print(f"\nTRACE ({len(data.get('trace', []))} steps):")
    for t in data.get("trace", []):
        content = t["content"][:200]
        print(f"  [{t['type']:12s}] {content}")
    print()


# Test 1: Combined RAG and ticket creation
test_query("What are the password requirements? Also, please create a high priority ticket because I am locked out of my account.")

# Test 2: RAG ambiguity resolution
test_query("I need a new laptop, but I don't know what models are available. Could you check and let me know?")

print("\n Complex tests completed!")
