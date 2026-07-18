# Apply video-analysis storage, RBAC, ingest API. Builds/imports images into k3d.
param(
    [string]$ClusterName = "homellm-demo"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "Building images ..."
docker build -t homellm/video-ingest-api:dev "$root\services\video-ingest-api"
docker build -t homellm/valorant-segmenter:dev "$root\services\valorant-segmenter"

Write-Host "Importing images into k3d '$ClusterName' ..."
k3d image import homellm/video-ingest-api:dev homellm/valorant-segmenter:dev -c $ClusterName

Write-Host "Ensuring base namespaces/quotas ..."
& "$PSScriptRoot\cluster-apply-base.ps1"

Write-Host "Applying video-analysis manifests ..."
kubectl apply -f "$root\k8s\video-analysis\media-pvc.yaml"
kubectl apply -f "$root\k8s\video-analysis\rbac.yaml"
kubectl delete job media-dirs-init -n video-analysis --ignore-not-found
kubectl apply -f "$root\k8s\video-analysis\media-dirs-init-job.yaml"
kubectl wait --for=condition=complete job/media-dirs-init -n video-analysis --timeout=120s
kubectl apply -f "$root\k8s\video-analysis\ingest-api.yaml"
kubectl -n video-analysis rollout status deployment/video-ingest-api --timeout=180s
kubectl -n video-analysis get pvc,sa,deploy,svc
Write-Host "video-analysis applied."
Write-Host "Port-forward: kubectl -n video-analysis port-forward svc/video-ingest-api 8090:8090"
