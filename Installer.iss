; ============================================================================
;  Five Nights At Châtelet — Installateur Inno Setup
;  BambouX Studio — EPITA Promo 2030 — Projet SAE J3D 2025/2026
; ============================================================================
;
;  Compilation :
;    - GUI  : ouvrir ce fichier avec Inno Setup Compiler (ISCC) puis "Build"
;    - CLI  : ISCC.exe Installer.iss
;
;  Arborescence attendue à la compilation :
;    Installer.iss
;    LICENSE
;    README.md
;    build\FiveNightsAtChatelet.exe        ; produit par PyInstaller
;    site\index.html, site\...             ; copie locale du site web
;    icon.ico                              ; (optionnel) icône du jeu
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
; AppId : GUID unique. NE PAS le modifier entre les versions, sinon les
; futures mises à jour ne reconnaîtront pas l'installation existante et
; l'entrée dans "Programmes et fonctionnalités" sera dupliquée.
AppId={{8F2A7D14-3C9E-4B6A-9F11-5E7C2D8A4F90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Emplacement par défaut : C:\Program Files\BambouX Studio\Five Nights At Châtelet
DefaultDirName={autopf}\{#MyAppPublisher}\{#MyAppName}
DefaultGroupName={#MyAppPublisher}
DisableProgramGroupPage=yes

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
PrivilegesRequired=admin

; --- Intégration "Programmes et fonctionnalités" (Add/Remove Programs) ---
; Ces champs sont lus par Windows pour afficher l'entrée de désinstallation.
; Inno Setup s'occupe de créer la clé HKLM\...\Uninstall\{AppId}_is1
; automatiquement à partir de ces métadonnées.
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

; Détecter et fermer le jeu s'il est lancé avant d'installer ou désinstaller
CloseApplications=yes
RestartApplications=no

; Icône de l'installateur (commenter si pas de .ico)
;SetupIconFile=icon.ico

[Languages]
Name: "french";  MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

; ============================================================================
;  Composants : ce que l'utilisateur peut cocher/décocher dans l'assistant.
;  Répond à l'exigence SAE-J3D : "le choix des éléments optionnels ou
;  localisés doit être possible directement depuis l'installateur".
; ============================================================================
[Components]
Name: "main";    Description: "Jeu principal (obligatoire)"; Types: full compact custom; Flags: fixed
Name: "website"; Description: "Copie locale du site web (consultable hors-ligne)"; Types: full

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

; ============================================================================
;  Fichiers à installer
; ============================================================================
[Files]
; --- Composant principal : exécutable + ressources légales ---
Source: "build\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "LICENSE";                DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "README.md";              DestDir: "{app}"; Flags: ignoreversion; Components: main

; --- Composant optionnel : copie locale du site ---
Source: "site\*"; DestDir: "{app}\site"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: website

; ============================================================================
;  Raccourcis Menu Démarrer / Bureau
; ============================================================================
[Icons]
Name: "{group}\{#MyAppName}";                Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Site web (local)";            Filename: "{app}\site\index.html"; Components: website
Name: "{group}\Désinstaller {#MyAppName}";   Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";          Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; ============================================================================
;  Action post-installation : proposer de lancer le jeu
; ============================================================================
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; ============================================================================
;  Nettoyage à la désinstallation
;  Inno Setup supprime déjà tout ce qu'il a installé via [Files] ; on ajoute
;  ici les fichiers générés à l'exécution (config touches, caches).
; ============================================================================
[UninstallDelete]
Type: files;          Name: "{app}\config_touches.json"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\logs"
; Supprime le dossier d'installation s'il est vide après nettoyage
Type: dirifempty;     Name: "{app}"
Type: dirifempty;     Name: "{autopf}\{#MyAppPublisher}"
