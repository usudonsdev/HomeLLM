# End-to-end Valorant inbox ingest demo on the desktop k3d cluster.
param(
    [string]$ClusterName = "homellm-demo",
    [string]$Filename = "demo_valorant.mp4"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

& "$PSScriptRoot\cluster-apply-video-analysis.ps1" -ClusterName $ClusterName

$seedDir = Join-Path $root ".local\seed"
New-Item -ItemType Directory -Force -Path $seedDir | Out-Null
$seedFile = Join-Path $seedDir $Filename

Write-Host "Generating short stub mp4 via ffmpeg container ..."
docker run --rm -v "${seedDir}:/out" linuxserver/ffmpeg:version-7.1-cli `
  -y -f lavfi -i "testsrc=size=320x240:rate=30" -f lavfi -i "sine=frequency=440:sample_rate=44100" `
  -t 6 -c:v libx264 -pix_fmt yuv420p -c:a aac "/out/$Filename"

$pod = kubectl -n video-analysis get pod -l app=video-ingest-api -o jsonpath='{.items[0].metadata.name}'
if (-not $pod) { throw "video-ingest-api pod not found" }

Write-Host "Copying $Filename into pod inbox ($pod) ..."
kubectl -n video-analysis exec $pod -- mkdir -p /media/inbox
Push-Location $seedDir
try {
    # Avoid Windows drive-letter paths: kubectl treats "C:" as a remote pod spec.
    kubectl -n video-analysis cp ".\$Filename" "${pod}:/media/inbox/$Filename"
}
finally {
    Pop-Location
}

Write-Host "Starting port-forward on 8090 ..."
$pf = Start-Process -PassThru -WindowStyle Hidden -FilePath "kubectl" -ArgumentList @(
    "-n", "video-analysis", "port-forward", "svc/video-ingest-api", "8090:8090"
)
Start-Sleep -Seconds 2

try {
    Write-Host "POST /v1/jobs ..."
    $body = @{ game = "valorant"; filename = $Filename } | ConvertTo-Json -Compress
    $created = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8090/v1/jobs" `
        -ContentType "application/json" -Body $body
    $created | ConvertTo-Json -Depth 5
    $jobId = $created.id

    Write-Host "Waiting for job $jobId to become ready/failed ..."
    $deadline = (Get-Date).AddMinutes(3)
    $final = $null
    do {
        Start-Sleep -Seconds 3
        $final = Invoke-RestMethod -Uri "http://127.0.0.1:8090/v1/jobs/$jobId"
        Write-Host ("  status=" + $final.status)
    } while ($final.status -notin @("ready", "failed") -and (Get-Date) -lt $deadline)

    $final | ConvertTo-Json -Depth 6
    if ($final.status -ne "ready") {
        throw "Valorant demo job did not reach ready (status=$($final.status) error=$($final.error))"
    }
    Write-Host "Valorant inbox ingest demo succeeded. rounds=$($final.round_count)"
}
finally {
    if ($pf -and -not $pf.HasExited) {
        Stop-Process -Id $pf.Id -Force -ErrorAction SilentlyContinue
    }
}
