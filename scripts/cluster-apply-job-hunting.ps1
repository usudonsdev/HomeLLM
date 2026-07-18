# Build API image, import into k3d, apply job-hunting workloads.
param(
    [string]$ClusterName = "homellm-demo",
    [string]$Image = "homellm/job-hunting-api:dev"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

$local = Join-Path $root ".local\k8s"
if (-not (Test-Path "$local\postgres-secret.yaml")) {
    & "$PSScriptRoot\secrets-materialize-demo.ps1"
}

Write-Host "Building $Image ..."
docker build -t $Image "$root\services\job-hunting-api"

Write-Host "Importing image into k3d cluster '$ClusterName' ..."
k3d image import $Image -c $ClusterName

Write-Host "Applying secrets + job-hunting manifests ..."
kubectl apply -f "$local\postgres-secret.yaml"
kubectl apply -f "$local\api-db-secret.yaml"
kubectl create configmap postgres-init `
  --from-file=01-init.sql="$root\services\job-hunting-api\sql\init.sql" `
  -n job-hunting `
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f "$root\k8s\job-hunting\postgres.yaml"
kubectl apply -f "$root\k8s\job-hunting\ollama-externalname.yaml"
kubectl apply -f "$root\k8s\job-hunting\api.yaml"

Write-Host "Waiting for postgres and api ..."
kubectl -n job-hunting rollout status deployment/postgres --timeout=180s
kubectl -n job-hunting rollout status deployment/job-hunting-api --timeout=180s
kubectl -n job-hunting get pods,svc
Write-Host "job-hunting applied. Port-forward example:"
Write-Host "  kubectl -n job-hunting port-forward svc/job-hunting-api 8000:8000"
