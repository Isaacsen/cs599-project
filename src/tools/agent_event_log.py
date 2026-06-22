from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AgentEvent:
    sequence: int
    event_type: str
    node: str
    message: str
    timestamp: str
    payload: dict[str, Any] = field(default_factory=dict)


class AgentEventLog:
    def __init__(self, output_path: str | Path) -> None:
        self.output_path = Path(output_path)
        self.events: list[AgentEvent] = []

    def append(
        self,
        event_type: str,
        node: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> AgentEvent:
        event = AgentEvent(
            sequence=len(self.events) + 1,
            event_type=event_type,
            node=node,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=payload or {},
        )
        self.events.append(event)
        return event

    def write(self) -> Path:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(asdict(event), ensure_ascii=False, separators=(",", ":")) for event in self.events]
        self.output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return self.output_path


def read_agent_events(path: str | Path) -> list[dict[str, Any]]:
    event_path = Path(path)
    if not event_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in event_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events
