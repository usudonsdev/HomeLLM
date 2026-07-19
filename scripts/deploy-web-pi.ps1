# Build static Next.js site and deploy to Raspberry Pi over SSH.
# Prerequisites on desktop: Node/npm, OpenSSH client, filled .local/pi-deploy.env
# Prerequisites on Pi: rsync (or scp fallback), nginx (or python http.server)

param(
    [string]$EnvFile = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$web = Join-Path $root "services\web"
if (-not $EnvFile) {
    $EnvFile = Join-Path $root ".local\pi-deploy.env"
}

if (-not (Test-Path $EnvFile)) {
    Write-Host @"
Missing $EnvFile

Create it from the example:

  PI_SSH=pi@100.x.x.x
  PI_WEB_ROOT=/var/www/homellm
  # optional:
  # PI_SSH_PORT=22
  # PI_RELOAD_CMD=sudo systemctl reload nginx

Also set API URLs before build via services/web/.env.local (NEXT_PUBLIC_*).
"@
    exit 1
}

Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $pair = $_.Split("=", 2)
    if ($pair.Length -eq 2) {
        [System.Environment]::SetEnvironmentVariable($pair[0].Trim(), $pair[1].Trim(), "Process")
    }
}

$piSsh = $env:PI_SSH
$piRoot = $env:PI_WEB_ROOT
$port = if ($env:PI_SSH_PORT) { $env:PI_SSH_PORT } else { "22" }
$reload = $env:PI_RELOAD_CMD

if (-not $piSsh -or -not $piRoot) {
    throw "PI_SSH and PI_WEB_ROOT are required in $EnvFile"
}

Write-Host "Building static export..."
$outDir = Join-Path $web "out"
Push-Location $web
try {
    if (-not (Test-Path "node_modules")) {
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed ($LASTEXITCODE)" }
    }
    npm run build
}
finally {
    Pop-Location
}

if (-not (Test-Path (Join-Path $outDir "index.html"))) {
    # Windows often EBUSY-locks services/web/out (Explorer/OneDrive/IDE). Build in %TEMP% instead.
    Write-Host "In-tree out/ missing or locked; building under TEMP..."
    $tmp = Join-Path $env:TEMP "homellm-web-build"
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    robocopy $web $tmp /E /XD out .next node_modules /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
    $nm = Join-Path $web "node_modules"
    if (-not (Test-Path (Join-Path $tmp "node_modules"))) {
        cmd /c "mklink /J `"$(Join-Path $tmp 'node_modules')`" `"$nm`"" | Out-Null
    }
    $envLocal = Join-Path $web ".env.local"
    if (Test-Path $envLocal) { Copy-Item $envLocal (Join-Path $tmp ".env.local") -Force }
    Push-Location $tmp
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "TEMP npm run build failed ($LASTEXITCODE)" }
    }
    finally {
        Pop-Location
    }
    $outDir = Join-Path $tmp "out"
}

if (-not (Test-Path (Join-Path $outDir "index.html"))) {
    throw "Build output missing: $outDir"
}

Write-Host "Ensuring remote directory $piRoot ..."
ssh -p $port $piSsh "mkdir -p '$piRoot'"

Write-Host "Uploading out/ -> ${piSsh}:$piRoot (tar.gz, preserves tree on Windows) ..."
# Avoid `tar | ssh` on Windows — the pipe often corrupts the archive for GNU tar on the Pi.
# Avoid `scp out\*` — PowerShell flattens directories.
$archive = Join-Path $root ".local\web-out.tar.gz"
New-Item -ItemType Directory -Force -Path (Split-Path $archive) | Out-Null
if (Test-Path $archive) { Remove-Item $archive -Force }
tar -czf $archive -C $outDir .
ssh -p $port $piSsh "mkdir -p '$piRoot'"
scp -P $port $archive "${piSsh}:/tmp/homellm-web-out.tar.gz"
ssh -p $port $piSsh "find '$piRoot' -mindepth 1 -delete && tar -xzf /tmp/homellm-web-out.tar.gz -C '$piRoot' && rm -f /tmp/homellm-web-out.tar.gz && test -f '$piRoot/index.html' && test -f '$piRoot/videos/index.html'"

if ($reload) {
    Write-Host "Running remote reload: $reload"
    ssh -p $port $piSsh $reload
}

Write-Host "Deploy complete."
Write-Host "Open the Pi Tailscale URL (or LAN) serving $piRoot"
Write-Host "Browser must reach Windows API hosts set in NEXT_PUBLIC_* at build time."
