# Build et Release — Five Nights At Châtelet

Ce document explique comment générer les exécutables du jeu pour Windows, Linux et macOS.

---

## Comment ça marche

Le projet utilise **GitHub Actions** pour automatiser la création des exécutables. Le fichier de configuration est `.github/workflows/build-release.yml`.

Quand un build est déclenché, GitHub lance 3 machines virtuelles en parallèle (une par OS), installe les dépendances et compile le jeu avec **PyInstaller**. Sur la machine Windows, un installateur **Inno Setup** est en plus compilé à partir de `Installer.iss`. Enfin, un job `release` regroupe tout et crée une Release GitHub avec **4 fichiers** en téléchargement (voir [Ce qui est généré](#ce-qui-est-généré)).

---

## Déclencher un build

### Méthode 1 — Tag Git

```bash
git tag v1.0.0-pre
git push origin v1.0.0-pre
```

### Méthode 2 — Manuellement sur GitHub

1. Aller sur le repo GitHub
2. Cliquer sur l'onglet **Actions**
3. Sélectionner **Build and Release Executables**
4. Cliquer sur **Run workflow**
5. Entrer un numéro de version (ex: `v1.1.0-pre`)
6. Cliquer sur **Run workflow**

> Une version contenant `-pre`, `-beta` ou `-rc` est publiée comme **pre-release**.

---

## Ce qui est généré

| Fichier | OS / Type |
|---|---|
| `FiveNightsAtChatelet-Setup-X.Y.Z.exe` | Windows — installateur (recommandé) |
| `FiveNightsAtChatelet-Windows.exe` | Windows — portable |
| `FiveNightsAtChatelet-Linux` | Linux — portable (`chmod +x` avant de lancer) |
| `FiveNightsAtChatelet-macOS` | macOS — portable |

Les fichiers sont disponibles dans l'onglet **Releases** du repo GitHub.

---

## Installateur Windows (Inno Setup)

L'installateur Windows est décrit par le fichier `Installer.iss` à la racine du repo. Il fournit :

- un assistant d'installation (français / anglais) ;
- le **choix des composants** : jeu principal (obligatoire) et copie locale du site web (optionnelle) ;
- des raccourcis Menu Démarrer / Bureau ;
- une entrée propre dans **Paramètres → Applications** pour la désinstallation.

Dans le workflow, le runner Windows compile l'installateur automatiquement : il installe Inno Setup via `choco install innosetup`, copie l'exécutable PyInstaller dans `build\FiveNightsAtChatelet.exe`, puis lance `ISCC.exe`.

Pour le compiler **en local** :

```
ISCC.exe /DMyAppVersion=1.0.0 Installer.iss
```

Arborescence attendue à la compilation :

```
Installer.iss
LICENSE
README.md
build\FiveNightsAtChatelet.exe   ; produit par PyInstaller
site\                            ; copie locale du site web (composant optionnel)
```

L'installateur final est généré dans `dist\FiveNightsAtChatelet-Setup-X.Y.Z.exe`.

---

## Dépannage

### Le build Windows échoue

Vérifier que les chemins des ressources dans le `.yml` utilisent `;` comme séparateur (syntaxe Windows) :
```
--add-data "ressources;ressources"
```

### Le build Linux/macOS échoue

Vérifier que les chemins utilisent `:` comme séparateur :
```
--add-data "ressources:ressources"
```

### Erreur 403 lors de la création de la release

Aller dans **Settings** → **Actions** → **General** → **Workflow permissions** et activer **Read and write permissions**.

### L'exécutable ne trouve pas les ressources

Vérifier que le dossier `ressources/` est bien à la racine du repo et que le `--add-data` pointe vers le bon chemin.

### L'exécutable se lance puis plante immédiatement

Souvent dû à un module manquant de `panda3d` / `ursina` non embarqué par PyInstaller. Vérifier que la commande de build contient bien `--collect-all panda3d --collect-all ursina --hidden-import panda3d.core` (voir [Prérequis pour builder en local](#prérequis-pour-builder-en-local)).

### L'exécutable ne se lance pas sur Linux/macOS

Ajouter les permissions d'exécution :
```bash
chmod +x FiveNightsAtChatelet-Linux
./FiveNightsAtChatelet-Linux
```

---

## Prérequis pour builder en local

Si tu veux builder sans GitHub Actions, installe d'abord les dépendances et PyInstaller :

```bash
pip install -r requirements.txt
pip install pyinstaller
```

Puis lance la commande correspondant à ton OS (identique à celle du workflow) :

```bash
# Windows (séparateur ";")
pyinstaller --onefile --windowed --add-data "ressources;ressources" \
  --collect-all panda3d --collect-all ursina \
  --hidden-import panda3d.core --exclude-module panda3d.rocket \
  --name "FiveNightsAtChatelet-Windows" Five_Nights_At_Chatelet.py

# Linux (séparateur ":")
pyinstaller --onefile --windowed --add-data "ressources:ressources" \
  --collect-all panda3d --collect-all ursina \
  --hidden-import panda3d.core --exclude-module panda3d.rocket \
  --name "FiveNightsAtChatelet-Linux" Five_Nights_At_Chatelet.py

# macOS (séparateur ":")
pyinstaller --onefile --windowed --add-data "ressources:ressources" \
  --collect-all panda3d --collect-all ursina \
  --hidden-import panda3d.core --exclude-module panda3d.rocket \
  --name "FiveNightsAtChatelet-macOS" Five_Nights_At_Chatelet.py
```

L'exécutable sera dans le dossier `dist/`.
