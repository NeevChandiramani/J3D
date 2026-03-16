# Build et Release — Five Nights At Châtelet

Ce document explique comment générer les exécutables du jeu pour Windows, Linux et macOS.

---

## Comment ça marche

Le projet utilise **GitHub Actions** pour automatiser la création des exécutables. Le fichier de configuration est `.github/workflows/build-release.yml`.

Quand un build est déclenché, GitHub lance 3 machines virtuelles en parallèle (une par OS), installe les dépendances, compile le jeu avec **PyInstaller**, puis crée une Release GitHub avec les 3 fichiers en téléchargement.

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

---

## Ce qui est généré

| Fichier | OS |
|---|---|
| `FiveNightsAtChatelet.exe` | Windows |
| `FiveNightsAtChatelet` | Linux |
| `FiveNightsAtChatelet` | macOS |

Les fichiers sont disponibles dans l'onglet **Releases** du repo GitHub.

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

### L'exécutable ne se lance pas sur Linux/macOS

Ajouter les permissions d'exécution :
```bash
chmod +x FiveNightsAtChatelet
./FiveNightsAtChatelet
```

---

## Prérequis pour builder en local

Si tu veux builder sans GitHub Actions :

```bash
pip install pyinstaller

# Windows
pyinstaller --onefile --windowed --add-data "ressources;ressources" --name "FiveNightsAtChatelet" Five_Nights_At_Chatelet.py

# Linux/macOS
pyinstaller --onefile --windowed --add-data "ressources:ressources" --name "FiveNightsAtChatelet" Five_Nights_At_Chatelet.py
```

L'exécutable sera dans le dossier `dist/`.
