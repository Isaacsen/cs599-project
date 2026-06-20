param(
    [string]$Python = "python",
    [string]$DockerImage = "testguard-python:latest"
)

$ErrorActionPreference = "Stop"

Write-Host "[TestGuard Demo] Build Docker sandbox image"
docker build -f Dockerfile.sandbox -t $DockerImage .

Write-Host "`n[TestGuard Demo] Run unit tests"
& $Python -m unittest discover -s tests

Write-Host "`n[TestGuard Demo] Run compile check"
& $Python -m compileall src tests examples

Write-Host "`n[TestGuard Demo] Run agent pipeline in Docker sandbox"
& $Python -m src.main examples/sample_python_project --generate-tests --executor docker --docker-image $DockerImage --report-json docs/runs/sample_run.json

Write-Host "`n[TestGuard Demo] Export LLM prompt"
& $Python -m src.main examples/sample_python_project --generate-tests --executor docker --docker-image $DockerImage --export-llm-prompt docs/runs/llm_prompt.json

Write-Host "`n[TestGuard Demo] Run benchmark"
& $Python -m src.benchmark --executor docker --docker-image $DockerImage --output docs/runs/benchmark.json

Write-Host "`n[TestGuard Demo] Run code review agent"
& $Python -m src.review examples/review_target --output docs/runs/review.json

Write-Host "`n[TestGuard Demo] Generate bug fix plan"
& $Python -m src.fix examples/review_target --output docs/runs/fix_plan.json

Write-Host "`n[TestGuard Demo] Generate missing unit tests"
& $Python -m src.unit_tests examples/review_target --output docs/runs/unit_tests.json

Write-Host "`n[TestGuard Demo] Run software engineer agent"
& $Python -m src.engineer examples/review_target --output docs/runs/software_engineer.json

Write-Host "`n[TestGuard Demo] Done"
