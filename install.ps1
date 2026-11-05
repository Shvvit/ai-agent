$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Nie znaleziono Python Launcher. Zainstaluj Python 3.12 lub 3.13."
}
$pythonVersion = $null
foreach ($candidate in @("3.12", "3.13")) {
    & py "-$candidate" --version *> $null
    if ($LASTEXITCODE -eq 0) {
        $pythonVersion = $candidate
        break
    }
}
if (-not $pythonVersion) {
    throw "Wymagany Python 3.12 lub 3.13. Zainstaluj jedną z tych wersji."
}
Write-Host "Używam Python $pythonVersion"
& py "-$pythonVersion" -m venv .venv
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Nie udało się utworzyć środowiska .venv."
}
& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -e ".[dev,web]"
& ".venv\Scripts\python.exe" scripts\check_environment.py
Write-Host "Instalacja zakończona. Uruchom: .\start.ps1" -ForegroundColor Green
