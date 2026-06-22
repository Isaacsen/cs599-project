from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.server.run_manager import ROOT, RunManager, RunRequest, record_to_dict


WEB_DIR = ROOT / "web" / "agent-viewer"
DOCS_DIR = ROOT / "docs"

app = FastAPI(title="Software Engineer Agent Server")
manager = RunManager()

app.mount("/viewer", StaticFiles(directory=str(WEB_DIR), html=True), name="viewer")
app.mount("/docs", StaticFiles(directory=str(DOCS_DIR)), name="docs")


class StartRunPayload(BaseModel):
    project_path: str = Field(default="examples/review_target")
    apply_fixes: bool = False
    apply_tests: bool = False
    run_sandbox: bool = True
    sandbox_executor: str = Field(default="local", pattern="^(local|docker)$")
    docker_image: str = "software-engineer-agent-python:latest"
    timeout_seconds: int = Field(default=30, ge=1, le=600)
    repair_iterations: int = Field(default=3, ge=0, le=10)
    llm_timeout: int | None = Field(default=None, ge=1, le=600)
    llm_retries: int | None = Field(default=None, ge=0, le=5)
    no_llm_token_stream: bool = True


@app.get("/")
def index() -> RedirectResponse:
    return RedirectResponse(url="/viewer/")


@app.post("/api/runs")
def start_run(payload: StartRunPayload) -> dict[str, Any]:
    record = manager.start_run(RunRequest(**payload.model_dump()))
    return record_to_dict(record)


@app.get("/api/runs")
def list_runs() -> dict[str, Any]:
    return {"runs": [record_to_dict(record) for record in manager.list_runs()]}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    record = manager.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return record_to_dict(record)


@app.post("/api/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict[str, Any]:
    record = manager.cancel_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return record_to_dict(record)


@app.get("/api/runs/{run_id}/events")
def stream_events(run_id: str) -> EventSourceResponse:
    record = manager.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return EventSourceResponse(_event_generator(record))


@app.get("/api/runs/{run_id}/report")
def get_report(run_id: str) -> dict[str, Any]:
    record = manager.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    for event in reversed(record.events):
        if event.get("event_type") == "report":
            return event.get("payload", {}).get("report", {})
    if record.report_path and record.report_path.exists():
        return json.loads(record.report_path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="Report is not ready")


@app.get("/api/runs/{run_id}/markdown")
def get_markdown(run_id: str) -> FileResponse:
    record = manager.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if not record.markdown_path or not record.markdown_path.exists():
        raise HTTPException(status_code=404, detail="Markdown report is not ready")
    return FileResponse(record.markdown_path, media_type="text/markdown")


async def _event_generator(record):
    sent = 0
    while True:
        while sent < len(record.events):
            event = record.events[sent]
            sent += 1
            yield {"event": event["event_type"], "data": json.dumps(event, ensure_ascii=False)}

        if record.status not in {"queued", "running", "cancelling"}:
            break

        await asyncio.sleep(0.5)
        yield {"event": "heartbeat", "data": "{}"}


def main() -> None:
    import uvicorn

    uvicorn.run("src.server.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
