def divide(a: float, b: float) -> float:
    return a / b


def parse_expression(expression: str):
    return eval(expression)


API_TOKEN = "unit-test-placeholder"


def hide_error(value: str) -> int:
    try:
        return int(value)
    except Exception:
        return 0
