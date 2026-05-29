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
You can create, edit, rename, move, or delete columns and cards on the board by modifying the board data.

You must ALWAYS respond with a JSON object (and ONLY a JSON object) matching the following structure:
{{
  "chatResponse": "Your text message back to the user explaining what you did.",
  "boardUpdate": null or the complete updated BoardData object if you made changes (e.g. created, edited, moved, or deleted cards/columns).
}}

Ensure that "boardUpdate" maintains the exact structural integrity of the Kanban board, including:
- "columns": list of {{ "id": string, "title": string, "cardIds": list of strings }}
- "cards": dictionary of card ID to {{ "id": string, "title": string, "details": string }}

If the user wants you to create a card, generate a unique random ID (e.g. "card-xxxxxx" using random alphanumeric characters) and insert it both into the "cards" dictionary and the corresponding column's "cardIds" list.
If the user wants you to move a card, find it in the "cardIds" of its current column and move it to the "cardIds" of the target column.
If you do not need to make any changes to the board, set "boardUpdate" to null.

Current Board Data:
{board_json}

DO NOT include any markdown formatting outside the JSON, other than optionally wrapping your JSON response in a single ```json ... ``` block. Do not write any conversational text before or after the JSON.
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
        
        # Simple structural validation
        if "chatResponse" not in parsed:
            parsed["chatResponse"] = "I have updated the board."
        if "boardUpdate" not in parsed:
            parsed["boardUpdate"] = None
            
        return parsed
    except Exception as e:
        return {
            "chatResponse": f"Sorry, I encountered an error processing your request: {str(e)}",
            "boardUpdate": None
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
