"""Interactive Windows/Linux terminal entry point."""

import json
import os

from dotenv import load_dotenv
from agent import DEFAULT_MODEL, StudentAssistantAgent


def main() -> None:
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key == "replace_with_your_actual_key":
        print("Missing GROQ_API_KEY. Copy .env.example to .env and paste your own Groq API key.")
        return

    try:
        from groq import Groq
    except ImportError:
        print("Missing Groq SDK. Run: python -m pip install -r requirements.txt")
        return

    client = Groq(api_key=api_key, timeout=30.0, max_retries=1)
    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    agent = StudentAssistantAgent(client=client, model=model)
    show_trace = True

    print("\nStudent Assistant Agent | Model:", model)
    print("Commands: /exit, /reset, /trace on, /trace off")
    print("Ask a question (e.g. Calculate 250 * 15 / 100).\n")
    while True:
        try:
            question = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
        if question.casefold() == "/exit":
            print("Goodbye!")
            break
        if question.casefold() == "/reset":
            agent.reset()
            print("Conversation memory cleared.\n")
            continue
        if question.casefold() in ("/trace on", "/trace off"):
            show_trace = question.casefold() == "/trace on"
            print("Trace is", "on" if show_trace else "off", "\n")
            continue
        if not question:
            print("Enter a non-empty question.\n")
            continue

        answer = agent.ask(question)
        if show_trace:
            if not agent.last_tool_calls:
                print("  [TRACE] No local tool called")
            for trace in agent.last_tool_calls:
                print("  [TRACE] LLM chose:", trace["tool"])
                print("  [TRACE] Arguments:", json.dumps(trace["arguments"], ensure_ascii=False))
                print("  [TRACE] Tool result:", json.dumps(trace["result"], ensure_ascii=False))
        print("Agent:", answer, "\n")


if __name__ == "__main__":
    main()
