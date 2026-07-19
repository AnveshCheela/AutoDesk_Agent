# AutoDesk Agent 🤖💼

An AI-powered IT Helpdesk assistant designed to autonomously manage IT support operations. It acts as an intelligent first line of defense—capable of answering complex policy questions by searching an internal knowledge base, parsing IT issues, and autonomously creating, reading, and updating IT support tickets.

## Features ✨
* **Agentic ReAct Loop**: Built from scratch using a custom Reason + Act (ReAct) orchestration loop. The agent reasons about its tasks and dynamically determines which tools to call.
* **Semantic Search (RAG)**: Integrates **ChromaDB** and `sentence-transformers` for Retrieval-Augmented Generation, allowing the agent to answer questions based on company policies.
* **Ticketing System Integration**: Uses a mock **SQLite** database where the agent can autonomously query, create, and escalate IT tickets.
* **Persistent Memory**: Uses **Redis** to maintain conversation history across sessions, ensuring the agent remembers context.
* **Resilient Tool Execution**: Implements a robust fallback parser to seamlessly catch and fix LLM hallucinations (like returning XML tags instead of JSON for tool calls).
* **Modern UI & Agent Trace**: Features a beautiful glassmorphism UI with a side-by-side **Agent Trace** panel, allowing users to watch the agent's internal thought process and tool execution in real-time.

## Tech Stack 🛠️
* **Backend**: FastAPI (Python)
* **LLM**: Groq API (`llama-3.3-70b-versatile`)
* **Vector DB**: ChromaDB
* **Relational DB**: SQLite
* **Memory/Cache**: Redis
* **Frontend**: HTML / CSS / Vanilla JavaScript

## Getting Started 🚀

### 1. Prerequisites
Ensure you have the following installed:
* Python 3.9+
* Redis (Running on `localhost:6379`)

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/AnveshCheela/AutoDesk_Agent.git
cd AutoDesk_Agent
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory and add your API keys:
```ini
# .env
GROK_API_KEY=your_groq_api_key_here
```

### 4. Populate Mock Databases
Run the setup script to generate the SQLite database (`helpdesk.db`) and build the ChromaDB vector embeddings (`chroma_db/`) from the sample IT policies.
```bash
python populate_db.py
```

### 5. Start the Server
Run the FastAPI backend server:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open your browser and navigate to `http://127.0.0.1:8000` to interact with the agent!

## Architecture Overview 🏗️
The backend leverages an orchestration engine located in `app/services/agent.py`. When a user submits a query:
1. The engine retrieves the user's conversation history from Redis.
2. It loops through a ReAct cycle, asking the LLM what it wants to do.
3. If the LLM returns a tool call, the backend executes the corresponding python function (e.g., querying SQLite or ChromaDB) and feeds the result back into the prompt.
4. Once the LLM determines it has enough information, it generates a final response.
5. The trace of thoughts and actions is sent back to the frontend to populate the Agent Trace panel.

## License
MIT License
