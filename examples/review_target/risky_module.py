# risky_module.py
import json
import os
from numbers import Number
from typing import Any


def divide(a: float, b: float) -> float:
    """返回 a / b。仅支持数字类型，非数字输入抛出 TypeError，除零抛出 ZeroDivisionError。"""
    if not isinstance(a, Number) or not isinstance(b, Number):
        raise TypeError(f"unsupported operand types for divide: {type(a).__name__}, {type(b).__name__}")
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b


def parse_expression(expression: str) -> Any:
    """解析 JSON 表达式，非法输入或解析失败时抛出 ValueError。"""
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("expression must be a non-empty string")
    try:
        return json.loads(expression)
    except json.JSONDecodeError as exc:
        raise ValueError(f"failed to parse expression: {exc}") from exc


# 保留模块级变量供现有代码读取，但不在导入时抛出异常
API_TOKEN = os.getenv("API_TOKEN", "")


def require_api_token() -> str:
    """延迟校验 API_TOKEN，仅在调用时抛出 RuntimeError。"""
    token = os.getenv("API_TOKEN")
    if not token:
        raise RuntimeError("API_TOKEN environment variable is not set")
    return token


def hide_error(value: str) -> int:
    """将字符串转换为整数，非法输入时抛出 ValueError。"""
    return int(value)
