param(
    [Parameter(Mandatory = $true)]
    [string]$InstallDir
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$LogPath = Join-Path $env:TEMP "WlasneAI-install.log"
Start-Transcript -Path $LogPath -Append | Out-Null

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw "Ten instalator działa wyłącznie w Windows 10/11."
    }

    Write-Step "Sprawdzanie Windows Package Manager"
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "Nie znaleziono winget. Zainstaluj lub zaktualizuj App Installer ze sklepu Microsoft Store, uruchom ponownie komputer i ponów instalację."
    }

    Write-Step "Instalowanie Python 3.12"
    & winget install --id Python.Python.3.12 --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        & py -3.12 --version *> $null
        if ($LASTEXITCODE -ne 0) { throw "Nie udało się zainstalować Python 3.12 (kod: $LASTEXITCODE)." }
    }
    Refresh-Path
    if (-not (Get-Command py.exe -ErrorAction SilentlyContinue)) {
        throw "Python Launcher nie jest dostępny. Uruchom ponownie komputer i ponów instalację."
    }
    & py -3.12 --version
    if ($LASTEXITCODE -ne 0) { throw "Python 3.12 nie uruchamia się poprawnie." }

    Write-Step "Instalowanie Ollama"
    $ollamaCommand = Get-Command ollama.exe -ErrorAction SilentlyContinue
    if (-not $ollamaCommand) {
        & winget install --id Ollama.Ollama --exact --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) { throw "Nie udało się zainstalować Ollama (kod: $LASTEXITCODE)." }
        Refresh-Path
        $ollamaCommand = Get-Command ollama.exe -ErrorAction SilentlyContinue
    }
    if ($ollamaCommand) {
        $ollamaExe = $ollamaCommand.Source
    } else {
        $possible = @("$env:LOCALAPPDATA\Programs\Ollama\ollama.exe", "$env:ProgramFiles\Ollama\ollama.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
        if ($possible) { $ollamaExe = $possible } else { throw "Nie znaleziono ollama.exe po instalacji. Uruchom ponownie komputer i ponów instalację." }
    }

    Write-Step "Przygotowanie środowiska agenta"
    Set-Location $InstallDir
    & py -3.12 -m venv (Join-Path $InstallDir ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Nie udało się utworzyć środowiska Python." }
    $python = Join-Path $InstallDir ".venv\Scripts\python.exe"
    & $python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "Nie udało się zaktualizować pip." }
    & $python -m pip install -e ".[web]"
    if ($LASTEXITCODE -ne 0) { throw "Nie udało się zainstalować bibliotek agenta." }

    Write-Step "Uruchamianie Ollama"
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 | Out-Null
    } catch {
        Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
        $ready = $false
        for ($i = 0; $i -lt 45; $i++) {
            Start-Sleep -Seconds 2
            try {
                Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 | Out-Null
                $ready = $true
                break
            } catch {}
        }
        if (-not $ready) { throw "Ollama nie uruchomiła serwera." }
    }

    Write-Step "Pobieranie modelu Qwen3 8B (kilka GB)"
    & $ollamaExe pull qwen3:8b
    if ($LASTEXITCODE -ne 0) { throw "Nie udało się pobrać modelu. Ponów później: ollama pull qwen3:8b" }

    Write-Step "Tworzenie skrótu na pulpicie"
    $launcher = Join-Path $InstallDir "launch-agent.ps1"
    if (-not (Test-Path $launcher)) { throw "Brak launch-agent.ps1 w instalacji." }
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktop "Własne AI.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $launcher + '"'
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.Description = "Uruchom lokalnego agenta Własne AI"
    $shortcut.Save()

    Write-Step "Instalacja zakończona"
    Write-Host "Agent został zainstalowany. Skrót: $shortcutPath" -ForegroundColor Green
    & $launcher
}
catch {
    Write-Host ""
    Write-Host "INSTALACJA NIE POWIODŁA SIĘ: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Log instalacji: $LogPath" -ForegroundColor Yellow
    exit 1
}
finally {
    Stop-Transcript | Out-Null
}
