#define MyAppName "Własne AI"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "Shvvit"
#define MyAppExeName "launch-agent.ps1"

[Setup]
AppId={{A2B9F4C1-78C0-4A3D-9C37-8B0B8C45E912}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\WlasneAI
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\launch-agent.ps1
OutputDir=..\dist
OutputBaseFilename=Setup-WlasneAI
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
DisableProgramGroupPage=yes
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
SetupLogging=yes

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Tasks]
Name: "desktopicon"; Description: "Utwórz skrót na pulpicie"; GroupDescription: "Dodatkowe opcje:"; Flags: checkedonce

[Files]
Source: "..\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".git\*,.venv\*,data\*,workspace\*,__pycache__\*,.pytest_cache\*,*.pyc,benchmark-results.json,installer\*,dist\*"
Source: "install-agent.ps1"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\Własne AI"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\{#MyAppExeName}"""; WorkingDir: "{app}"
Name: "{autodesktop}\Własne AI"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\{#MyAppExeName}"""; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{tmp}\install-agent.ps1"" -InstallDir ""{app}"""; Flags: waituntilterminated; StatusMsg: "Instalowanie Pythona, Ollama, bibliotek i modelu Qwen3..."
