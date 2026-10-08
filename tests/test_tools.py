import pytest

from data import STUDENTS
from tools import calculator, get_attendance, get_student_info


@pytest.mark.parametrize("expression,expected", [
    ("250 * 15 / 100", 37.5),
    ("25 * 40", 1000),
    ("2+3", 5),
    ("5-7", -2),
    ("-8/2", -4),
    ("(3+2)*4", 20),
    ("800 * 15 / 100", 120),
    ("120 / 800 * 100", 15),
])
def test_calculator_good(expression, expected):
    result = calculator(expression)
    assert result["status"] == "success"
    assert result["result"] == expected


@pytest.mark.parametrize("expression", [
    "10/0", "10+", "2**100000", "__import__('os').system('whoami')",
    "9 % 2", "1 << 2", "float('inf')", "", "9" * 180,
    "(1 + 2j)", "True + 1",
])
def test_calculator_rejects_unsafe_or_invalid(expression):
    assert calculator(expression)["status"] == "error"


def test_student_department():
    assert get_student_info(" Arun ") == {"status": "success", "name": "Arun", "department": "CSE"}
    assert get_student_info("arun")["department"] == "CSE"
    assert "attendance" not in get_student_info("Arun")


def test_attendance():
    assert get_attendance("PRIYA")["attendance"] == 91
    assert get_attendance("Arun")["attendance"] == 82
    assert "department" not in get_attendance("Priya")


def test_unknown_student_and_bad_name():
    assert get_attendance("Rahul")["status"] == "not_found"
    assert get_student_info("Rahul")["status"] == "not_found"
    assert get_attendance(5)["status"] == "error"
    assert get_student_info("  ")["status"] == "error"


def test_duplicate_names_are_not_guessed(monkeypatch):
    monkeypatch.setitem(STUDENTS, "103", {"name": "ARUN", "department": "EE", "attendance": 70})
    assert get_student_info("arun")["status"] == "ambiguous"
