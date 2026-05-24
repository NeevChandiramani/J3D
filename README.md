# Five Nights At Châtelet

> Jeu d'horreur et de survie multijoueur en vue à la troisième personne — Projet SAE J3D EPITA 2025/2026

**BambouX Studio** — Promo 2030

---

## Concept

Five Nights At Châtelet est un jeu d'horreur multijoueur asymétrique inspiré de Five Nights at Freddy's, qui se déroule dans une reconstitution de la station Châtelet. Les joueurs sont répartis en deux équipes aux objectifs opposés :

- **Survivants** : coopèrent pour résoudre une série d'énigmes et s'échapper de la station.
- **Infectés** : traquent les survivants dans les couloirs pour les éliminer avant qu'ils ne s'échappent.

En multijoueur, les rôles sont distribués automatiquement par le serveur (~45 % d'Infectés). Si la connexion réseau échoue, le jeu démarre en mode solo.

---

## Énigmes & tâches

Pour s'échapper, les Survivants doivent résoudre plusieurs mini-jeux disséminés dans la station :

- **NavigoTask** — recharge / validation d'un pass Navigo
- **Énigme électrique** — rétablir le circuit du tableau
- **Énigme de plomberie** — réparer les canalisations
- **Labyrinthe de signalisation** — suivre le bon parcours dans la signalétique

Chaque énigme est implémentée dans son propre fichier Python et déclenchée par interaction (`E`) avec un objet du décor.

---

## Stack technique

- **Moteur 3D** : Ursina Engine (Panda3D)
- **Menu / overlays 2D** : Pygame
- **Langage** : Python 3.11
- **Réseau** : Sockets TCP (broadcast d'état JSON)
- **Modélisation** : Blender (export `.obj` / `.mtl`)
- **Build / CI** : PyInstaller + Inno Setup + GitHub Actions

---

## Installation & Lancement

### Depuis les releases (recommandé)

1. Aller dans l'onglet [Releases](https://github.com/NeevChandiramani/J3D/releases) du repo.
2. Télécharger le fichier correspondant à votre OS :
   - `FiveNightsAtChatelet-Setup-X.Y.Z.exe` — Windows, installateur
   - `FiveNightsAtChatelet-Windows.exe` — Windows, portable
   - `FiveNightsAtChatelet-Linux` — Linux portable (`chmod +x` avant de lancer)
   - `FiveNightsAtChatelet-macOS` — macOS portable
3. Lancer directement, aucune installation Python requise.

### Depuis le code source

```bash
# Cloner le repo
git clone https://github.com/NeevChandiramani/J3D
cd J3D

# Créer un environnement virtuel Python 3.11
python3.11 -m venv venv
source venv/bin/activate    # Linux / macOS
venv\Scripts\activate       # Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer le jeu
python Five_Nights_At_Chatelet.py
```

Les dépendances Python sont minimales : `ursina`, `pygame`, `tomlkit` (voir `requirements.txt`).

---

## Contrôles

| Action | Touche par défaut |
|---|---|
| Avancer | `Z` |
| Reculer | `S` |
| Gauche | `Q` |
| Droite | `D` |
| Sauter | `Espace` |
| Sprint | `Shift gauche` |
| Interagir | `E` |
| Plein écran | `F11` |

Les touches sont reconfigurables depuis le menu principal et stockées dans `config_touches.json`.

---

## Multijoueur

L'architecture est client-serveur TCP :

- Le serveur (`server.py`) tourne en continu sur un VPS dédié et écoute sur le port `5555`.
- Chaque client (`NetworkClient.py`) se connecte automatiquement au démarrage.
- Les positions et états des joueurs sont synchronisés en continu en JSON (≈ 50 ms).
- Le serveur gère le lobby, distribue les rôles, et relaie les évènements de partie (attaques, déclenchement d'énigmes, fin de partie).
- En cas d'échec de connexion, le jeu démarre automatiquement en mode solo.

Pour héberger le serveur soi-même :

```bash
python server.py
```

---

## Structure du projet

```
J3D/
├── Five_Nights_At_Chatelet.py      # Boucle principale du jeu (Ursina)
├── Menu.py                          # Menu principal (Pygame)
├── server.py                        # Serveur TCP multijoueur
├── NetworkClient.py                 # Client réseau TCP
├── Rooms.py                         # Système de salles / téléportation
├── NavigoTask.py                    # Mini-jeu : pass Navigo
├── enigme_electrique.py             # Mini-jeu : tableau électrique
├── enigme_plomberie.py              # Mini-jeu : plomberie
├── EnigmeLabyrintheSignalisation.py # Mini-jeu : labyrinthe de signalisation
├── Installer.iss                    # Script Inno Setup (installateur Windows)
├── icon.ico                         # Icône de l'exécutable
├── requirements.txt                 # Dépendances Python
├── BUILDING.md                      # Doc de build & release
├── config_touches.json              # Mapping de touches sauvegardé
├── ressources/
│   ├── *.obj / *.mtl                # Modèles 3D (station, personnages, props)
│   ├── sounds/                      # Musique, ambiance, pas, screamers audio
│   ├── images/                      # Textures et arrière-plans
│   └── screamers/                   # Jump-scares (images + audio)
├── docs/                            # Manuels d'installation / utilisation
├── site/                            # Site web vitrine du projet
└── .github/workflows/
    └── build-release.yml            # CI/CD : build automatique multi-OS
```

---

## Build

Voir [`BUILDING.md`](BUILDING.md) pour la procédure complète (CI GitHub Actions, Inno Setup, build local avec PyInstaller).

En résumé, un tag Git `vX.Y.Z` ou un lancement manuel du workflow **Build and Release Executables** produit automatiquement les 4 binaires (Windows installeur, Windows portable, Linux, macOS) et publie une Release GitHub.

---

## Site web

Site vitrine du projet, avec rapports de soutenance et ressources :
<https://fivenightsatchatelet.neevchandiramani.com/>

---

## Licence

MIT — © 2026 BambouX Studio
