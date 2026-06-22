from __future__ import annotations

import unittest

from src.llm.client import _read_streaming_content
from src.llm.streaming import clear_llm_stream_context, set_current_llm_node, set_llm_token_sink


class LLMStreamingTests(unittest.TestCase):
    def tearDown(self) -> None:
        clear_llm_stream_context()

    def test_streaming_content_emits_tokens_to_sink(self) -> None:
        emitted: list[tuple[str, str]] = []
        set_current_llm_node("llm_fix")
        set_llm_token_sink(lambda node, token: emitted.append((node, token)))

        response = [
            b'data: {"choices":[{"delta":{"content":"hello"}}]}\n',
            b'data: {"choices":[{"delta":{"content":" world"}}]}\n',
            b"data: [DONE]\n",
        ]

        result = _read_streaming_content(response)

        self.assertEqual("hello world", result)
        self.assertEqual([("llm_fix", "hello"), ("llm_fix", " world")], emitted)


if __name__ == "__main__":
    unittest.main()
