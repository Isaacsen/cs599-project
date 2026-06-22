from __future__ import annotations

import queue
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import os

from src.engineer import _event_payload, _progress_status
from src.tools.agent_event_log import AgentEventLog
from src.tools.software_engineer_graph_writer import (
    software_engineer_graph_result_to_dict,
    llm_review_to_dict,
    llm_fix_plan_to_dict,
    llm_fix_to_dict,
    write_software_engineer_graph_result,
    write_software_engineer_markdown,
)
from src.tools.llm_test_writer import llm_test_report_to_dict
from src.workflow.software_engineer_graph import run_software_engineer_graph
from src.llm.streaming import clear_llm_stream_context, set_current_llm_node, set_llm_token_sink


ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "docs" / "runs" / "web"


@dataclass(frozen=True)
class RunRequest:
    project_path: str = "examples/review_target"
    apply_fixes: bool = False
    apply_tests: bool = False
    run_sandbox: bool = True
    sandbox_executor: str = "local"
    docker_image: str = "software-engineer-agent-python:latest"
    timeout_seconds: int = 30
    repair_iterations: int = 3
    llm_timeout: int | None = None
    llm_retries: int | None = None
    no_llm_token_stream: bool = True


@dataclass
class RunRecord:
    run_id: str
    request: RunRequest
    status: str = "queued"
    started_at: str | None = None
    finished_at: str | None = None
    error: str = ""
    report_path: Path | None = None
    markdown_path: Path | None = None
    events_path: Path | None = None
    cancel_requested: bool = False
    events: list[dict[str, Any]] = field(default_factory=list)
    event_queue: queue.Queue[dict[str, Any]] = field(default_factory=queue.Queue)


class RunCancelled(RuntimeError):
    pass


class RunManager:
    def __init__(self, runs_dir: Path = RUNS_DIR) -> None:
        self.runs_dir = runs_dir
        self._runs: dict[str, RunRecord] = {}
        self._lock = threading.Lock()

    def start_run(self, request: RunRequest) -> RunRecord:
        run_id = uuid.uuid4().hex[:12]
        record = RunRecord(run_id=run_id, request=request)
        with self._lock:
            self._runs[run_id] = record
        thread = threading.Thread(target=self._run_agent, args=(record,), daemon=True)
        thread.start()
        return record

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._lock:
            return self._runs.get(run_id)

    def list_runs(self) -> list[RunRecord]:
        with self._lock:
            return list(self._runs.values())

    def cancel_run(self, run_id: str) -> RunRecord | None:
        record = self.get_run(run_id)
        if record is None:
            return None
        if record.status in {"queued", "running"}:
            record.cancel_requested = True
            record.status = "cancelling"
        return record

    def _run_agent(self, record: RunRecord) -> None:
        request = record.request
        run_dir = self.runs_dir / record.run_id
        event_log = AgentEventLog(run_dir / "events.jsonl")
        record.status = "running"
        record.started_at = _now()
        self._emit(record, event_log, "run_start", "server", "Run started", {"request": asdict(request)})

        try:
            set_llm_token_sink(lambda node, token: self._emit_llm_token(record, event_log, node, token))
            _set_optional_env("LLM_TIMEOUT_SECONDS", request.llm_timeout)
            _set_optional_env("LLM_MAX_RETRIES", request.llm_retries)
            if request.no_llm_token_stream:
                os.environ.pop("LLM_STREAM_STDOUT", None)
            else:
                os.environ["LLM_STREAM_STDOUT"] = "1"

            result = run_software_engineer_graph(
                _resolve_project_path(request.project_path),
                apply_fixes=request.apply_fixes,
                apply_tests=request.apply_tests,
                run_sandbox=request.run_sandbox,
                sandbox_executor=request.sandbox_executor,
                docker_image=request.docker_image,
                timeout_seconds=request.timeout_seconds,
                repair_iterations=request.repair_iterations,
                progress_callback=lambda node, state: self._handle_progress(record, event_log, node, state),
            )
            record.report_path = run_dir / "software_engineer.json"
            record.markdown_path = run_dir / "software_engineer.md"
            write_software_engineer_graph_result(result, record.report_path)
            write_software_engineer_markdown(result, record.markdown_path)
            record.status = result.state.get("status", "completed")
            self._emit(
                record,
                event_log,
                "report",
                "final",
                record.status,
                {"report": software_engineer_graph_result_to_dict(result)},
            )
        except RunCancelled as exc:
            record.status = "cancelled"
            record.error = str(exc)
            self._emit(record, event_log, "cancelled", "server", str(exc), {})
        except Exception as exc:
            record.status = "failed"
            record.error = str(exc)
            self._emit(record, event_log, "error", "server", str(exc), {})
        finally:
            clear_llm_stream_context()
            record.finished_at = _now()
            self._emit(record, event_log, "run_end", "server", record.status, {"error": record.error})
            record.events_path = event_log.write()

    def _handle_progress(
        self,
        record: RunRecord,
        event_log: AgentEventLog,
        node: str,
        state: dict[str, Any],
    ) -> None:
        is_start = node.endswith(":start")
        base_node = node.removesuffix(":start")
        if record.cancel_requested:
            self._emit(record, event_log, "cancelled", base_node, f"Run cancelled before {base_node}", {})
            raise RunCancelled(f"Run cancelled before {base_node}")
        if is_start:
            set_current_llm_node(base_node)
        self._emit(
            record,
            event_log,
            "node_start" if is_start else "node_end",
            base_node,
            "starting" if is_start else _progress_status(base_node, state),
            _detailed_event_payload(base_node, state),
        )
        if not is_start:
            set_current_llm_node(None)
        if record.cancel_requested:
            self._emit(record, event_log, "cancelled", base_node, f"Run cancelled after {base_node}", {})
            raise RunCancelled(f"Run cancelled after {base_node}")

    def _emit(
        self,
        record: RunRecord,
        event_log: AgentEventLog,
        event_type: str,
        node: str,
        message: str,
        payload: dict[str, Any],
    ) -> None:
        event = event_log.append(event_type, node, message, payload)
        event_dict = asdict(event)
        record.events.append(event_dict)
        record.event_queue.put(event_dict)

    def _emit_llm_token(
        self,
        record: RunRecord,
        event_log: AgentEventLog,
        node: str,
        token: str,
    ) -> None:
        if record.cancel_requested:
            return
        self._emit(record, event_log, "llm_token", node, token, {"token": token})


