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

Write-Host "`n[TestGuard Demo] Done"
