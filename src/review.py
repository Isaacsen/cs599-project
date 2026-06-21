from __future__ import annotations

import argparse
import sys

from src.agents.code_reviewer import format_review_report, review_repository
from src.tools.repo_scanner import scan_repository
from src.tools.review_writer import write_review_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Software Engineer Agent code review agent.")
    parser.add_argument("project_path", help="Path to the Python project to review.")
    parser.add_argument(
        "--output",
        default="docs/runs/review.json",
        help="Path to write the JSON review report.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        scan = scan_repository(args.project_path)
        report = review_repository(args.project_path, scan)
        output_path = write_review_report(report, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(format_review_report(report))
    print(f"\nReview Report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
