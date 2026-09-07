"""
Insight Agent (Day 6 — brief section 4.5).

Standard OpenAI-style tool-calling loop (Groq's API is OpenAI-compatible,
not Anthropic's Messages API): send the conversation + tool definitions
to the model; if it responds with tool_calls, execute them locally
against the database and feed results back as role="tool" messages;
repeat until the model responds with plain content. The system prompt is
the enforcement mechanism for "answer only from live backend data — no
invented numbers": it explicitly forbids answering numeric/factual fleet
questions without a tool call, and this is what a live test (ask
something with no data) is meant to verify.
"""
import json

from groq import Groq, APIStatusError

from app.core.config import settings
from app.agent.tools import TOOL_DEFINITIONS, execute_tool

SYSTEM_PROMPT = """You are the FleetGuard AI Insight Agent, a fleet maintenance assistant.

You have tools that query LIVE backend data: parts, correlation statistics, \
failure-probability predictions, RUL (remaining useful life) estimates, and \
vehicle lookup.

HARD RULE: You must never state a specific number (a probability, a \
correlation, a risk tier, a km/day figure, a count) unless it came from a \
tool result in this conversation. If you don't have the data, call a tool \
to get it. If a tool returns an error or no data, say so plainly — do not \
estimate, guess, or fill in a plausible-sounding number.

When the user gives a loose vehicle reference (a partial VIN, "truck 4521", \
etc.) instead of an exact VIN, use find_vehicle first to resolve it before \
calling any other vehicle-specific tool. If find_vehicle returns multiple \
matches, ask the user which one they mean rather than guessing.

When you report a number, briefly note where it came from (e.g. "based on \
this week's scoring run" or "from the correlation analysis for this part") \
so the user can tell it's grounded, not invented.

Keep answers concise and conversational — this is a chat panel, not a report. \
Use plain language over jargon where possible, but keep exact figures precise."""


def run_agent_turn(user_message: str, conversation_history: list[dict] | None = None) -> dict:
    """
    conversation_history: list of OpenAI-format messages ({"role": ..., "content": ...,
    "tool_calls": [...]?}) from prior turns. Pass [] or None for a fresh conversation.

    Returns {"reply": str, "tool_calls": [{"tool": str, "input": dict, "result": dict}], "messages": [...]}
    — "messages" is the FULL updated history (including the system prompt) to pass
    back in as conversation_history on the next turn.
    """
    if not settings.groq_api_key:
        return {
            "reply": "The Insight Agent isn't configured yet — GROQ_API_KEY is "
                     "missing from .env. Add your API key and restart the server.",
            "tool_calls": [],
            "messages": conversation_history or [],
        }

    client = Groq(api_key=settings.groq_api_key)

    messages = list(conversation_history or [])
    if not messages or messages[0].get("role") != "system":
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    messages.append({"role": "user", "content": user_message})

    tool_calls_log = []
    max_iterations = 6  # safety cap on tool-call loops within one turn

    for _ in range(max_iterations):
        try:
            response = client.chat.completions.create(
                model=settings.groq_model,
                max_tokens=1024,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )
        except APIStatusError as e:
            return {
                "reply": f"The Insight Agent hit an API error ({e.status_code}): {e.message}",
                "tool_calls": tool_calls_log,
                "messages": messages,
            }

        choice_message = response.choices[0].message
        assistant_msg = {
            "role": "assistant",
            "content": choice_message.content,
        }
        if choice_message.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in choice_message.tool_calls
            ]
        messages.append(assistant_msg)

        if not choice_message.tool_calls:
            return {
                "reply": choice_message.content or "",
                "tool_calls": tool_calls_log,
                "messages": messages,
            }

        for tc in choice_message.tool_calls:
            tool_name = tc.function.name
            try:
                tool_input = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                tool_input = {}
            result = execute_tool(tool_name, tool_input)
            tool_calls_log.append({"tool": tool_name, "input": tool_input, "result": result})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

    return {
        "reply": "I made several tool calls but couldn't reach a final answer — "
                 "try rephrasing your question.",
        "tool_calls": tool_calls_log,
        "messages": messages,
    }
