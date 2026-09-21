; Inno Setup script -> builds a Windows installer EXE (Setup.exe) for
; NetworkChecker. Run on Windows after PyInstaller has produced
; dist\NetworkChecker.exe and dist\NetworkChecker-CLI.exe:
;
;   iscc packaging\inno\NetworkChecker.iss
;
; Requires Inno Setup 6+: https://jrsoftware.org/isinfo.php
; Output: packaging\inno\Output\NetworkChecker-Setup.exe

#define MyAppName "NetworkChecker"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "NetworkChecker Project"
#define MyAppExeName "NetworkChecker.exe"
#define MyCliExeName "NetworkChecker-CLI.exe"

[Setup]
AppId={{B6E2B7B0-9D9E-4A9E-9A9C-4E1B2C7C9B10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=NetworkChecker-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
Name: "addtopath"; Description: "Add the command-line tool ({#MyCliExeName}) to PATH"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\{#MyCliExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\documents\futureactions.md"; DestDir: "{app}\documents"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

; Optionally add the install directory to the user PATH so
; "NetworkChecker-CLI" is callable from any terminal.
[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
    ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NeedsAddPath(ExpandConstant('{app}'))

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Uppercase(Param) + ';', ';' + Uppercase(OrigPath) + ';') = 0;
end;
