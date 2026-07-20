# Delete smoke-test experiences from job-hunting Postgres (k3d/k3s).
# Default title matches scripts/smoke_payload_experience.json
param(
    [string]$Title = "HomeLLM smoke experience",
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$encoded = [uri]::EscapeDataString($Title)
Write-Host "DELETE $BaseUrl/experiences?title=$Title"
$res = curl.exe -s -X DELETE "$BaseUrl/experiences?title=$encoded"
Write-Host $res
