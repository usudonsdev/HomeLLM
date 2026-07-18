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
Push-Location $web
try {
    if (-not (Test-Path "node_modules")) {
        npm install
    }
    npm run build
}
finally {
    Pop-Location
}

$outDir = Join-Path $web "out"
if (-not (Test-Path $outDir)) {
    throw "Build output missing: $outDir"
}

Write-Host "Ensuring remote directory $piRoot ..."
ssh -p $port $piSsh "mkdir -p '$piRoot'"

Write-Host "Uploading out/ -> ${piSsh}:$piRoot ..."
# Prefer rsync if available on PATH; otherwise tar|ssh.
$rsync = Get-Command rsync -ErrorAction SilentlyContinue
if ($rsync) {
    & rsync -az --delete -e "ssh -p $port" "$outDir/" "${piSsh}:$piRoot/"
} else {
    Write-Host "rsync not found; using tar over ssh"
    Push-Location $outDir
    try {
        tar -cf - . | ssh -p $port $piSsh "mkdir -p '$piRoot' && tar -xf - -C '$piRoot'"
    }
    finally {
        Pop-Location
    }
}

if ($reload) {
    Write-Host "Running remote reload: $reload"
    ssh -p $port $piSsh $reload
}

Write-Host "Deploy complete."
Write-Host "Open the Pi Tailscale URL (or LAN) serving $piRoot"
Write-Host "Browser must reach Windows API hosts set in NEXT_PUBLIC_* at build time."
