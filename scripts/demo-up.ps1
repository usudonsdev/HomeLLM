# One-shot: create demo cluster + base + job-hunting management/runtime.
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot

& "$here\cluster-create-demo.ps1"
& "$here\cluster-apply-base.ps1"
& "$here\secrets-materialize-demo.ps1"
& "$here\cluster-apply-job-hunting.ps1"

Write-Host ""
Write-Host "Management plane + job-hunting demo stack is up."
Write-Host "Next: kubectl -n job-hunting port-forward svc/job-hunting-api 8000:8000"
Write-Host "Then: powershell -File scripts\smoke_test.ps1"
