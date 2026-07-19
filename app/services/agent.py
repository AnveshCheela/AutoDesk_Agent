"""
Agent Orchestration Engine — the core agentic reasoning loop.

This module implements the ReAct (Reasoning + Acting) pattern:
  1. Receive user query + conversation history
  2. Send to Grok with tool definitions
  3. If Grok calls a tool → execute it → feed result back
  4. Repeat until Grok gives a final text answer (or max steps reached)
  5. Log every step as a trace for observability

Tools available:
  - search_knowledge_base(query): Search IT policy docs via RAG
  - check_ticket_status(ticket_id): Look up a ticket by ID
  - create_ticket(issue, priority): Create a new support ticket
"""

import json
import logging
from typing import List, Dict, Optional

from openai import OpenAI
from openai.types.chat import ChatCompletionMessage

from app.config import settings
from app.services.llm_client import get_llm_client
from app.services.rag import search_knowledge_base
from app.services.ticket_db import create_ticket, check_ticket_status

logger = logging.getLogger(__name__)

# ============================================
# System Prompt
# ============================================
SYSTEM_PROMPT = """You are AutoDesk, a helpful and efficient IT helpdesk assistant.
You have access to a knowledge base and a ticketing system.

IMPORTANT INSTRUCTION FOR TOOL CALLING:
You are communicating with an API that requires strict JSON tool calling.
NEVER use `<function=...>` XML tags to call tools. You must use the native OpenAI tool-calling JSON schema.
If you need to call a tool, only output the JSON matching the tool's signature.

Your capabilities:
1. **Answer IT policy questions** by searching the knowledge base (company documentation about passwords, VPN, hardware, software, email, security incidents).
2. **Check ticket status** when users ask about existing support tickets.
3. **Create new support tickets** when users report issues or request help.

Guidelines:
- Always search the knowledge base before answering policy questions. Do NOT make up information.
- When creating tickets, confirm what you created (ticket ID, issue, priority).
- When checking ticket status, report all relevant details (status, priority, creation date, assignee).
- Be professional, concise, and helpful. Use bullet points for clarity when appropriate.
- If a user's request is ambiguous, ask for clarification instead of guessing.
- You may need to use multiple tools in sequence to fully answer a question (e.g., search the KB for policy, then create a ticket based on the result).
"""

# ============================================
# Tool Definitions (OpenAI Function Calling format)
# ============================================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search TechCorp's IT knowledge base for information about company policies, procedures, and troubleshooting guides. Use this tool when the user asks about IT policies, how-to questions, or needs guidance on company procedures like password resets, VPN setup, hardware requests, software installation, email policies, or security incident reporting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant IT documentation. Be specific and descriptive for better results.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_ticket_status",
            "description": "Check the status and details of an existing IT support ticket by its ticket ID number. Use this when the user asks about the status of a specific ticket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "integer",
                        "description": "The numeric ticket ID to look up (e.g., 1, 42, 100).",
                    }
                },
                "required": ["ticket_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Create a new IT support ticket for the user. Use this when the user reports an issue, requests help, or needs to submit a support request. Extract the issue description and priority from the user's message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue": {
                        "type": "string",
                        "description": "A clear description of the issue or request.",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Priority level. Use 'critical' for system-wide outages, 'high' for work-blocking issues, 'medium' for general requests, 'low' for minor inconveniences.",
                    },
                },
                "required": ["issue", "priority"],
            },
        },
    },
]

