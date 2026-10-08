"""Small, independently testable, safe tools used by the LLM agent."""

import ast
import math
import operator

from data import STUDENTS

# Never use eval() on user- or model-generated expressions.
_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_MAX_ABS_VALUE = 1_000_000_000_000
_MAX_EXPRESSION_LENGTH = 140
_MAX_TREE_DEPTH = 16


def _check_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Only numbers and +, -, *, /, parentheses are supported.")
    if not math.isfinite(value) or abs(value) > _MAX_ABS_VALUE:
        raise ValueError("The numeric value is too large or invalid.")
    return value


def _evaluate(node, depth=0):
    """Evaluate an allowlisted arithmetic AST, rejecting all Python code."""
    if depth > _MAX_TREE_DEPTH:
        raise ValueError("The expression is too complex.")
    if isinstance(node, ast.Expression):
        return _evaluate(node.body, depth + 1)
    if isinstance(node, ast.Constant):
        return _check_number(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate(node.left, depth + 1)
        right = _evaluate(node.right, depth + 1)
        if isinstance(node.op, ast.Div) and right == 0:
            raise ZeroDivisionError("Cannot divide by zero.")
        return _check_number(_BINARY_OPERATORS[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _check_number(_UNARY_OPERATORS[type(node.op)](_evaluate(node.operand, depth + 1)))
    raise ValueError("Unsupported expression. Use numbers, +, -, *, /, and parentheses.")


def calculator(expression: str) -> dict:
    """Calculate arithmetic safely; percentages use arithmetic (e.g., 250*15/100)."""
    if not isinstance(expression, str) or not expression.strip():
        return {"status": "error", "message": "Provide a non-empty arithmetic expression."}
    if len(expression) > _MAX_EXPRESSION_LENGTH:
        return {"status": "error", "message": "Expression is too long."}
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        value = _evaluate(tree)
        # Normalize tiny floating-point artifacts for readable answers.
        if isinstance(value, float):
            value = round(value, 10)
        return {"status": "success", "expression": expression, "result": value}
    except (SyntaxError, ValueError, OverflowError, ZeroDivisionError) as exc:
        return {"status": "error", "message": str(exc) if not isinstance(exc, SyntaxError) else "Malformed arithmetic expression."}


def _lookup_student(name: str) -> dict:
    if not isinstance(name, str) or not name.strip():
        return {"status": "error", "message": "Provide a student name."}
    query = name.strip().casefold()
    matches = [record for record in STUDENTS.values() if record["name"].casefold() == query]
    if not matches:
        return {"status": "not_found", "message": f"Student {name.strip()} was not found in the database."}
    if len(matches) > 1:
        return {"status": "ambiguous", "message": "More than one student has that name; ask for the student ID."}
    return {"status": "success", "student": matches[0]}


def get_student_info(name: str) -> dict:
    """Return only the selected student's department (not attendance)."""
    result = _lookup_student(name)
    if result["status"] != "success":
        return result
    student = result["student"]
    return {"status": "success", "name": student["name"], "department": student["department"]}


def get_attendance(name: str) -> dict:
    """Return only the selected student's attendance (not department)."""
    result = _lookup_student(name)
    if result["status"] != "success":
        return result
    student = result["student"]
    return {"status": "success", "name": student["name"], "attendance": student["attendance"]}


# This registry controls which Python functions may execute. It does NOT
# select a tool based on user keywords; the LLM selects the tool.
APPROVED_TOOLS = {
    "calculator": calculator,
    "get_student_info": get_student_info,
    "get_attendance": get_attendance,
}
