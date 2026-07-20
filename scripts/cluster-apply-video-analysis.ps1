# Apply video-analysis storage, RBAC, ingest API. Builds/imports images into k3d.
param(
    [string]$ClusterName = "homellm-demo"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
$local = Join-Path $root ".local\k8s"
if (-not (Test-Path "$local\video-postgres-secret.yaml")) {
    & "$PSScriptRoot\secrets-materialize-demo.ps1"
}

Write-Host "Building images ..."
docker build -t homellm/video-ingest-api:dev "$root\services\video-ingest-api"
docker build -t homellm/valorant-analyzer:dev "$root\services\valorant-analyzer"
docker build -t homellm/valorant-segmenter:dev "$root\services\valorant-segmenter"

Write-Host "Importing images into k3d '$ClusterName' ..."
k3d image import homellm/video-ingest-api:dev homellm/valorant-analyzer:dev homellm/valorant-segmenter:dev -c $ClusterName

Write-Host "Ensuring base namespaces/quotas ..."
& "$PSScriptRoot\cluster-apply-base.ps1"

Write-Host "Ensuring host video folder (Documents\HomeLLM\videos) ..."
& "$PSScriptRoot\ensure-video-media-host.ps1" | Out-Null

Write-Host "Applying video-analysis manifests ..."
# Switch from legacy local-path PVC to hostPath PV if needed.
$oldPvc = kubectl -n video-analysis get pvc video-media-pvc -o json 2>$null
if ($LASTEXITCODE -eq 0 -and $oldPvc) {
    $sc = kubectl -n video-analysis get pvc video-media-pvc -o jsonpath='{.spec.storageClassName}' 2>$null
    if ($sc -ne "homellm-video-hostpath") {
        Write-Host "Replacing legacy media PVC (storageClass=$sc) with hostPath Documents\HomeLLM\videos ..."
        kubectl -n video-analysis scale deployment/video-ingest-api --replicas=0
        kubectl -n video-analysis delete job --all --ignore-not-found
        kubectl -n video-analysis delete pvc video-media-pvc --wait=true
        kubectl -n video-analysis scale deployment/video-ingest-api --replicas=1
    }
}
kubectl apply -f "$root\k8s\video-analysis\media-pv.yaml"
kubectl apply -f "$local\video-postgres-secret.yaml"
kubectl apply -f "$local\video-api-db-secret.yaml"
kubectl create configmap postgres-init `
  --from-file=01-init.sql="$root\services\video-ingest-api\sql\init.sql" `
  -n video-analysis `
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f "$root\k8s\video-analysis\postgres.yaml"
kubectl apply -f "$root\k8s\video-analysis\rbac.yaml"
kubectl delete job media-dirs-init -n video-analysis --ignore-not-found
kubectl apply -f "$root\k8s\video-analysis\media-dirs-init-job.yaml"
kubectl wait --for=condition=complete job/media-dirs-init -n video-analysis --timeout=120s
kubectl apply -f "$root\k8s\video-analysis\ingest-api.yaml"
kubectl -n video-analysis rollout status deployment/postgres --timeout=180s
kubectl -n video-analysis rollout status deployment/video-ingest-api --timeout=180s
kubectl -n video-analysis get pvc,sa,deploy,svc
Write-Host "video-analysis applied."
Write-Host "Port-forward: kubectl -n video-analysis port-forward svc/video-ingest-api 8090:8090"
