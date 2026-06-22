from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.tools.agent_event_log import AgentEventLog, read_agent_events


class AgentEventLogTests(unittest.TestCase):
    def test_writes_jsonl_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "events.jsonl"
            event_log = AgentEventLog(output_path)

            event_log.append("node_start", "scan", "starting")
            event_log.append("node_end", "scan", "scanned", {"source_files": 2})
            written_path = event_log.write()

            self.assertEqual(output_path, written_path)
            events = read_agent_events(output_path)
            self.assertEqual(2, len(events))
            self.assertEqual(1, events[0]["sequence"])
            self.assertEqual("node_end", events[1]["event_type"])
            self.assertEqual({"source_files": 2}, events[1]["payload"])


if __name__ == "__main__":
    unittest.main()
