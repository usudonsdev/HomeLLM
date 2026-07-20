# End-to-end Valorant ingest + analyzer demo on the desktop k3d cluster.
param(
    [string]$ClusterName = "homellm-demo",
    [string]$Filename = "demo_valorant.mp4"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

& "$PSScriptRoot\demo-valorant-ingest.ps1" -ClusterName $ClusterName -Filename $Filename

Write-Host "Starting port-forward on 8090 ..."
$pf = Start-Process -PassThru -WindowStyle Hidden -FilePath "kubectl" -ArgumentList @(
    "-n", "video-analysis", "port-forward", "svc/video-ingest-api", "8090:8090"
)
Start-Sleep -Seconds 2

try {
    Write-Host "Waiting for analyzer output ..."
    $deadline = (Get-Date).AddMinutes(3)
    $match = $null
    do {
        Start-Sleep -Seconds 5
        $matches = Invoke-RestMethod -Uri "http://127.0.0.1:8090/v1/matches"
        if ($matches.Count -gt 0) {
            $match = $matches[0]
        }
    } while (-not $match -and (Get-Date) -lt $deadline)

    if (-not $match) {
        throw "No analyzed matches were produced within timeout."
    }

    Write-Host "GET /v1/matches/$($match.id) ..."
    $detail = Invoke-RestMethod -Uri "http://127.0.0.1:8090/v1/matches/$($match.id)"
    $detail | ConvertTo-Json -Depth 6

    Write-Host "POST /v1/tips ..."
    $tipsBody = @{ match_ids = @($match.id); limit = 5 } | ConvertTo-Json -Depth 4
    $tips = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8090/v1/tips" `
        -ContentType "application/json" -Body $tipsBody
    $tips | ConvertTo-Json -Depth 6
}
finally {
    if ($pf -and -not $pf.HasExited) {
        Stop-Process -Id $pf.Id -Force -ErrorAction SilentlyContinue
    }
}
