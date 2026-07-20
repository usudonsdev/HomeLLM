# Ensure the host video drop folder exists (Documents\HomeLLM\videos\...).
# This is the user-facing path for large VODs and for k3d hostPath mounts.
param(
    [string]$Root = ""
)

$ErrorActionPreference = "Stop"

if (-not $Root) {
    $Root = Join-Path $env:USERPROFILE "Documents\HomeLLM\videos"
}

foreach ($name in @("inbox", "work", "rounds", "state", "done", "failed", "templates\valorant")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root $name) | Out-Null
}

$readme = Join-Path $Root "templates\valorant\README.txt"
if (-not (Test-Path $readme)) {
    @(
        "Put Valorant inter-round logo PNG/JPG templates here.",
        "The segmenter matches these against sampled frames (OpenCV).",
        "If empty, transition-spike detection is used, then time fallback."
    ) | Set-Content -Path $readme -Encoding utf8
}

Write-Host "Host video media ready:"
Write-Host "  $Root"
Write-Host "Drop large VODs here:"
Write-Host "  $(Join-Path $Root 'inbox')"
Write-Host "Logo templates (optional but recommended):"
Write-Host "  $(Join-Path $Root 'templates\valorant')"
Write-Output $Root
