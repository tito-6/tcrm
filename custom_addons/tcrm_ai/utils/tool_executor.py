# Part of TCRM AI. See LICENSE for details.

"""
ReAct-style multi-step tool execution loop.
Calls Gemini; if response is a tool call, runs the tool and appends result to messages; repeats until natural language answer or max rounds.
"""

import json
import re
import logging

_logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5


def parse_tool_call(text):
    """
    Extract (tool_name, args) from model response, or None if not a tool call.
    Tries code block first, then raw JSON.
    """
    if not text or not isinstance(text, str):
        return None
    stripped = text.strip()
    # 1) Code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if match:
        try:
            payload = json.loads(match.group(1))
            if isinstance(payload, dict) and payload.get("tool") and payload.get("args") is not None:
                return payload.get("tool"), payload.get("args") or {}
        except json.JSONDecodeError:
            pass
    # 2) Raw JSON
    for block in (stripped, stripped.split("\n")[0] if "\n" in stripped else None):
        if not block:
            continue
        try:
            payload = json.loads(block)
            if isinstance(payload, dict) and payload.get("tool") and payload.get("args") is not None:
                return payload.get("tool"), payload.get("args") or {}
        except json.JSONDecodeError:
            pass
    return None


def execute_with_tools(messages_text, tools_map, call_gemini_fn):
    """
    ReAct loop. messages_text is the full prompt string for the first call.
    call_gemini_fn(single_prompt_str) -> response text.
    Returns (final_answer_text, list of tool result dicts for tables/links).
    """
    current_prompt = messages_text
    tool_results = []  # list of dicts with keys rows, links, link

    for _ in range(MAX_TOOL_ROUNDS):
        response = call_gemini_fn(current_prompt)
        if not response or not (response if isinstance(response, str) else getattr(response, "strip", lambda: "")()):
            break
        response = (response or "").strip()
        parsed = parse_tool_call(response)
        if parsed and parsed[0] in tools_map:
            tool_name, args = parsed
            try:
                result = tools_map[tool_name](**args)
                data = json.loads(result) if isinstance(result, str) else result
                if isinstance(data, dict):
                    tool_results.append(data)
                # Append assistant message + tool result to prompt for next round
                current_prompt = (
                    current_prompt
                    + "\n\nAssistant (tool call):\n"
                    + response
                    + "\n\nTool result:\n"
                    + (result if isinstance(result, str) else json.dumps(result))
                    + "\n\nReply in natural language only. Summarize for the user with numbers and TCRM links. Do NOT output JSON or code."
                )
                continue
            except (TypeError, KeyError, Exception) as e:
                _logger.warning("TCRM AI tool run error: %s", e)
                current_prompt = (
                    current_prompt
                    + "\n\nAssistant (tool call):\n"
                    + response
                    + "\n\nTool error: "
                    + str(e)
                    + "\n\nReply in natural language. If you cannot complete the request, say so politely."
                )
                continue
        # Natural language answer
        return response, tool_results

    return "", tool_results
