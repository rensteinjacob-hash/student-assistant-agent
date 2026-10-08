"""Offline tests: the mock LLM requests tools; the real Python tools execute."""

import json
from copy import deepcopy
from types import SimpleNamespace as NS

from agent import MAX_TOOL_ROUNDS, StudentAssistantAgent, TOOL_SCHEMAS, execute_tool


def response(content=None, calls=None):
    return NS(choices=[NS(message=NS(content=content, tool_calls=calls))])


def tool_call(name, arguments, call_id="call_1"):
    return NS(id=call_id, function=NS(name=name, arguments=arguments))


class MockClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.received = []
        self.chat = NS(completions=NS(create=self.create))

    def create(self, **kwargs):
        self.received.append(deepcopy(kwargs))
        if not self.responses:
            raise RuntimeError("Mock response was not configured")
        current = self.responses.pop(0)
        if isinstance(current, Exception):
            raise current
        return current


def test_calculator_tool_loop():
    mock = MockClient(
        response(calls=[tool_call("calculator", json.dumps({"expression": "250*15/100"}))]),
        response(content="37.5"),
    )
    agent = StudentAssistantAgent(mock)
    assert agent.ask("Calculate 250 * 15 / 100") == "37.5"
    assert agent.last_tool_calls[0]["tool"] == "calculator"
    assert agent.last_tool_calls[0]["result"]["result"] == 37.5
    assert mock.received[1]["messages"][-1]["role"] == "tool"
    assert mock.received[1]["messages"][-1]["tool_call_id"] == "call_1"
    assert len(TOOL_SCHEMAS) == 3


def test_department_attendance_and_unknown():
    for name, arguments, expected in [
        ("get_student_info", {"name": "Arun"}, {"department": "CSE"}),
        ("get_attendance", {"name": "Priya"}, {"attendance": 91}),
        ("get_attendance", {"name": "Rahul"}, {"status": "not_found"}),
    ]:
        mock = MockClient(response(calls=[tool_call(name, json.dumps(arguments))]), response(content="Done"))
        agent = StudentAssistantAgent(mock)
        assert agent.ask("Test") == "Done"
        assert agent.last_tool_calls[0]["tool"] == name
        assert all(agent.last_tool_calls[0]["result"].get(k) == v for k, v in expected.items())


def test_general_question_no_tool():
    mock = MockClient(response(content="Python is a programming language."))
    agent = StudentAssistantAgent(mock)
    assert "programming language" in agent.ask("What is Python?")
    assert agent.last_tool_calls == []
    assert len(mock.received) == 1


def test_memory_with_follow_up():
    mock = MockClient(
        response(calls=[tool_call("get_attendance", '{"name":"Arun"}')]),
        response(content="Arun has 82% attendance."),
        response(calls=[tool_call("get_student_info", '{"name":"Arun"}', "call_2")]),
        response(content="He is in CSE."),
    )
    agent = StudentAssistantAgent(mock)
    assert "82%" in agent.ask("What is Arun's attendance?")
    assert "CSE" in agent.ask("What department is he in?")
    assert any(m["content"] == "What is Arun's attendance?" for m in mock.received[2]["messages"] if m["role"] == "user")
    agent.reset()
    assert len(agent.messages) == 1


def test_invalid_tool_call_arguments_are_safe():
    for tool_name, args in [
        ("calculator", '{invalid'),
        ("calculator", '{"expression": 42}'),
        ("calculator", '{"expression":"2+2","other":1}'),
        ("unapproved_function", '{}'),
        ("get_attendance", '[]'),
    ]:
        result, _ = execute_tool(tool_name, args)
        assert result["status"] == "error"


def test_empty_request_does_not_call_model():
    mock = MockClient()
    agent = StudentAssistantAgent(mock)
    assert "non-empty" in agent.ask("   ")
    assert len(mock.received) == 0


def test_network_failure_does_not_crash_or_commit_memory():
    mock = MockClient(ConnectionError("simulated outage"))
    agent = StudentAssistantAgent(mock)
    assert "request failed" in agent.ask("Hi")
    assert len(agent.messages) == 1


def test_repeated_calls_stop_at_safety_limit():
    mock = MockClient(*[
        response(calls=[tool_call("calculator", '{"expression":"2+2"}', f"call_{i}")])
        for i in range(MAX_TOOL_ROUNDS)
    ])
    agent = StudentAssistantAgent(mock)
    assert "safety limit" in agent.ask("Calculate something")
    assert len(mock.received) == MAX_TOOL_ROUNDS
    assert len(agent.messages) == 1


def test_tool_call_and_result_order_is_preserved():
    mock = MockClient(
        response(calls=[
            tool_call("get_student_info", '{"name":"Arun"}', "a"),
            tool_call("get_attendance", '{"name":"Arun"}', "b"),
        ]),
        response(content="Arun is from CSE and has 82% attendance."),
    )
    agent = StudentAssistantAgent(mock)
    assert "CSE" in agent.ask("What is Arun's department and attendance?")
    roles = [m["role"] for m in mock.received[1]["messages"]]
    assert roles[-3:] == ["assistant", "tool", "tool"]
    assert [t["tool"] for t in agent.last_tool_calls] == ["get_student_info", "get_attendance"]
