# Apply management-plane objects (namespaces, quotas, limitranges).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "Applying k8s/base ..."
kubectl apply -f "$root\k8s\base\namespaces.yaml"
kubectl apply -f "$root\k8s\base\resourcequotas.yaml"
kubectl apply -f "$root\k8s\base\limitranges.yaml"
kubectl get ns -l app.kubernetes.io/part-of=homellm
kubectl get resourcequota -A
kubectl get limitrange -A
Write-Host "Base management applied."
