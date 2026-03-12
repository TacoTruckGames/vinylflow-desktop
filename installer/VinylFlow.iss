; VinylFlow Inno Setup Script
; Builds VinylFlow-Setup-{version}.exe installer for Windows
; PySide6 native UI — no WebView2 dependency

#define MyAppName "VinylFlow"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "VinylFlow"
#define MyAppURL "https://vinylflow.app/"
#define MyAppExeName "VinylFlow.exe"

[Setup]
AppId={{8E3F7A2B-4C5D-6E7F-8A9B-0C1D2E3F4A5B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=VinylFlow-Setup-{#MyAppVersion}
SetupIconFile=..\assets\VinylFlow.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "fileassoc"; Description: "Add ""Digitize with VinylFlow"" to right-click menu for audio files"; GroupDescription: "File Associations:"

[Files]
Source: "..\dist\VinylFlow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; File association context menu: "Digitize with VinylFlow"
Root: HKCU; Subkey: "Software\Classes\.wav\shell\VinylFlow"; ValueType: string; ValueName: ""; ValueData: "Digitize with VinylFlow"; Tasks: fileassoc; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.wav\shell\VinylFlow"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#MyAppExeName}"",0"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\.wav\shell\VinylFlow\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc; Flags: uninsdeletekey

Root: HKCU; Subkey: "Software\Classes\.aiff\shell\VinylFlow"; ValueType: string; ValueName: ""; ValueData: "Digitize with VinylFlow"; Tasks: fileassoc; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.aiff\shell\VinylFlow"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#MyAppExeName}"",0"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\.aiff\shell\VinylFlow\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc; Flags: uninsdeletekey

Root: HKCU; Subkey: "Software\Classes\.aif\shell\VinylFlow"; ValueType: string; ValueName: ""; ValueData: "Digitize with VinylFlow"; Tasks: fileassoc; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.aif\shell\VinylFlow"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#MyAppExeName}"",0"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\.aif\shell\VinylFlow\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc; Flags: uninsdeletekey

Root: HKCU; Subkey: "Software\Classes\.flac\shell\VinylFlow"; ValueType: string; ValueName: ""; ValueData: "Digitize with VinylFlow"; Tasks: fileassoc; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.flac\shell\VinylFlow"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#MyAppExeName}"",0"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\.flac\shell\VinylFlow\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
