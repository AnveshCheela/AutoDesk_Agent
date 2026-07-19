"""Test the full agent pipeline via the API."""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_query(message, session_id="test-session"):
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


# Test 1: RAG query (should search knowledge base)
test_query("How do I reset my password?")

# Test 2: Ticket creation (should call create_ticket tool)
test_query("My monitor is flickering and giving me headaches. Please create a high priority ticket.")

# Test 3: Ticket status check (should call check_ticket_status)
test_query("What is the status of ticket #1?")

print("\n All tests completed!")
