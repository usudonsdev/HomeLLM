# Materialize secrets from examples into .local/ (gitignored). Safe defaults for demo only.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$local = Join-Path $root ".local\k8s"
New-Item -ItemType Directory -Force -Path $local | Out-Null

$pgExample = Join-Path $root "k8s\job-hunting\postgres-secret.example.yaml"
$apiExample = Join-Path $root "k8s\job-hunting\api-db-secret.example.yaml"
$pgOut = Join-Path $local "postgres-secret.yaml"
$apiOut = Join-Path $local "api-db-secret.yaml"
$videoPgExample = Join-Path $root "k8s\video-analysis\postgres-secret.example.yaml"
$videoApiExample = Join-Path $root "k8s\video-analysis\api-db-secret.example.yaml"
$videoPgOut = Join-Path $local "video-postgres-secret.yaml"
$videoApiOut = Join-Path $local "video-api-db-secret.yaml"

$user = "homellm"
$pass = "local-demo-only-change-me"
$dbUrl = "postgresql+psycopg://${user}:${pass}@postgres:5432/homellm"
$videoDbUrl = "postgresql+psycopg://${user}:${pass}@postgres:5432/homellm_video"

@(
    "apiVersion: v1",
    "kind: Secret",
    "metadata:",
    "  name: postgres-secret",
    "  namespace: job-hunting",
    "type: Opaque",
    "stringData:",
    "  POSTGRES_USER: `"$user`"",
    "  POSTGRES_PASSWORD: `"$pass`"",
    "  POSTGRES_DB: `"homellm`""
) | Set-Content -Path $pgOut -Encoding utf8

@(
    "apiVersion: v1",
    "kind: Secret",
    "metadata:",
    "  name: api-db-secret",
    "  namespace: job-hunting",
    "type: Opaque",
    "stringData:",
    "  DATABASE_URL: `"$dbUrl`""
) | Set-Content -Path $apiOut -Encoding utf8

@(
    "apiVersion: v1",
    "kind: Secret",
    "metadata:",
    "  name: postgres-secret",
    "  namespace: video-analysis",
    "type: Opaque",
    "stringData:",
    "  POSTGRES_USER: `"$user`"",
    "  POSTGRES_PASSWORD: `"$pass`"",
    "  POSTGRES_DB: `"homellm_video`""
) | Set-Content -Path $videoPgOut -Encoding utf8

@(
    "apiVersion: v1",
    "kind: Secret",
    "metadata:",
    "  name: api-db-secret",
    "  namespace: video-analysis",
    "type: Opaque",
    "stringData:",
    "  DATABASE_URL: `"$videoDbUrl`""
) | Set-Content -Path $videoApiOut -Encoding utf8

Write-Host "Wrote demo secrets under .local/k8s/ (gitignored)."
Write-Host "Sources referenced: $pgExample , $apiExample , $videoPgExample , $videoApiExample"
Write-Host "For production, replace passwords before applying on the notebook."
