import pytest

from calculator import add, divide


def test_add() -> None:
    assert add(1, 2) == 3


def test_divide() -> None:
    assert divide(4, 2) == 2


def test_divide_by_zero() -> None:
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)
