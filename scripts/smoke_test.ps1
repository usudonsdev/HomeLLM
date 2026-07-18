param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not $PSScriptRoot) { $root = Get-Location }
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Join-Path (Get-Location) "scripts" }

Write-Host "== GET /health =="
curl.exe -s "$BaseUrl/health"
Write-Host ""

Write-Host "== GET /health/ollama =="
curl.exe -s "$BaseUrl/health/ollama"
Write-Host ""

Write-Host "== POST /experiences =="
curl.exe -s -X POST "$BaseUrl/experiences" `
  -H "Content-Type: application/json" `
  --data-binary "@$scriptDir\smoke_payload_experience.json"
Write-Host ""

Write-Host "== GET /experiences =="
curl.exe -s "$BaseUrl/experiences"
Write-Host ""

Write-Host "== POST /rag/ask =="
curl.exe -s -X POST "$BaseUrl/rag/ask" `
  -H "Content-Type: application/json" `
  --data-binary "@$scriptDir\smoke_payload_rag.json"
Write-Host ""

Write-Host "Smoke test finished."
