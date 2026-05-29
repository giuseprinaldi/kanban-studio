import os
import json
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load .env
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = "openai/gpt-oss-120b:free"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

SYSTEM_PROMPT = """You are a helpful AI assistant integrated into a Kanban Project Management board (Kanban Studio).
You help the user by issuing a short list of ACTIONS that modify the board. You must NOT return the whole board — only the actions needed. This keeps responses fast.

Respond with ONLY a JSON object of exactly this shape:
{{
  "chatResponse": "A short message to the user describing what you did, or answering their question.",
  "actions": [ ...zero or more action objects... ]
}}

Supported action objects (reference columns and cards by their exact title or id as shown in the board below):
- {{"type": "add_card", "column": "<column title or id>", "title": "<card title>", "details": "<card details>"}}
- {{"type": "edit_card", "card": "<card title or id>", "title": "<new title, optional>", "details": "<new details, optional>"}}
- {{"type": "delete_card", "card": "<card title or id>"}}
- {{"type": "move_card", "card": "<card title or id>", "toColumn": "<column title or id>", "position": <optional 0-based index>}}
- {{"type": "rename_column", "column": "<column title or id>", "title": "<new title>"}}
- {{"type": "add_column", "title": "<column title>"}}
- {{"type": "delete_column", "column": "<column title or id>"}}

Rules:
- If the user only asks a question, or no change is needed, return "actions": [].
- Do NOT invent card or column ids. Refer to existing items by the title or id shown below.
- Keep "chatResponse" concise.

Current board:
{board_json}

Return only the JSON object, optionally wrapped in a single ```json ... ``` block. No other text.
"""

def clean_json_response(raw_response: str) -> str:
    # Remove markdown code blocks if present
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_response, re.DOTALL)
    if match:
        return match.group(1)
    
    # Try finding the first '{' and last '}'
    start_idx = raw_response.find("{")
    end_idx = raw_response.rfind("}")
    if start_idx != -1 and end_idx != -1:
        return raw_response[start_idx:end_idx + 1]
        
    return raw_response

def run_chat_query(messages: List[Dict[str, str]], current_board: Dict[str, Any]) -> Dict[str, Any]:
    if not OPENROUTER_API_KEY:
        return {
            "chatResponse": "Error: OPENROUTER_API_KEY is not configured.",
            "boardUpdate": None
        }
        
    # Build system prompt with current board state
    formatted_system = SYSTEM_PROMPT.format(board_json=json.dumps(current_board, indent=2))
    
    # Construct LLM request messages
    llm_messages = [{"role": "system", "content": formatted_system}]
    
    # Add conversation history
    # Keep only user and assistant messages
    for msg in messages:
        llm_messages.append({"role": msg["role"], "content": msg["content"]})
        
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=llm_messages,
            temperature=0.2,
            timeout=45.0,
            response_format={"type": "json_object"},
        )

        raw_text = completion.choices[0].message.content
        cleaned = clean_json_response(raw_text)
        parsed = json.loads(cleaned)

        # Normalise the response shape
        if not isinstance(parsed.get("chatResponse"), str):
            parsed["chatResponse"] = "Done."
        if not isinstance(parsed.get("actions"), list):
            parsed["actions"] = []

        return parsed
    except Exception as e:
        return {
            "chatResponse": f"Sorry, I encountered an error processing your request: {str(e)}",
            "actions": []
        }


def run_test_query() -> str:
    """Simple connectivity check used by /api/ai/test (PLAN Part 8)."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured.")

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": "What is 2+2? Reply with only the number."}],
        temperature=0,
        timeout=45.0,
    )
    return completion.choices[0].message.content
