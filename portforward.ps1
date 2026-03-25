<#
  Forwards the k8s backend service to http://127.0.0.1:8000 (keep this window open while using the UI at :30080).
#>
param(
    [string]$Namespace = "kpn-genai",
    [string]$ReleaseName = "kpn"
)
$ErrorActionPreference = "Stop"
$svc = "$ReleaseName-kpn-genai-backend"
Write-Host "API port-forward: http://127.0.0.1:8000 -> svc/$svc (Ctrl+C to stop)" -ForegroundColor Green
kubectl port-forward -n $Namespace "svc/$svc" 8000:8000
