param(
    [string]$ClusterName = "homellm-demo"
)

$ErrorActionPreference = "Stop"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "Deleting k3d cluster '$ClusterName'..."
k3d cluster delete $ClusterName
Write-Host "Deleted."