# ============================================
# Tool Executor
# ============================================
def execute_tool(tool_name: str, arguments: Dict) -> str:
    """
    Execute a tool by name with the given arguments.

    Returns:
        A JSON string with the tool result.
    """
    try:
        if tool_name == "search_knowledge_base":
            results = search_knowledge_base(query=arguments["query"], top_k=3)
            if not results:
                return json.dumps({"result": "No relevant documents found in the knowledge base."})

            # Format results for the LLM
            formatted = []
            for r in results:
                formatted.append({
                    "source": r["metadata"]["source"],
                    "section": r["metadata"].get("section", ""),
                    "content": r["text"],
                    "relevance": r["relevance_score"],
                })
            return json.dumps({"results": formatted})

        elif tool_name == "check_ticket_status":
            ticket = check_ticket_status(ticket_id=arguments["ticket_id"])
            if ticket is None:
                return json.dumps({"error": f"Ticket #{arguments['ticket_id']} not found."})
            return json.dumps({"ticket": ticket})

        elif tool_name == "create_ticket":
            ticket = create_ticket(
                issue=arguments["issue"],
                priority=arguments.get("priority", "medium"),
            )
            return json.dumps({"ticket_created": ticket})

        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}")
        return json.dumps({"error": f"Tool '{tool_name}' failed: {str(e)}"})


