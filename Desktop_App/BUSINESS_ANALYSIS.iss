#define MyAppName "BUSINESS ANALYSIS"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Khùlè Khùlè III"
#define MyAppExeName "BUSINESS_ANALYSIS.exe"

[Setup]
AppId={{8B0F5D35-4E25-4A3C-9B7B-BA20260200A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\BUSINESS ANALYSIS
DefaultGroupName=BUSINESS ANALYSIS
OutputDir=installer
OutputBaseFilename=BUSINESS_ANALYSIS_Setup_v2.0.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
Uninstallable=yes

[Files]
Source: "dist\BUSINESS_ANALYSIS.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\BUSINESS ANALYSIS"; Filename: "{app}\BUSINESS_ANALYSIS.exe"
Name: "{autodesktop}\BUSINESS ANALYSIS"; Filename: "{app}\BUSINESS_ANALYSIS.exe"

[Run]
Filename: "{app}\BUSINESS_ANALYSIS.exe"; Description: "Launch BUSINESS ANALYSIS"; Flags: nowait postinstall skipifsilent
