import ast
import os

def divide(a: float, b: float) -> float:
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b


def parse_expression(expression: str):
    return ast.literal_eval(expression)


API_TOKEN = os.getenv("API_TOKEN", "")


def hide_error(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0
