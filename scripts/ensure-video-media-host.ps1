# Ensure the host video drop folder exists (Documents\HomeLLM\videos\...).
# This is the user-facing path for large VODs and for k3d hostPath mounts.
param(
    [string]$Root = ""
)

$ErrorActionPreference = "Stop"

if (-not $Root) {
    $Root = Join-Path $env:USERPROFILE "Documents\HomeLLM\videos"
}

foreach ($name in @("inbox", "work", "rounds", "state", "done", "failed")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root $name) | Out-Null
}

Write-Host "Host video media ready:"
Write-Host "  $Root"
Write-Host "Drop large VODs here:"
Write-Host "  $(Join-Path $Root 'inbox')"
Write-Output $Root
