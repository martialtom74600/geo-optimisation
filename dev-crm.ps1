# Une seule commande : preparation (venv, pip, npm) + lancement API + interface GEO-CRM.
# Usage (depuis la racine du depot) :  .\dev-crm.ps1
# Ou :  powershell -ExecutionPolicy Bypass -File .\dev-crm.ps1
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

function Resolve-Python {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return (Get-Command python).Source
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $exe = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($exe) { return $exe.Trim() }
    }
    throw "Python introuvable. Installez Python 3.11+ (python.org) et cochez 'Add to PATH'."
}

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creation de l'environnement .venv ..." -ForegroundColor Cyan
    $basePy = Resolve-Python
    & $basePy -m venv (Join-Path $Root ".venv")
    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
}

Write-Host "Installation / mise a jour des paquets Python ..." -ForegroundColor Cyan
& $venvPython -m pip install -U pip -q
& $venvPython -m pip install -e "." -q
& $venvPython -m pip install -e ".\geo_crm\backend" -q

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm introuvable. Installez Node.js 18+ (https://nodejs.org/) puis rouvrez le terminal."
}

$fe = Join-Path $Root "geo_crm\frontend"
Set-Location $fe
Write-Host "npm install (frontend) ..." -ForegroundColor Cyan
npm install

Write-Host ""
Write-Host "Ouvrez l'app :  http://127.0.0.1:8000   (l'API tourne en coulisses sur le port 8001)" -ForegroundColor Green
Write-Host "Arret : Ctrl+C" -ForegroundColor DarkGray
npm run dev:all:win
