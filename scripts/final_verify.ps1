param(
    [string]$Python = "python",
    [string]$DockerImage = "software-engineer-agent-python:latest"
)

$ErrorActionPreference = "Stop"

Write-Host "[Software Engineer Agent Final Verify] Run unit tests"
& $Python -m unittest discover -s tests
if ($LASTEXITCODE -ne 0) {
    throw "Unit tests failed."
}

Write-Host "`n[Software Engineer Agent Final Verify] Run compile check"
& $Python -m compileall src tests examples
if ($LASTEXITCODE -ne 0) {
    throw "Compile check failed."
}

Write-Host "`n[Software Engineer Agent Final Verify] Build Docker sandbox image"
docker build -f Dockerfile.sandbox -t $DockerImage .
if ($LASTEXITCODE -ne 0) {
    throw "Docker sandbox image build failed."
}

Write-Host "`n[Software Engineer Agent Final Verify] Generate software engineer report"
& $Python -m src.engineer examples/review_target --run-sandbox --sandbox-executor docker --docker-image $DockerImage --output docs/runs/software_engineer.json --output-md docs/runs/software_engineer.md
if ($LASTEXITCODE -ne 0) {
    throw "Software engineer agent failed."
}

Write-Host "`n[Software Engineer Agent Final Verify] Generate LLM test report with configured provider"
& $Python -m src.llm_tests examples/sample_python_project --output docs/runs/llm_tests.json
if ($LASTEXITCODE -ne 0) {
    throw "LLM test generator failed."
}

Write-Host "`n[Software Engineer Agent Final Verify] Export final report PDF"
& $Python scripts/export_report_pdf.py
if ($LASTEXITCODE -ne 0) {
    throw "Final report PDF export failed."
}

Write-Host "`n[Software Engineer Agent Final Verify] Inspect final report PDF"
& $Python -c "from pathlib import Path; from pypdf import PdfReader; pdf=next(Path('docs').glob('CS599_*.pdf')); r=PdfReader(str(pdf)); assert len(r.pages) >= 5; assert r.outline; print(f'PDF pages: {len(r.pages)}')"
if ($LASTEXITCODE -ne 0) {
    throw "Final report PDF inspection failed."
}

Write-Host "`n[Software Engineer Agent Final Verify] Scan for possible plaintext API keys"
$SecretPattern = "(DASHSCOPE_API_KEY|DEEPSEEK_API_KEY|LLM_API_KEY)\s*=\s*[^\s#]+|sk-[A-Za-z0-9_-]{8,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{20,}"
& rg -n $SecretPattern -g "!课程要求.md" -g "!.git/**"
if ($LASTEXITCODE -eq 0) {
    throw "Possible plaintext API key found."
}
if ($LASTEXITCODE -ne 1) {
    throw "Secret scan failed."
}

Write-Host "`n[Software Engineer Agent Final Verify] Done"
