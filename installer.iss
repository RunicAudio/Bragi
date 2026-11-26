; Bragi Windows installer
; Compiled by GitHub Actions after "flet build windows".

#define AppId "{{com.runicaudio.bragi}}"
#define AppName "Bragi"
#define AppExe "Bragi.exe"
#ifndef AppVersion
  #define AppVersion "0.2.0"
#endif

#if !FileExists("build\windows\{#AppExe}")
  #error Bragi.exe was not found in build\windows. Run "flet build windows" first.
#endif

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=RunicAudio
AppComments=Guitar training, fretboard learning, tuning, and ear training.
DefaultDirName={localappdata}\Programs\Bragi
DefaultGroupName=Bragi
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
SetupIconFile=build\flutter\windows\runner\resources\app_icon.ico
UninstallDisplayIcon={app}\{#AppExe}
OutputDir=build\installer
OutputBaseFilename=Bragi-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "build\windows\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Bragi"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\Bragi"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch Bragi"; Flags: nowait postinstall skipifsilent
