param(
    [string]$Python = "python",
    [string]$DockerImage = "software-engineer-agent-python:latest"
)

$ErrorActionPreference = "Stop"

Write-Host "[Software Engineer Agent Demo] Build Docker sandbox image"
docker build -f Dockerfile.sandbox -t $DockerImage .

Write-Host "`n[Software Engineer Agent Demo] Run unit tests"
& $Python -m unittest discover -s tests

Write-Host "`n[Software Engineer Agent Demo] Run compile check"
& $Python -m compileall src tests examples

Write-Host "`n[Software Engineer Agent Demo] Run full software engineer agent"
& $Python -m src.engineer examples/review_target --run-sandbox --sandbox-executor docker --docker-image $DockerImage --output docs/runs/software_engineer.json --output-md docs/runs/software_engineer.md

Write-Host "`n[Software Engineer Agent Demo] Run auxiliary test pipeline in Docker sandbox"
& $Python -m src.main examples/sample_python_project --generate-tests --executor docker --docker-image $DockerImage --report-json docs/runs/sample_run.json

Write-Host "`n[Software Engineer Agent Demo] Export LLM prompt"
& $Python -m src.main examples/sample_python_project --generate-tests --executor docker --docker-image $DockerImage --export-llm-prompt docs/runs/llm_prompt.json

Write-Host "`n[Software Engineer Agent Demo] Run benchmark"
& $Python -m src.benchmark --executor docker --docker-image $DockerImage --output docs/runs/benchmark.json

Write-Host "`n[Software Engineer Agent Demo] Run LLM test generator with configured provider"
& $Python -m src.llm_tests examples/sample_python_project --output docs/runs/llm_tests.json

Write-Host "`n[Software Engineer Agent Demo] Done"
