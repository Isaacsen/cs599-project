from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.workflow.pipeline import PipelineReport


def report_to_dict(report: PipelineReport) -> dict[str, Any]:
    return {
        "scan": asdict(report.scan),
        "execution": asdict(report.execution),
        "analysis": asdict(report.analysis),
        "test_plan": asdict(report.test_plan) if report.test_plan else None,
        "generated_tests_enabled": report.generated_tests_enabled,
        "generated_suite": asdict(report.generated_suite) if report.generated_suite else None,
    }


def write_json_report(report: PipelineReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report_to_dict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
