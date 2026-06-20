from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.agents.code_reviewer import ReviewReport


def review_report_to_dict(report: ReviewReport) -> dict[str, Any]:
    return {
        "project_path": report.project_path,
        "summary": {
            "finding_count": report.finding_count,
            "high_count": report.high_count,
            "medium_count": report.medium_count,
            "low_count": report.low_count,
        },
        "findings": [asdict(finding) for finding in report.findings],
    }


def write_review_report(report: ReviewReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(review_report_to_dict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
