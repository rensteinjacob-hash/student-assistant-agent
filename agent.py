"""LLM-driven tool selection, safe execution, history, and controlled failures."""

import json

from tools import APPROVED_TOOLS

DEFAULT_MODEL = "openai/gpt-oss-120b"
MAX_TOOL_ROUNDS = 5

SYSTEM_PROMPT = """You are an accurate, friendly university Student Assistant Agent.
You have three tools and must decide which tool (if any) to call based on meaning.
For calculations, always use calculator, even for simple arithmetic. Convert
natural-language percentages into expressions with + - * / and parentheses;
15% of 250 means 250*15/100; what percent 120 is of 800 means 120/800*100.
For a student's department, use get_student_info; for attendance, use
get_attendance. When asked for both, use both. Never fabricate student data:
use the appropriate tool. For general questions like 'What is Python?',
answer directly without calling unrelated tools. Ask for clarification when
the person or request is ambiguous. Understand pronouns using earlier messages.
Use tool results, including not_found and error statuses, honestly. Keep your
answers concise and beginner-friendly. Never claim a tool ran if it did not.
"""


def _schema(name: str, description: str, argument: str, argument_description: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {argument: {"type": "string", "description": argument_description}},
                "required": [argument],
                "additionalProperties": False,
            },
        },
    }


TOOL_SCHEMAS = [
    _schema(
        "calculator",
        "Use for all arithmetic: addition, subtraction, multiplication, division, percentages. "
        "Give a numeric expression using + - * / and parentheses; no percent symbol. "
        "Examples: 250 * 15 / 100; 15 percent of 250 -> 250*15/100; "
        "what percent is 120 of 800 -> 120/800*100.",
        "expression",
        "A mathematical expression with digits, +, -, *, /, parentheses; not Python code.",
    ),
    _schema(
        "get_student_info",
        "Lookup a student's DEPARTMENT from the local student dictionary; do NOT use for attendance.",
        "name",
        "Student's name, such as Arun. Use conversation context for references like 'he'.",
    ),
    _schema(
        "get_attendance",
        "Lookup a student's ATTENDANCE percentage from the local student dictionary; not department.",
        "name",
        "Student's name, such as Priya. Use conversation context for references like 'she'.",
    ),
]


def execute_tool(tool_name: str, raw_arguments: str) -> tuple[dict, dict]:
    """Parse and validate the LLM request before calling an approved function."""
    try:
        args = json.loads(raw_arguments)
    except (TypeError, ValueError):
        return {"status": "error", "message": "Malformed JSON tool arguments."}, {}
    if tool_name not in APPROVED_TOOLS:
        return {"status": "error", "message": "Unknown or unauthorized tool."}, args if isinstance(args, dict) else {}
    expected_key = "expression" if tool_name == "calculator" else "name"
    if not isinstance(args, dict) or set(args) != {expected_key} or not isinstance(args[expected_key], str):
        return {"status": "error", "message": f"Expected a string argument named '{expected_key}'."}, args if isinstance(args, dict) else {}
    try:
        return APPROVED_TOOLS[tool_name](**args), args
    except Exception:
        # Do not leak internal stack traces into user-visible LLM context.
        return {"status": "error", "message": "Internal tool error."}, args


class StudentAssistantAgent:
    def __init__(self, client, model: str = DEFAULT_MODEL):
        # Client injection also allows offline tests with a mock LLM.
        self.client = client
        self.model = model
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.last_tool_calls: list[dict] = []

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.last_tool_calls = []

    def ask(self, question: str) -> str:
        self.last_tool_calls = []
        if not isinstance(question, str) or not question.strip():
            return "Please enter a non-empty question."

        # Only commit to long-lived memory after successful completion.
        history = self.messages + [{"role": "user", "content": question.strip()}]
        for _round in range(MAX_TOOL_ROUNDS):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=history,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                    reasoning_format="hidden",
                    temperature=0.2,
                )
                msg = response.choices[0].message
            except Exception as exc:
                return (
                    f"LLM request failed ({type(exc).__name__}). "
                    "Check your API key, internet connection, Groq limits, and model name."
                )

            requested = msg.tool_calls or []
            if not requested:
                answer = (msg.content or "").strip()
                if not answer:
                    return "The model returned no answer. Please try a clearer question."
                history.append({"role": "assistant", "content": answer})
                self.messages = history
                return answer

            # Store the model's exact tool requests before storing their results.
            history.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in requested
                ],
            })
            for call in requested:
                result, args = execute_tool(call.function.name, call.function.arguments)
                self.last_tool_calls.append({"tool": call.function.name, "arguments": args, "result": result})
                history.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.function.name,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        return "I reached the tool-call safety limit. Please rephrase your request."
