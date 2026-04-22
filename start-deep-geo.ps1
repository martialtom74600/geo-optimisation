# Deep GEO : Docker + API + worker Celery (honcho) dans un seul terminal.
# Usage (racine du depot) :  .\start-deep-geo.ps1
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

Write-Host "Demarrage Docker (postgres + redis)..." -ForegroundColor Cyan
$dockerErr = $null
try {
    $null = & docker compose up -d 2>&1
    if ($LASTEXITCODE -ne 0) { $dockerErr = "code $LASTEXITCODE" }
} catch {
    $dockerErr = $_.Exception.Message
}
if ($dockerErr) {
    Write-Host "Attention Docker: $dockerErr - si Postgres/Redis tournent deja, vous pouvez continuer." -ForegroundColor Yellow
}

$VenvScripts = Join-Path $Root ".venv\Scripts"
$py = Join-Path $VenvScripts "python.exe"
$honcho = Join-Path $VenvScripts "honcho.exe"
if (-not (Test-Path $py)) {
    $msg = 'Venv introuvable : python -m venv .venv puis pip install -e ./deep_geo_backend'
    throw $msg
}
if (-not (Test-Path $honcho)) {
    Write-Host "Installation de honcho dans le venv..." -ForegroundColor Cyan
    & $py -m pip install "honcho>=1.1.0" -q
    $honcho = Join-Path $VenvScripts "honcho.exe"
}

$env:Path = "$VenvScripts;$env:Path"
Set-Location (Join-Path $Root "deep_geo_backend")

Write-Host ""
Write-Host "Lancement : [web] = FastAPI port 8010  |  [worker] = Celery" -ForegroundColor Green
Write-Host "Arret : Ctrl+C pour tout arreter" -ForegroundColor DarkGray
Write-Host "Docs: http://127.0.0.1:8010/docs" -ForegroundColor Cyan
Write-Host ""

# honcho : logs prefixes web / worker
& $honcho start