# ============================================
# Agent Reasoning Loop
# ============================================
def run_agent(
    user_message: str,
    conversation_history: Optional[List[Dict]] = None,
) -> Dict:
    """
    Run the agentic reasoning loop.

    Args:
        user_message: The current user message.
        conversation_history: Previous messages in the conversation (for multi-turn).

    Returns:
        Dict with:
          - 'response': The agent's final text response.
          - 'trace': List of reasoning steps for observability.
    """
    client = get_llm_client()
    trace = []
    max_steps = settings.MAX_AGENT_STEPS

    # Build message list
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history (if any)
    if conversation_history:
        messages.extend(conversation_history)

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    logger.info(f"Agent invoked. User: '{user_message[:80]}...'")

    # --- Reasoning Loop ---
    for step in range(max_steps):
        logger.info(f"--- Agent Step {step + 1}/{max_steps} ---")

        trace.append({
            "type": "thought",
            "content": f"Step {step + 1}: Sending to Grok for reasoning...",
        })

        try:
            import openai
            
            # Call the LLM with tool definitions
            try:
                response = client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=1024,
                )
                assistant_message = response.choices[0].message
                content = assistant_message.content
            except openai.BadRequestError as e:
                err_dict = getattr(e, 'body', {}) or {}
                if isinstance(err_dict, dict):
                    err_info = err_dict.get('error', {})
                    failed_gen = err_info.get('failed_generation', '')
                else:
                    err_info = {}
                    failed_gen = ''
                    
                if "tool_use_failed" in str(e) and failed_gen and "<function=" in failed_gen:
                    logger.warning("Caught Groq 400 Error. Rescuing tool call from failed_generation.")
                    
                    # Convert the XML `<function=tool_name({"arg": "val"})></function>` into JSON
                    import re
                    xml_pattern = r'<function=([^>]+)\((.*?)\)></function>'
                    xml_matches = re.findall(xml_pattern, failed_gen)
                    
                    if xml_matches:
                        # Clean up failed_gen to be the text before the XML
                        clean_text = re.sub(xml_pattern, '', failed_gen).strip()
                        
                        # Create a mock assistant message with native tool calls to feed into our execution logic
                        class MockFunction:
                            def __init__(self, name, arguments):
                                self.name = name
                                self.arguments = arguments
                                
                        class MockToolCall:
                            def __init__(self, id, name, arguments):
                                self.id = id
                                self.type = "function"
                                self.function = MockFunction(name, arguments)
                                
                        class MockMessage:
                            def __init__(self, content, tool_calls):
                                self.role = "assistant"
                                self.content = content
                                self.tool_calls = tool_calls
                                
                            def to_dict(self):
                                return {
                                    "role": self.role,
                                    "content": self.content,
                                    "tool_calls": [
                                        {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                                        for tc in self.tool_calls
                                    ]
                                }
                                
                        mock_tool_calls = []
                        for i, (func_name, func_args_json) in enumerate(xml_matches):
                            mock_tool_calls.append(MockToolCall(f"call_xml_{i}", func_name, func_args_json))
                            
                        assistant_message = MockMessage(clean_text if clean_text else None, mock_tool_calls)
                        content = assistant_message.content
                    else:
                        raise e # Could not rescue
                else:
                    raise e # Not a rescuable error

            # Case 1: Native LLM tool calls
            tool_calls_to_execute = []
            
            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    tool_calls_to_execute.append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "args": json.loads(tool_call.function.arguments)
                    })
                messages.append(assistant_message.to_dict())
            
            # Case 1b: Hallucinated JSON tool calls in content body (Llama 3 quirk)
            elif content and "{" in content and "}" in content:
                import re
                # Match {"type": "function", "name": "...", "parameters": {...}}
                # Allowing for whitespace and nested braces in parameters
                pattern = r'\{\s*"type"\s*:\s*"function"\s*,\s*"name"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{[^\}]*\}\s*\}'
                matches = re.findall(pattern, content)
                
                clean_content = content
                for match_str in matches:
                    try:
                        parsed = json.loads(match_str)
                        if "name" in parsed and "parameters" in parsed:
                            logger.info(f"Caught hallucinated JSON tool call: {parsed['name']}")
                            tool_calls_to_execute.append({
                                "id": f"call_hallucinated_{len(tool_calls_to_execute)}",
                                "name": parsed["name"],
                                "args": parsed["parameters"]
                            })
                            clean_content = clean_content.replace(match_str, "")
                    except json.JSONDecodeError:
                        continue
                
                if tool_calls_to_execute:
                    clean_content = clean_content.strip()
                    fake_msg = {
                        "role": "assistant",
                        "content": clean_content if clean_content else None,
                        "tool_calls": []
                    }
                    for call in tool_calls_to_execute:
                        fake_msg["tool_calls"].append({
                            "id": call["id"],
                            "type": "function",
                            "function": {
                                "name": call["name"],
                                "arguments": json.dumps(call["args"])
                            }
                        })
                    messages.append(fake_msg)

            if tool_calls_to_execute:
                for call in tool_calls_to_execute:
                    tool_name = call["name"]
                    tool_args = call["args"]
                    tool_id = call["id"]

                    logger.info(f"Tool call: {tool_name}({tool_args})")
                    trace.append({
                        "type": "action",
                        "content": f"Calling tool: {tool_name}({json.dumps(tool_args)})",
                    })

                    # Execute the tool
                    tool_result = execute_tool(tool_name, tool_args)

                    logger.info(f"Tool result: {tool_result[:200]}...")
                    trace.append({
                        "type": "observation",
                        "content": f"Result from {tool_name}: {tool_result[:500]}",
                    })

                    # Feed the tool result back to the LLM
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": tool_result,
                    })

                # Continue the loop — LLM may want to call more tools or give a final answer

            # Case 2: LLM gives a final text answer (no tool calls)
            else:
                final_response = assistant_message.content or "I'm sorry, I couldn't generate a response."
                logger.info(f"Agent final response: {final_response[:100]}...")
                trace.append({
                    "type": "thought",
                    "content": f"Final answer generated.",
                })

                return {
                    "response": final_response,
                    "trace": trace,
                }

        except Exception as e:
            error_msg = f"Error during agent step {step + 1}: {str(e)}"
            logger.error(error_msg)
            trace.append({
                "type": "error",
                "content": error_msg,
            })

            return {
                "response": f"I encountered an error while processing your request: {str(e)}. Please try again.",
                "trace": trace,
            }

    # Max steps reached — return whatever we have
    logger.warning(f"Agent reached max steps ({max_steps}) without a final answer.")
    trace.append({
        "type": "error",
        "content": f"Reached maximum reasoning steps ({max_steps}). Returning best available response.",
    })

    return {
        "response": "I've been working on your request but reached my processing limit. Could you please rephrase or simplify your question?",
        "trace": trace,
    }
