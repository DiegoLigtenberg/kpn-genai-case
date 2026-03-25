<#
.SYNOPSIS
  Build Docker images, deploy with Helm to Kubernetes, wait for rollouts.

.DESCRIPTION
  Defaults: namespace kpn-genai, Helm release name kpn (service prefix kpn-kpn-genai-*).
  After deploy, open http://127.0.0.1:30080 and run the printed port-forward in a second terminal.

.EXAMPLE
  .\runkubernetes.ps1
.EXAMPLE
  .\runkubernetes.ps1 -UseOpenAI
.EXAMPLE
  .\runkubernetes.ps1 -SkipBuild
.EXAMPLE
  .\runkubernetes.ps1 -UseDockerCache
.EXAMPLE
  .\runkubernetes.ps1 -SkipBuild -SkipHelm -PortForward
#>
param(
    [string]$Namespace = "kpn-genai",
    [string]$ReleaseName = "kpn",
    [switch]$SkipBuild,
    [switch]$SkipHelm,
    [switch]$UseOpenAI,
    # Faster builds; may leave stale layers (broken UI/ API fixes). Default is full rebuild.
    [switch]$UseDockerCache,
    # Opens a new PowerShell window running kubectl port-forward (must stay open while using the UI).
    [switch]$PortForward
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$FullName = "$ReleaseName-kpn-genai"
$BackendDeploy = "$FullName-backend"
$FrontendDeploy = "$FullName-frontend"
$BackendSvc = "$FullName-backend"

Write-Host "Repo: $RepoRoot" -ForegroundColor Cyan

if (-not $SkipBuild) {
    $cacheArgs = @()
    if (-not $UseDockerCache) {
        $cacheArgs = @("--no-cache")
        Write-Host "Docker: backend + frontend with --no-cache (use -UseDockerCache to reuse layers)" -ForegroundColor Yellow
    } else {
        Write-Host "Docker: backend + frontend using layer cache (-UseDockerCache)" -ForegroundColor Yellow
    }
    Write-Host "Building backend image..." -ForegroundColor Cyan
    docker build @cacheArgs -f docker/backend.Dockerfile -t kpn-genai-backend:latest .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "Building frontend image..." -ForegroundColor Cyan
    docker build @cacheArgs -f docker/frontend.Dockerfile -t kpn-genai-frontend:latest .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipHelm) {
    kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f -

    $helmArgs = @(
        "upgrade", "--install",
        $ReleaseName,
        (Join-Path $RepoRoot "helm/kpn-genai"),
        "-n", $Namespace
    )
    if ($UseOpenAI) {
        $helmArgs += @("--set", "backend.llmType=openai", "--set", "backend.azureSecretName=kpn-azure")
        Write-Host "Helm: backend.llmType=openai, azureSecretName=kpn-azure (ensure Secret exists in $Namespace)" -ForegroundColor Yellow
    }

    Write-Host "Helm upgrade..." -ForegroundColor Cyan
    & helm @helmArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    # Same image tag (e.g. :latest) after a local docker build does not change the Deployment spec,
    # so Helm alone may leave old pods running. Restart so new images are used.
    Write-Host "Restarting workloads to pick up rebuilt images..." -ForegroundColor Cyan
    kubectl rollout restart "deployment/$BackendDeploy" -n $Namespace
    kubectl rollout restart "deployment/$FrontendDeploy" -n $Namespace

    Write-Host "Waiting for rollouts..." -ForegroundColor Cyan
    kubectl rollout status "deployment/$BackendDeploy" -n $Namespace --timeout=180s
    kubectl rollout status "deployment/$FrontendDeploy" -n $Namespace --timeout=180s
}

Write-Host ""
Write-Host "Deploy finished." -ForegroundColor Green
Write-Host "  UI (NodePort):  http://127.0.0.1:30080" -ForegroundColor White
Write-Host ""
Write-Host "The frontend calls the API at http://127.0.0.1:8000 - port-forward must stay running while using the UI." -ForegroundColor Yellow
$pf = "kubectl port-forward -n $Namespace svc/$BackendSvc 8000:8000"
Write-Host "  $pf" -ForegroundColor White
if ($PortForward) {
    Write-Host "Opening new window with port-forward (-PortForward)..." -ForegroundColor Cyan
    Start-Process powershell.exe -ArgumentList @(
        "-NoExit",
        "-NoProfile",
        "-Command",
        "Write-Host 'API port-forward (leave this window open). Ctrl+C to stop.' -ForegroundColor Green; $pf"
    )
} else {
    Write-Host "Or run: .\runkubernetes.ps1 -SkipBuild -SkipHelm -PortForward" -ForegroundColor DarkGray
}
Write-Host ""
