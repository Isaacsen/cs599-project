from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.agents.unit_test_writer import UnitTestReport


def unit_test_report_to_dict(report: UnitTestReport) -> dict[str, Any]:
    return {
        "project_path": report.project_path,
        "applied": report.applied,
        "test_file_path": report.test_file_path,
        "summary": {
            "planned_test_count": report.planned_test_count,
            "generated_test_count": report.generated_test_count,
            "security_check_passed": report.security_check.passed,
        },
        "test_plan": asdict(report.test_plan),
        "security_check": asdict(report.security_check),
        "suite": asdict(report.suite),
    }


def write_unit_test_report(report: UnitTestReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(unit_test_report_to_dict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
