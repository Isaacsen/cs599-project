# Project Artifacts

## Required Documents

- `README.md`: project entry point and run instructions.
- `docs/CS599_大作业报告.md`: final report source.
- `docs/CS599_大作业报告.pdf`: final report PDF.
- `docs/architecture.md`: architecture and LangGraph workflow description.
- `docs/specs/product_spec.md`: product spec.
- `docs/specs/architecture_spec.md`: architecture spec.
- `docs/specs/api_spec.md`: CLI and data structure spec.

## Demo Evidence

- `docs/runs/software_engineer.json`: main LangGraph Software Engineer Agent JSON report.
- `docs/runs/software_engineer.md`: readable Software Engineer Agent report.
- `docs/runs/software_engineer_agent_flow.png`: LangGraph-exported agent workflow image.
- `docs/runs/sample_run.json`: auxiliary test pipeline report.
- `docs/runs/benchmark.json`: benchmark report.
- `docs/runs/llm_prompt.json`: exported LLM test-generation prompt.
- `docs/runs/llm_tests.json`: LLM Test Generator report.

## Source Code

- `src/engineer.py`: canonical Software Engineer Agent CLI.
- `src/workflow/software_engineer_graph.py`: LangGraph StateGraph workflow.
- `src/tools/software_engineer_graph_writer.py`: JSON and Markdown report writer.
- `src/main.py`: auxiliary test pipeline CLI.
- `src/benchmark.py`: benchmark CLI.
- `src/llm_tests.py`: LLM Test Generator CLI.
- `src/agents/`: agent implementations.
- `src/llm/`: LLM config, prompt builder, and OpenAI-compatible client.
- `src/sandbox/`: local and Docker execution backends.
- `src/tools/`: scanner, workspaces, and report writers.

## Verification

- `tests/`: unit tests for agents, workflow, LLM helpers, sandbox policy, benchmark, and report behavior.
- `scripts/run_demo.ps1`: full demo script.
- `scripts/final_verify.ps1`: final verification script.
- `scripts/export_report_pdf.py`: PDF export script.
