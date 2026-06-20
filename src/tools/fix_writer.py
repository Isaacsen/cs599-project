from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.agents.bug_fixer import FixPlan


def fix_plan_to_dict(plan: FixPlan) -> dict[str, Any]:
    return {
        "project_path": plan.project_path,
        "applied": plan.applied,
        "summary": {
            "edit_count": plan.edit_count,
            "files_changed": plan.files_changed,
        },
        "edits": [asdict(edit) for edit in plan.edits],
    }


def write_fix_plan(plan: FixPlan, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(fix_plan_to_dict(plan), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
