; VinylFlow Inno Setup Script
; Builds VinylFlow-Setup-{version}.exe installer for Windows

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

[Code]
// Check if WebView2 Runtime is installed; if not, download and install silently
function IsWebView2Installed: Boolean;
var
  RegValue: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', RegValue)
    or RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', RegValue)
    or RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', RegValue);
end;

procedure InstallWebView2;
var
  ResultCode: Integer;
  BootstrapperPath: String;
begin
  BootstrapperPath := ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe');
  // Download the Evergreen Bootstrapper
  if not DownloadTemporaryFile('https://go.microsoft.com/fwlink/p/?LinkId=2124703', 'MicrosoftEdgeWebview2Setup.exe', '', nil) then
  begin
    MsgBox('Failed to download WebView2 Runtime. Please install it manually from https://developer.microsoft.com/microsoft-edge/webview2/', mbError, MB_OK);
    Exit;
  end;

  // Run silently
  Exec(BootstrapperPath, '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not IsWebView2Installed then
    begin
      Log('WebView2 Runtime not found — installing...');
      InstallWebView2;
    end;
  end;
end;
