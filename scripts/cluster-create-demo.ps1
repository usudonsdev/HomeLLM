# Requires: Docker Desktop running, k3d, kubectl
param(
    [string]$ClusterName = "homellm-demo",
    [int]$ApiPort = 8080
)

$ErrorActionPreference = "Stop"

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "Creating k3d cluster '$ClusterName' (k3s-in-Docker demo)..."
$existing = k3d cluster list -o json | ConvertFrom-Json | Where-Object { $_.name -eq $ClusterName }
if ($existing) {
    Write-Host "Cluster already exists. Skipping create."
} else {
    k3d cluster create $ClusterName `
        --agents 0 `
        --port "${ApiPort}:80@loadbalancer" `
        --k3s-arg "--disable=traefik@server:0"
}

k3d kubeconfig merge $ClusterName --kubeconfig-switch-context
kubectl config use-context "k3d-$ClusterName"
kubectl cluster-info
Write-Host "Demo cluster ready. Context: k3d-$ClusterName"
