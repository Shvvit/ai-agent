$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Nie znaleziono Python Launcher. Zainstaluj Python 3.12 lub 3.13."
}
py -3.12 -m venv .venv
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Nie udało się utworzyć środowiska .venv."
}
& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -e ".[dev,web]"
& ".venv\Scripts\python.exe" scripts\check_environment.py
Write-Host "Instalacja zakończona. Uruchom: .\start.ps1" -ForegroundColor Green
