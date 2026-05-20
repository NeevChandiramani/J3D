; ============================================================================
;  Five Nights At Châtelet — Installateur Inno Setup
;  BambouX Studio — EPITA Promo 2030 — Projet SAE J3D 2025/2026
; ============================================================================
;
;  Compilation :
;    - GUI  : ouvrir ce fichier avec Inno Setup Compiler puis "Build"
;    - CLI  : ISCC.exe Installer.iss
;
;  Arborescence attendue à la compilation :
;    Installer.iss
;    LICENSE
;    README.md
;    build\FiveNightsAtChatelet.exe        ; produit par PyInstaller
;    site\index.html, site\...             ; copie locale du site web
;    docs\manuel_installation_J3D.pdf          ; manuel d'installation (PDF)
;    docs\manuel_utilisation_J3D.pdf           ; manuel d'utilisation (PDF)
;
;  Sortie :
;    dist\FiveNightsAtChatelet-Setup-1.0.0.exe
; ============================================================================

#define MyAppName       "Five Nights At Châtelet"
#define MyAppVersion    "1.0.0"
#define MyAppPublisher  "BambouX Studio"
#define MyAppURL        "https://fivenightsatchatelet.neevchandiramani.com/"
#define MyAppExeName    "FiveNightsAtChatelet.exe"

[Setup]
; AppId : GUID unique. NE PAS le modifier entre les versions.
AppId={{8F2A7D14-3C9E-4B6A-9F11-5E7C2D8A4F90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
SetupIconFile=icon.ico

; Installation par utilisateur (profil AppData) : aucun droit admin requis,
; et le jeu peut écrire son cache de modèles 3D sans erreur de permission.
DefaultDirName={localappdata}\{#MyAppPublisher}\{#MyAppName}
DefaultGroupName={#MyAppPublisher}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest

; Contrat de licence affiché dans l'assistant
LicenseFile=LICENSE

; Génération de l'installateur final
OutputDir=dist
OutputBaseFilename=FiveNightsAtChatelet-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; Cible 64 bits (Windows 10/11)
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; --- Intégration "Programmes et fonctionnalités" (Add/Remove Programs) ---
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

; Détecter et fermer le jeu s'il est lancé avant d'installer ou désinstaller
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "french";  MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"


;  Composants : éléments optionnels choisis dans l'assistant.

[Components]
Name: "main";    Description: "Jeu principal (obligatoire)"; Types: full compact custom; Flags: fixed
Name: "website"; Description: "Copie locale du site web (consultable hors-ligne)"; Types: full

[Tasks]
Name: "desktopicon";        Description: "Créer une icône du jeu sur le Bureau";            GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "websitedesktopicon"; Description: "Créer un raccourci vers le site web sur le Bureau"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; Components: website

; ============================================================================
;  Fichiers à installer
; ============================================================================
[Files]
; --- Composant principal : exécutable, licence, manuels ---
Source: "build\{#MyAppExeName}";          DestDir: "{app}";      Flags: ignoreversion; Components: main
Source: "LICENSE";                        DestDir: "{app}";      Flags: ignoreversion; Components: main
Source: "README.md";                      DestDir: "{app}";      Flags: ignoreversion; Components: main
Source: "docs\manuel_installation_J3D.pdf";   DestDir: "{app}\docs"; Flags: ignoreversion; Components: main
Source: "docs\manuel_utilisation_J3D.pdf";    DestDir: "{app}\docs"; Flags: ignoreversion; Components: main

; --- Composant optionnel : copie locale du site ---
Source: "site\*"; DestDir: "{app}\site"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: website

;  Raccourcis Menu Démarrer / Bureau

[Icons]
; --- Menu Démarrer ---
Name: "{group}\{#MyAppName}";              Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Manuel d'installation";     Filename: "{app}\docs\manuel_installation_J3D.pdf"
Name: "{group}\Manuel d'utilisation";      Filename: "{app}\docs\manuel_utilisation_J3D.pdf"
Name: "{group}\Site web (local)";          Filename: "{app}\site\index.html"; Components: website
Name: "{group}\Désinstaller {#MyAppName}"; Filename: "{uninstallexe}"

; --- Bureau (optionnel) ---
Name: "{autodesktop}\{#MyAppName}";              Filename: "{app}\{#MyAppExeName}";    Tasks: desktopicon
Name: "{autodesktop}\{#MyAppName} - Site web";   Filename: "{app}\site\index.html";    Tasks: websitedesktopicon; Components: website


;  Actions post-installation (cases à cocher sur l'écran de fin)

[Run]
Filename: "{app}\{#MyAppExeName}";              Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\docs\manuel_utilisation_J3D.pdf";  Description: "Ouvrir le manuel d'utilisation";                           Flags: shellexec nowait postinstall skipifsilent unchecked


;  Nettoyage à la désinstallation (fichiers générés à l'exécution)

[UninstallDelete]
Type: files;          Name: "{app}\config_touches.json"
Type: filesandordirs; Name: "{app}\models_compressed"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\logs"
Type: dirifempty;     Name: "{app}"
Type: dirifempty;     Name: "{localappdata}\{#MyAppPublisher}"


;  Code : détection d'une installation existante au lancement de l'installateur

[Code]
const
  // Cle de registre créée par Inno (AppId + suffixe "_is1").
  UninstRegKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8F2A7D14-3C9E-4B6A-9F11-5E7C2D8A4F90}_is1';

// Récupère la commande de désinstallation enregistrée par une install précédente.
function GetUninstallString(): String;
var
  sUnInstall: String;
begin
  sUnInstall := '';
  // HKCU d'abord (install par utilisateur), HKLM ensuite (ancienne install admin).
  if not RegQueryStringValue(HKCU, UninstRegKey, 'UninstallString', sUnInstall) then
    RegQueryStringValue(HKLM, UninstRegKey, 'UninstallString', sUnInstall);
  Result := sUnInstall;
end;

function IsAlreadyInstalled(): Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

// Exécuté au tout début, avant l'affichage de l'assistant.
function InitializeSetup(): Boolean;
var
  iResponse: Integer;
  iResultCode: Integer;
  sUnInstall: String;
begin
  Result := True;

  if IsAlreadyInstalled() then
  begin
    iResponse := MsgBox(
      'Five Nights At Châtelet est déjà installé sur cet ordinateur.' + #13#10#13#10 +
      'Voulez-vous le désinstaller ?' + #13#10#13#10 +
      'Oui = désinstaller la version actuelle.' + #13#10 +
      'Non = réinstaller par-dessus.' + #13#10 +
      'Annuler = quitter sans rien faire.',
      mbConfirmation, MB_YESNOCANCEL);

    if iResponse = IDYES then
    begin
      // L'utilisateur a confirme : on lance la désinstallation en mode silencieux
      // (pas de double confirmation) puis on ferme l'installateur.
      sUnInstall := RemoveQuotes(GetUninstallString());
      Exec(sUnInstall, '/SILENT /NORESTART', '', SW_SHOW, ewWaitUntilTerminated, iResultCode);
      Result := False;
    end
    else if iResponse = IDCANCEL then
    begin
      // L'utilisateur quitte sans rien faire.
      Result := False;
    end;
    // IDNO : Result reste True -> l'installation continue (réinstallation par-dessus).
  end;
end;
