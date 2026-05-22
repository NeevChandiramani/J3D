# Five Nights At Châtelet

# UPDATE LE README (PLUS À JOUR !!)

> Jeu d'horreur et de survie multijoueur en vue à la troisième personne — Projet SAE J3D EPITA 2025/2026

**BambouX Studio** — Promo 2030

---

## Concept

Five Nights At Châtelet est un jeu d'horreur multijoueur asymétrique inspiré de Five Nights at Freddy's. Les joueurs sont répartis en deux équipes aux objectifs opposés :

- **Explorateurs** : coopèrent pour résoudre une énigme et s'échapper
- **Infectés** : traquent les survivants pour les éliminer

---

## Stack technique

- **Moteur 3D** : Ursina Engine
- **Menu** : Pygame
- **Langage** : Python 3.11
- **Réseau** : Sockets TCP
- **Modélisation** : Blender
- **Build** : PyInstaller + GitHub Actions

---

## Installation & Lancement

### Depuis les releases (recommandé)

1. Aller dans l'onglet [Releases page](https://github.com/NeevChandiramani/J3D/releases) du repo
2. Télécharger l'exécutable correspondant à votre OS
3. Lancer directement — aucune installation requise

### Depuis le code source

```bash
# Cloner le repo
git clone https://github.com/NeevChandiramani/J3D
cd J3D

# Créer un environnement virtuel Python 3.11
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer le jeu
python Five_Nights_At_Chatelet.py
```

---

## Multijoueur

Le multijoueur repose sur une architecture client-serveur TCP :

- Le serveur tourne en continu sur un VPS dédié
- Chaque client se connecte automatiquement au démarrage
- Les positions des joueurs sont synchronisées toutes les 50ms
- En cas d'échec de connexion, le jeu démarre en mode solo

---

## Structure du projet

```
J3D/
├── Five_Nights_At_Chatelet.py   # Fichier principal du jeu
├── Menu.py                       # Menu principal (Pygame)
├── NetworkClient.py              # Client réseau TCP
├── Rooms.py                      # Système de salles
├── requirements.txt              # Dépendances Python
├── ressources/
│   ├── Mall.obj                  # Modèle 3D de la map
│   ├── Crackhead.obj             # Modèle 3D du personnage
│   ├── sounds/
│   │   ├── menu_music.mp3
│   │   └── son_gare.mp3
│   └── images/
│       └── chatelet.jpg
└── .github/
    └── workflows/
        └── build-release.yml     # CI/CD build automatique
```

---

## Site web

https://fivenightsatchatelet.neevchandiramani.com/

---

## Licence

MIT — © 2026 BambouX Studio
