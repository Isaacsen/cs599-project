# Final Submission Checklist

## Project Positioning

- [x] Direction: Agentic AI native development.
- [x] Topic: Software Engineer Agent with permission-isolated execution.
- [x] Core workflow: code review, auto bug-fix planning, unit-test generation, LLM test generation, sandboxed validation.

## Course Requirement Mapping

- [x] SDD: `docs/specs/product_spec.md`, `docs/specs/architecture_spec.md`, `docs/specs/api_spec.md`.
- [x] Tool use / Function Calling: repo scanner, security checker, sandbox executor, report writers, LLM client.
- [x] State management and multi-step reasoning: `Software Engineer Agent` combines review, fix, and unit-test reports.
- [x] Multi-agent collaboration: Code Reviewer, Bug Fixer, Unit Test Writer, LLM Test Generator.
- [x] Observability and evaluation: JSON artifacts and benchmark report.
- [x] Permission isolation: Docker sandbox, dry-run apply gates, generated-code security checker.

## Final Verification Commands

```bash
python -m unittest discover -s tests
python -m compileall src tests examples
python -m src.engineer examples/review_target --output docs/runs/software_engineer.json
python -m src.llm_tests examples/sample_python_project --mock-response examples/llm_response/pytest_response.md --output docs/runs/llm_tests.json
```

Windows PowerShell helper:

```powershell
scripts/final_verify.ps1
```

## Required Artifacts

- [x] `README.md`
- [x] `docs/architecture.md`
- [x] `docs/demo_guide.md`
- [x] `docs/artifacts.md`
- [x] `docs/CS599_大作业报告.md`
- [x] `docs/CS599_大作业报告.pdf`
- [x] `docs/runs/sample_run.json`
- [x] `docs/runs/benchmark.json`
- [x] `docs/runs/llm_prompt.json`
- [x] `docs/runs/llm_tests.json`
- [x] `docs/runs/review.json`
- [x] `docs/runs/fix_plan.json`
- [x] `docs/runs/unit_tests.json`
- [x] `docs/runs/software_engineer.json`

## Final Manual Items

- [ ] Fill student name and student ID in the report cover.
- [x] Export `docs/CS599_大作业报告.md` to a PDF with navigation/bookmarks.
- [ ] Add demo screenshots or a demo recording if required by the instructor.
- [ ] Confirm GitHub repository access for the instructor account if the repository is private.
