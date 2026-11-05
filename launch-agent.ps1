param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show("Brakuje środowiska aplikacji. Uruchom ponownie instalator Własne AI.", "Własne AI") | Out-Null
    exit 1
}

$ollama = Get-Command ollama.exe -ErrorAction SilentlyContinue
if (-not $ollama) {
    $candidate = @("$env:LOCALAPPDATA\Programs\Ollama\ollama.exe", "$env:ProgramFiles\Ollama\ollama.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($candidate) { $ollamaExe = $candidate } else { throw "Nie znaleziono Ollama. Napraw instalację przez instalator Własne AI." }
} else {
    $ollamaExe = $ollama.Source
}

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
} catch {
    Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    $ollamaReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
            $ollamaReady = $true
            break
        } catch {}
    }
    if (-not $ollamaReady) { throw "Ollama nie odpowiada na porcie 11434." }
}

try {
    Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -TimeoutSec 2 -UseBasicParsing | Out-Null
} catch {
    Start-Process -FilePath $Python -ArgumentList "scripts/run.py" -WorkingDirectory $Root -WindowStyle Hidden
}

$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -TimeoutSec 2 -UseBasicParsing | Out-Null
        $ready = $true
        break
    } catch {}
}
if (-not $ready) { throw "Agent nie uruchomił interfejsu na http://127.0.0.1:8000. Sprawdź logi lub uruchom start.ps1 ręcznie." }

Start-Process "http://127.0.0.1:8000"
