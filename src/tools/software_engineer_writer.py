from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.agents.software_engineer import SoftwareEngineerReport
from src.tools.fix_writer import fix_plan_to_dict
from src.tools.review_writer import review_report_to_dict
from src.tools.unit_test_writer import unit_test_report_to_dict


def software_engineer_report_to_dict(report: SoftwareEngineerReport) -> dict[str, Any]:
    return {
        "project_path": report.project_path,
        "summary": {
            "finding_count": report.finding_count,
            "fix_edit_count": report.fix_edit_count,
            "generated_test_count": report.generated_test_count,
            "fix_applied": report.fix_plan.applied,
            "unit_tests_applied": report.unit_tests.applied,
        },
        "scan": asdict(report.scan),
        "review": review_report_to_dict(report.review),
        "fix_plan": fix_plan_to_dict(report.fix_plan),
        "unit_tests": unit_test_report_to_dict(report.unit_tests),
    }


def write_software_engineer_report(report: SoftwareEngineerReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(software_engineer_report_to_dict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
