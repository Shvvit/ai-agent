$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Brak .venv. Najpierw uruchom: .\install.ps1"
}
& $python scripts\run.py