def record_to_dict(record: RunRecord) -> dict[str, Any]:
    return {
        "run_id": record.run_id,
        "status": record.status,
        "started_at": record.started_at,
        "finished_at": record.finished_at,
        "error": record.error,
        "request": asdict(record.request),
        "report_path": str(record.report_path) if record.report_path else "",
        "markdown_path": str(record.markdown_path) if record.markdown_path else "",
        "events_path": str(record.events_path) if record.events_path else "",
        "cancel_requested": record.cancel_requested,
        "event_count": len(record.events),
    }


def _detailed_event_payload(node: str, state: dict[str, Any]) -> dict[str, Any]:
    payload = _event_payload(node, state)
    if node == "scan" and state.get("scan"):
        payload["scan"] = asdict(state["scan"])
    if node == "llm_review" and state.get("llm_review"):
        payload["llm_review"] = llm_review_to_dict(state["llm_review"])
    if node == "llm_fix_plan" and state.get("llm_fix_plan"):
        payload["llm_fix_plan"] = llm_fix_plan_to_dict(state["llm_fix_plan"])
    if node == "llm_fix" and state.get("llm_fix"):
        payload["llm_fix"] = llm_fix_to_dict(state["llm_fix"])
    if node == "llm_tests" and state.get("llm_tests"):
        payload["llm_tests"] = llm_test_report_to_dict(state["llm_tests"])
    if node == "sandbox_validate" and state.get("sandbox_validation"):
        payload["sandbox_validation"] = asdict(state["sandbox_validation"])
    if node == "repair_loop" and state.get("repair_loop"):
        payload["repair_loop"] = asdict(state["repair_loop"])
    if node == "coverage_feedback" and state.get("coverage_feedback"):
        payload["coverage_feedback"] = asdict(state["coverage_feedback"])
    return payload


def _resolve_project_path(project_path: str) -> Path:
    path = Path(project_path)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def _set_optional_env(name: str, value: int | None) -> None:
    if value is not None:
        os.environ[name] = str(value)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
