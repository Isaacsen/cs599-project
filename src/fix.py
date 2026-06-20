from __future__ import annotations

import argparse
import sys

from src.agents.bug_fixer import fix_repository, format_fix_plan
from src.tools.fix_writer import write_fix_plan
from src.tools.repo_scanner import scan_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run TestGuard bug fixer agent.")
    parser.add_argument("project_path", help="Path to the Python project to fix.")
    parser.add_argument(
        "--output",
        default="docs/runs/fix_plan.json",
        help="Path to write the JSON fix plan.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply safe automatic fixes to the target project. Omit for dry-run planning.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        scan = scan_repository(args.project_path)
        plan = fix_repository(args.project_path, scan, apply_changes=args.apply)
        output_path = write_fix_plan(plan, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(format_fix_plan(plan))
    print(f"\nFix Plan: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
