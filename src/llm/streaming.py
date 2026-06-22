from __future__ import annotations

import threading
from collections.abc import Callable


TokenSink = Callable[[str, str], None]

_state = threading.local()


def set_llm_token_sink(sink: TokenSink | None) -> None:
    _state.token_sink = sink


def set_current_llm_node(node: str | None) -> None:
    _state.current_node = node


def clear_llm_stream_context() -> None:
    _state.token_sink = None
    _state.current_node = None


def has_llm_token_sink() -> bool:
    return callable(getattr(_state, "token_sink", None))


def emit_llm_token(token: str) -> None:
    sink = getattr(_state, "token_sink", None)
    if not callable(sink):
        return
    node = getattr(_state, "current_node", "") or "llm"
    sink(node, token)
