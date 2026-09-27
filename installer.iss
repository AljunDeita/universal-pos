; installer.iss
; Inno Setup script for Universal POS.
; Compile this with Inno Setup Compiler (after you've run PyInstaller and
; produced the dist\UniversalPOS folder) to generate a distributable
; UniversalPOS_Setup.exe that you can copy to and run on other computers.

#define MyAppName "Universal POS"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Universal POS"
#define MyAppExeName "UniversalPOS.exe"

[Setup]
AppId={{B3F0B6B2-6C6E-4C6B-9B8B-UNIVERSALPOS1}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Installs into Program Files by default and asks for admin rights, which is
; normal for a shared Windows installer. The app itself stores its database
; in the current user's %LOCALAPPDATA% folder (not here), so this is safe.
PrivilegesRequired=admin
OutputDir=installer_output
OutputBaseFilename=UniversalPOS_Setup
SetupIconFile=assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Pulls in EVERYTHING PyInstaller produced (the exe plus its _internal
; support folder) — recursesubdirs makes sure nothing gets left behind.
Source: "dist\UniversalPOS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Only removes the installed program files. The user's sales database and
; receipts (in %LOCALAPPDATA%\UniversalPOS) are intentionally left alone on
; uninstall, so re-installing or updating never touches their sales history.
Type: filesandordirs; Name: "{app}"
