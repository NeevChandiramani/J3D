#lignes à commenter pour désactiver le menu = -

#import cv2
import threading
import math
import os
from pathlib import Path
import json
import sys
from ursina import *
import pygame
import random
from ursina.shaders import lit_with_shadows_shader
from Rooms import Rooms
from NetworkClient import NetworkClient
#pip install ursina on oublie pas tu connais

# ──────────────────────────────────────────────
# CHEMINS RESSOURCES (compatibilité PyInstaller)
# ──────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def res(path):
    return os.path.normpath(os.path.join(BASE_DIR, path))

# touches par défaut
touches = {
    'Move Forward': 'z',
    'Move Backward': 's',
    'Move Left': 'q',
    'Move Right': 'd',
    'Interact': 'e',
    'Jump': 'space',
    'Sprint': 'left shift'
}

try:                                                                            #-
    from Menu import run_menu                                                   #-
except Exception as e:                                                          #-
    run_menu = None                                                             #-
    print("Warning: impossible d'importer `Menu.run_menu()`: ", e)              #-

if run_menu:                                                                    #-
    result = run_menu()                                                         #-
    if result != 'start':                                                       #-
        sys.exit()                                                              #-

# charger les touches modifiées depuis le menu
if os.path.exists("config_touches.json"):
    try:
        with open("config_touches.json", "r") as f:
            touches.update(json.load(f))
    except Exception as e:
        print("Erreur lors du chargement des touches:", e)

Five_nights_at_chatelet = Ursina()

# On change le répertoire de travail vers BASE_DIR
# pour que Ursina trouve les assets avec des chemins relatifs
os.chdir(BASE_DIR)
application.asset_folder = Path(BASE_DIR)

try:                                                                            #-
    pygame.quit()                                                               #-
except Exception:                                                               #-
    pass                                                                        #-

# ──────────────────────────────────────────────
# RÉSEAU
# ──────────────────────────────────────────────
network = NetworkClient()
network.connect()

ghost_entities = {}   # {player_id: Entity}
ghost_hp = {}         # {player_id: int}

SEND_INTERVAL = 0.05
_send_timer = 0

# ──────────────────────────────────────────────
# RÔLES ET ATTRIBUTION
# ──────────────────────────────────────────────
# Définition des rôles disponibles
ROLES = {
    "Survivor": {
        "description": "Find the exits. Avoid the Infected.",
        "color_rgb": (80, 220, 100),
        "model_color": color.white,
        "model_path": 'ressources/Perso.obj',
        "speed_mult": 1.0,
        "max_hp": 100,
        "can_attack": False,
    },
    "Infected": {
        "description": "Eliminate all Survivors.",
        "color_rgb": (220, 50, 50),
        "model_color": color.red,
        "model_path": 'ressources/Crackhead.obj',
        "speed_mult": 1.15,
        "max_hp": 150,
        "can_attack": True,
    },
}

player_role = None
all_assigned_roles = {} # Stocke les rôles de tous les joueurs pour l'affichage correct des modèles
_role_announced = False
_role_announce_timer = 0.0
ROLE_ANNOUNCE_DURATION = 4.0
_announce_phase = 0
_announce_fade  = 0.0
FADE_SPEED      = 2.2

def assign_role():
    """Attribution aléatoire et équilibrée des rôles au lancement."""
    global player_role, MAX_HP, base_speed, _role_announced, _role_announce_timer, all_assigned_roles

    players = network.get_other_players() if network.connected else {}
    nb_players = len(players) + 1

    if nb_players <= 1:
        # En solo : tirage aléatoire
        player_role = random.choices(["Survivor", "Infected"], weights=[70, 30])[0]
        if network.my_id is not None:
            all_assigned_roles[str(network.my_id)] = player_role
    else:
        # En multijoueur : S'assurer qu'il y a au moins 1 Infecté et au moins 1 Survivant
        nb_infectes = max(1, min(nb_players - 1, round(nb_players * 0.35)))
        
        all_ids = sorted([str(pid) for pid in players.keys()])
        if network.my_id is not None:
            all_ids.append(str(network.my_id))
            all_ids.sort()
            
        random.seed(sum(ord(c) for c in "".join(all_ids)))
        infectes_ids = random.sample(all_ids, nb_infectes)
        random.seed()  # Réinitialise la seed pour la suite du jeu
        
        # Enregistrer les rôles de tous les joueurs présents
        for pid in all_ids:
            all_assigned_roles[pid] = "Infected" if pid in infectes_ids else "Survivor"
            
        my_str = str(network.my_id) if network.my_id is not None else all_ids[0]
        player_role = all_assigned_roles.get(my_str, "Survivor")

    # Appliquer les statistiques et le modèle 3D selon le rôle
    role_data = ROLES[player_role]
    MAX_HP = role_data["max_hp"]
    base_speed = 6.7 * role_data["speed_mult"]
    joueur_model.color = role_data["model_color"]
    joueur_model.model = role_data["model_path"] 

    _role_announced = True
    _role_announce_timer = ROLE_ANNOUNCE_DURATION
    show_role_announce()
    print(f"[ROLE] Role attribué : {player_role}")


def show_role_announce():
    global _announce_phase, _announce_fade
    role_data = ROLES[player_role]
    r, g_c, b = role_data["color_rgb"]
    role_announce_name.text  = player_role.upper()
    role_announce_name.color = color.rgba(r, g_c, b, 0)
    role_announce_title.color = color.rgba(180, 180, 180, 0)
    role_announce_desc.text  = role_data["description"]
    role_announce_desc.color = color.rgba(200, 200, 200, 0)
    role_announce_sub.color  = color.rgba(120, 120, 120, 0)
    role_announce_bg.color   = color.rgba(0, 0, 0, 0)
    role_announce_root.enabled = True
    _announce_phase = 0
    _announce_fade  = 0.0


def update_role_announce():
    """Gère l'animation d'apparition/disparition de l'annonce du rôle"""
    global _announce_phase, _announce_fade, _role_announce_timer, _role_announced
    if not _role_announced:
        return
    role_data = ROLES[player_role]
    r, g_c, b = role_data["color_rgb"]
    dt = time.dt

    if _announce_phase == 0:
        _announce_fade = min(1.0, _announce_fade + dt * FADE_SPEED)
        a_bg   = int(_announce_fade * 210)
        a_text = int(_announce_fade * 255)
        role_announce_bg.color    = color.rgba(0, 0, 0, a_bg)
        role_announce_title.color = color.rgba(180, 180, 180, a_text)
        role_announce_name.color  = color.rgba(r, g_c, b, a_text)
        role_announce_desc.color  = color.rgba(200, 200, 200, int(a_text * 0.8))
        role_announce_sub.color   = color.rgba(120, 120, 120, int(a_text * 0.7))
        if _announce_fade >= 1.0:
            _announce_phase = 1

    elif _announce_phase == 1:
        _role_announce_timer -= dt
        if _role_announce_timer <= 0:
            _announce_phase = 2
            _announce_fade  = 1.0

    elif _announce_phase == 2:
        _announce_fade = max(0.0, _announce_fade - dt * FADE_SPEED)
        a_bg   = int(_announce_fade * 210)
        a_text = int(_announce_fade * 255)
        role_announce_bg.color    = color.rgba(0, 0, 0, a_bg)
        role_announce_title.color = color.rgba(180, 180, 180, a_text)
        role_announce_name.color  = color.rgba(r, g_c, b, a_text)
        role_announce_desc.color  = color.rgba(200, 200, 200, int(a_text * 0.8))
        role_announce_sub.color   = color.rgba(120, 120, 120, int(a_text * 0.7))
        if _announce_fade <= 0.0:
            role_announce_root.enabled = False
            _role_announced = False


def update_role_indicator():
    """Met à jour le petit texte affichant le rôle en haut à droite"""
    if player_role:
        role_data = ROLES[player_role]
        r, g_c, b = role_data["color_rgb"]
        role_indicator.text  = f"[ {player_role.upper()} ]"
        role_indicator.color = color.rgba(r, g_c, b, 200)


def update_ghosts(other_players):
    for pid in list(ghost_entities.keys()):
        if pid not in other_players:
            destroy(ghost_entities.pop(pid))
            ghost_hp.pop(pid, None)

    for pid, data in other_players.items():
        if not isinstance(data, dict) or "x" not in data or "y" not in data or "z" not in data:
            continue

        if pid not in ghost_entities:
            # Récupération du rôle du joueur distant pour lui assigner le bon modèle
            ghost_role = all_assigned_roles.get(str(pid), "Survivor")
            ghost_model = ROLES[ghost_role]["model_path"]
            ghost_color = ROLES[ghost_role]["model_color"]

            ghost_entities[pid] = Entity(
                model=ghost_model,
                color=ghost_color,
                scale_y=3,
                collider='box'
            )
            ghost_hp[pid] = ROLES[ghost_role]["max_hp"]

        ghost_entities[pid].position = Vec3(data["x"], data["y"], data["z"])
        if "ry" in data:
            ghost_entities[pid].rotation_y = data["ry"]

    if hasattr(network, 'get_damage_events'):
        for event in network.get_damage_events():
            if event.get("type") == "screamer":
                play_screamer(event.get("screamer"))
                continue
            print(f"[NET] Event dégât reçu : {event}")
            if network.my_id is not None and str(event.get("target_id")) == str(network.my_id):
                print(f"[NET] Je suis la cible ! Appel receive_damage({event.get('amount', 10)})")
                receive_damage(event.get("amount", 10))

            target_pid = str(event.get("target_id"))
            if target_pid in ghost_entities:
                g = ghost_entities[target_pid]
                ghost_role = all_assigned_roles.get(target_pid, "Survivor")
                orig_color = ROLES[ghost_role]["model_color"]
                
                g.color = color.white
                # Le fantôme redevient de sa couleur d'origine après le coup
                invoke(setattr, g, 'color', orig_color, delay=0.15)


sol = Entity(
    model="ressources/Mall.obj",
    collider="mesh",
    shader=lit_with_shadows_shader,
    scale=Vec3(0.5, 1.5, 0.5)
)

joueur = Entity(
    position=(15, 3, 0),
    collider='box',
    scale_y=3
)

# Ambiance globale plus froide et plus sombre
AmbientLight(color=Vec4(0.035, 0.04, 0.05, 1))

# Lumières du métro (moins marron, plus gris/bleu)
metro_lights = [
    (Vec3(15, 8, 0),    Vec4(0.20, 0.22, 0.24, 1), 12),
    (Vec3(-10, 8, 10),  Vec4(0.16, 0.22, 0.18, 1), 13),
    (Vec3(-30, 8, -8),  Vec4(0.22, 0.12, 0.12, 1), 13),
    (Vec3(0, 8, -20),   Vec4(0.18, 0.20, 0.24, 1), 13),
    (Vec3(30, 8, 15),   Vec4(0.22, 0.22, 0.18, 1), 12),
    (Vec3(-45, 35, 0),  Vec4(0.15, 0.06, 0.06, 1), 16),
    (Vec3(0, 35, 0),    Vec4(0.14, 0.18, 0.22, 1), 16),
]

for _pos, _col, _rad in metro_lights:
    _pl = PointLight(position=_pos)
    _pl.color = _col
    _pl.radius = _rad

# Halo personnel du joueur — comme un téléphone allumé
halo_joueur = PointLight(parent=joueur, position=(0, 2, 0))
halo_joueur.color = Vec4(0.6, 0.55, 0.4, 1)
halo_joueur.radius = 10


joueur_model = Entity(
    parent=joueur,
    model='ressources/Perso.obj', # Modèle par défaut, sera mis à jour par assign_role()
    rotation_y=180,
    position=(-0.5, 0, 0)
)

rambarde_1 = Entity(
    model='cube',
    collider='box',
    visible=False,
    position=(-25.49, 23.38, 2.42),
    scale=(23.57, 40.81, 0.2)
)

rambarde_2 = Entity(
    model='cube',
    collider='box',
    visible=False,
    position=(-25.49, 23.38, -2.36),
    scale=(23.57, 40.81, 0.2)
)
rambarde_3 = Entity(
    model='cube',
    collider='box',
    visible=False,
    position=(37.59, 67.61, -3.91),
    scale=(0.2, 63.25, 31.31)
)

rambarde_4 = Entity(
    model='cube',
    collider='box',
    visible=False,
    position=(42.23, 67.61, -3.91),
    scale=(0.2, 63.25, 31.31)
)

# ── Rambardes cylindre (24 segments) ──
rambardes_cylindre = [
    Entity(model='cube', collider='box', visible=False, position=(-36.53, 73.11, -5.68), scale=(0.3, 73.77, 4.72), rotation_y=169.14),
    Entity(model='cube', collider='box', visible=False, position=(-34.21, 73.11, -11.88), scale=(0.3, 73.78, 8.62), rotation_y=154.15),
    Entity(model='cube', collider='box', visible=False, position=(-29.4, 73.11, -18.84), scale=(0.3, 73.78, 8.5), rotation_y=136.43),
    Entity(model='cube', collider='box', visible=False, position=(-22.67, 73.11, -24.4), scale=(0.3, 73.78, 9.07), rotation_y=123.16),
    Entity(model='cube', collider='box', visible=False, position=(-14.39, 73.11, -28.38), scale=(0.3, 73.78, 9.47), rotation_y=108.53),
    Entity(model='cube', collider='box', visible=False, position=(-4.97, 73.12, -30.42), scale=(0.3, 73.76, 9.92), rotation_y=96.14),
    Entity(model='cube', collider='box', visible=False, position=(4.93, 73.11, -30.44), scale=(0.3, 73.77, 9.99), rotation_y=84.08),
    Entity(model='cube', collider='box', visible=False, position=(14.36, 73.11, -28.39), scale=(0.3, 73.77, 9.43), rotation_y=71.07),
    Entity(model='cube', collider='box', visible=False, position=(22.62, 73.11, -24.39), scale=(0.3, 73.77, 9.07), rotation_y=57.01),
    Entity(model='cube', collider='box', visible=False, position=(29.3, 73.11, -18.8), scale=(0.3, 73.77, 8.49), rotation_y=42.56),
    Entity(model='cube', collider='box', visible=False, position=(34.01, 73.11, -11.96), scale=(0.3, 73.77, 8.29), rotation_y=26.29),
    Entity(model='cube', collider='box', visible=False, position=(36.34, 72.62, -4.18), scale=(0.3, 74.75, 8.18), rotation_y=6.95),
    Entity(model='cube', collider='box', visible=False, position=(36.34, 72.62, 4.15), scale=(0.3, 74.75, 8.59), rotation_y=-6.62),
    Entity(model='cube', collider='box', visible=False, position=(34.07, 73.11, 12.03), scale=(0.3, 73.77, 8.05), rotation_y=-26.09),
    Entity(model='cube', collider='box', visible=False, position=(29.36, 73.11, 18.83), scale=(0.3, 73.77, 8.67), rotation_y=-42.71),
    Entity(model='cube', collider='box', visible=False, position=(22.61, 73.11, 24.39), scale=(0.3, 73.77, 8.98), rotation_y=-58.06),
    Entity(model='cube', collider='box', visible=False, position=(14.35, 73.12, 28.3), scale=(0.3, 73.76, 9.43), rotation_y=-70.93),
    Entity(model='cube', collider='box', visible=False, position=(4.93, 73.11, 30.49), scale=(0.3, 73.78, 10.02), rotation_y=-82.48),
    Entity(model='cube', collider='box', visible=False, position=(-4.98, 72.99, 30.64), scale=(0.3, 74.02, 9.93), rotation_y=-95.89),
    Entity(model='cube', collider='box', visible=False, position=(-14.42, 72.99, 28.52), scale=(0.3, 74.02, 9.56), rotation_y=-109.74),
    Entity(model='cube', collider='box', visible=False, position=(-22.67, 73.11, 24.48), scale=(0.3, 73.78, 8.93), rotation_y=-122.89),
    Entity(model='cube', collider='box', visible=False, position=(-29.35, 72.99, 18.96), scale=(0.3, 74.02, 8.5), rotation_y=-136.52),
    Entity(model='cube', collider='box', visible=False, position=(-34.17, 72.99, 12.08), scale=(0.3, 74.02, 8.5), rotation_y=-153.43),
    Entity(model='cube', collider='box', visible=False, position=(-36.55, 73.11, 5.86), scale=(0.3, 73.78, 4.94), rotation_y=-168.67),
]

test_cube = Entity(
    model='cube',
    color=color.azure,
    position=(2, 1, 2),
    shader=lit_with_shadows_shader
)

cube_proche = Entity(
    model='cube',
    color=color.orange,
    position=(10, 5, 3),
    scale=(1, 1, 1),
    collider='box',
    shader=lit_with_shadows_shader
)

# ──────────────────────────────────────────────
# CUBE SCREAMER
# ──────────────────────────────────────────────
screamer_list = [
    ('ressources/screamers/Snapshot_2.png', 'ressources/screamers/Snapshot2.ogg'),
    ('ressources/screamers/Snapshot_3.png', 'ressources/screamers/Snapshot3.ogg'),
    ('ressources/screamers/Snapshot_4.png', 'ressources/screamers/Snapshot4.ogg'),
    ('ressources/screamers/Snapshot_5.png', 'ressources/screamers/Snapshot5.ogg'),
]

cube_screamer = Entity(
    model='cube',
    color=color.red,
    position=(-53.015377, 36.245815, 0.37925073),
    scale=(1, 1, 1),
    collider='box',
    shader=lit_with_shadows_shader
)

_screamer_timer = 0.0

#Interface de mort
ecran_mort = Entity(parent=camera.ui, enabled=False)

fond_mort = Entity(
    parent=ecran_mort,
    model='quad',
    color=color.rgba(0, 0, 0, 0.75),
    scale=(2, 1),
    z=0.1
)

texte_mort = Text(
    parent=ecran_mort,
    text='YOU DIED!',
    origin=(0, 0),
    position=(0, 0.15),
    scale=4,
    color=color.rgb(180, 0, 0),
    font='VeraMono.ttf'
)

ligne_mort = Entity(
    parent=ecran_mort,
    model='quad',
    color=color.rgba(180, 0, 0, 0.8),
    scale=(0.5, 0.003),
    position=(0, 0.07)
)

def bouton_respawn():
    respawn_player()

def bouton_menu():
    network.disconnect()
    import subprocess, sys, os
    subprocess.Popen([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "Five_Nights_At_Chatelet.py")])
    application.quit()

btn_respawn = Button(
    parent=ecran_mort,
    text='RESPAWN',
    text_color= color.black,
    position=(0, -0.05),
    scale=(0.28, 0.07),
    color=color.rgba(140, 0, 0, 0.9),
    highlight_color=color.rgba(200, 30, 30, 1),
    pressed_color=color.rgba(80, 0, 0, 1),
    on_click=bouton_respawn
)
btn_respawn.text_entity.scale *= 0.9



btn_menu = Button(
    parent=ecran_mort,
    text='TITLE SCREEN',
    text_color= color.black,
    position=(0, -0.16),
    scale=(0.28, 0.07),
    color=color.rgba(30, 30, 30, 0.9),
    highlight_color=color.rgba(70, 70, 70, 1),
    pressed_color=color.rgba(10, 10, 10, 1),
    on_click=bouton_menu

)
btn_menu.text_entity.scale *= 0.9


# ──────────────────────────────────────────────
# HP
# ──────────────────────────────────────────────
MAX_HP = 100
player_hp = MAX_HP
INVINCIBILITY_DURATION = 0.5
_invincibility_timer = 0.0
is_dead = False
_death_timer = 0.0
RESPAWN_DELAY = 3.0

def receive_damage(amount):
    global player_hp, _invincibility_timer, is_dead
    print(f"[DAMAGE] receive_damage appelé : amount={amount}, hp={player_hp}, invincible={_invincibility_timer:.2f}, dead={is_dead}")
    if _invincibility_timer > 0 or is_dead:
        print("[DAMAGE] Ignoré (invincible ou mort)")
        return
    player_hp -= amount
    player_hp = max(0, player_hp)
    _invincibility_timer = INVINCIBILITY_DURATION
    update_hp_ui()

    damage_flash.enabled = True
    invoke(setattr, damage_flash, 'enabled', False, delay=0.15)

    print(f"[DAMAGE] HP restant : {player_hp}")
    if player_hp <= 0:
        print("[DAMAGE] → player_death()")
        player_death()

def player_death():
    global is_dead, _death_timer
    is_dead = True
    _death_timer = RESPAWN_DELAY
    hp_text.text = 'HP: 0  —  MORT'
    hp_text.color = color.red

    ecran_mort.enabled = True
    mouse.locked = False
    mouse.visible = True

def respawn_player():
    global is_dead, player_hp, _invincibility_timer
    is_dead = False
    player_hp = MAX_HP
    _invincibility_timer = 1.0
    joueur.position = (15, 3, 0)
    hp_text.color = color.lime
    update_hp_ui()

    ecran_mort.enabled = False
    mouse.locked = True
    mouse.visible = False

def update_hp_ui():
    ratio = player_hp / MAX_HP
    hp_text.text = f'HP: {player_hp}'
    if ratio > 0.5:
        hp_text.color = color.lime
    elif ratio > 0.25:
        hp_text.color = color.orange
    else:
        hp_text.color = color.red

# ──────────────────────────────────────────────
# ATTAQUE
# ──────────────────────────────────────────────
ATTACK_DAMAGE   = 10
ATTACK_RANGE    = 3.0
ATTACK_WIDTH    = 2.0
ATTACK_HEIGHT   = 3.0
ATTACK_COOLDOWN = 0.6
_attack_timer   = 0.0

def do_attack():
    global _attack_timer
    if _attack_timer > 0 or is_dead:
        return
    _attack_timer = ATTACK_COOLDOWN

    forward = Vec3(joueur.forward.x, 0, joueur.forward.z).normalized()
    right   = Vec3(joueur.right.x,   0, joueur.right.z  ).normalized()

    center = joueur.position + Vec3(0, 1, 0) + forward * (ATTACK_RANGE * 0.5)
    hitbox_vis = Entity(
        model='cube',
        color=color.rgba(1, 0.1, 0.1, 0.35),
        position=center,
        rotation=joueur.rotation,
        scale=(ATTACK_WIDTH, ATTACK_HEIGHT, ATTACK_RANGE),
    )
    destroy(hitbox_vis, delay=0.12)

    for pid, ghost in list(ghost_entities.items()):
        delta  = ghost.position - joueur.position
        f_dist = delta.dot(forward)
        s_dist = abs(delta.dot(right))
        h_dist = abs((ghost.position.y + 1.5) - (joueur.position.y + 1.5))

        if (0 < f_dist <= ATTACK_RANGE) and (s_dist <= ATTACK_WIDTH * 0.5) and (h_dist <= ATTACK_HEIGHT * 0.5):
            ghost_hp[pid] = max(0, ghost_hp.get(pid, MAX_HP) - ATTACK_DAMAGE)
            print(f"[ATTACK] HIT sur {pid} ! HP restant : {ghost_hp[pid]}")

            if ghost_hp[pid] <= 0:
                print(f"[ATTACK] Ghost {pid} est mort !")
                destroy(ghost_entities.pop(pid))
                ghost_hp.pop(pid, None)
            else:
                ghost_role = all_assigned_roles.get(str(pid), "Survivor")
                orig_color = ROLES[ghost_role]["model_color"]
                ghost.color = color.white
                # Le fantôme redevient de sa couleur d'origine après avoir pris le coup
                invoke(setattr, ghost, 'color', orig_color, delay=0.15)

            if network.connected:
                network.send_damage(pid, ATTACK_DAMAGE)


# ──────────────────────────────────────────────
# STAMINA
# ──────────────────────────────────────────────
max_stamina = 100
current_stamina = max_stamina
stamina_drain_rate = 25
stamina_regen_rate = 15
sprint_speed_multiplier = 2.0
base_speed = 6.7

# Son ambiance gare — chemin absolu car Audio ne suit pas os.chdir
son_gare = Audio('ressources/sounds/son_gare.ogg', autoplay=False)
_son_timer = random.uniform(120, 240)

# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────
distance_interaction = 3
rectangle_visible = False

rectangle_ui = Entity(
    model='quad',
    color=color.red,
    scale=(0.3, 0.2),
    position=(0, 0),
    parent=camera.ui,
    enabled=False
)

stamina_text = Text(
    text='Stamina: 100',
    position=(-0.8, -0.45),
    scale=1.5,
    parent=camera.ui,
    color=color.white
)

hp_text = Text(
    text='HP: 100',
    position=(-0.8, -0.35),
    scale=1.5,
    parent=camera.ui,
    color=color.lime
)

# Flash rouge reçu lors d'un coup
damage_flash = Entity(
    model='quad',
    color=color.rgba(1, 0, 0, 0.35),
    scale=(2, 1),
    position=(0, 0),
    parent=camera.ui,
    enabled=False
)

# Indicateur d'attaque (cooldown visuel, coin bas-droite)
attack_indicator = Text(
    text='[CLICK] Attack',
    position=(0.55, -0.45),
    scale=1.3,
    parent=camera.ui,
    color=color.white
)

network_text = Text(
    text='Réseau: connexion...',
    position=(-0.8, 0.45),
    scale=1.2,
    parent=camera.ui,
    color=color.yellow
)

#salle_ui = Text(
#    text="",
#    position=(-0.85,0.45),
#    scale=2,
#    parent=camera.ui
#)

# ──────────────────────────────────────────────
# UI — ANNONCE DU RÔLE
# ──────────────────────────────────────────────
role_announce_root = Entity(parent=camera.ui, enabled=False, z=-0.5)

role_announce_bg = Entity(
    parent=role_announce_root,
    model='quad',
    color=color.rgba(0, 0, 0, 0),
    scale=(3, 2),
    z=0.1
)

role_announce_title = Text(
    parent=role_announce_root,
    text='YOUR ROLE',
    origin=(0, 0),
    position=(0, 0.18),
    scale=2.5,
    color=color.rgba(180, 180, 180, 0),
    font='VeraMono.ttf'
)

role_announce_name = Text(
    parent=role_announce_root,
    text='',
    origin=(0, 0),
    position=(0, 0.04),
    scale=6,
    color=color.white,
    font='VeraMono.ttf'
)

role_announce_desc = Text(
    parent=role_announce_root,
    text='',
    origin=(0, 0),
    position=(0, -0.10),
    scale=1.8,
    color=color.rgba(200, 200, 200, 0),
    font='VeraMono.ttf'
)

role_announce_sub = Text(
    parent=role_announce_root,
    text='Good luck...',
    origin=(0, 0),
    position=(0, -0.22),
    scale=1.4,
    color=color.rgba(120, 120, 120, 0),
    font='VeraMono.ttf'
)

# Indicateur de rôle permanent (coin haut droit)
role_indicator = Text(
    text='',
    position=(0.62, 0.44),
    scale=1.2,
    parent=camera.ui,
    color=color.white
)

# ──────────────────────────────────────────────
# CAMÉRA & JOUEUR
# ──────────────────────────────────────────────
mouse.locked = True
mouse.visible = False

camera_pivot = Entity(parent=joueur, y=2)
camera.parent = camera_pivot
camera.fov = 90
camera.rotation = (15, 0, 0)

# W.I.P C'est pas très fluide pour la rotation du perso
def mouvement_camera():
    if is_dead:
        return
    joueur.rotation_y      += mouse.velocity[0] * 80
    camera_pivot.rotation_x -= mouse.velocity[1] * 80
    camera_pivot.rotation_x  = clamp(camera_pivot.rotation_x, -30, 45)
    camera_pivot.rotation_y  = 0
    camera.position = (0, 0, -5)

is_jumping = False
vertical_velocity = 0
gravity = -40
jump_force = 20
on_ground = True


def saut():
    global is_jumping, vertical_velocity, on_ground

    # Toujours appliquer la gravité
    vertical_velocity += gravity * time.dt
    joueur.y += vertical_velocity * time.dt

    # Raycast vers le bas depuis le centre du joueur
    col_info = raycast(
        joueur.position + Vec3(0, 0.1, 0),  # légèrement au-dessus des pieds
        Vec3(0, -1, 0),
        distance=1.5,
        ignore=[joueur]
    )

    if col_info and col_info.hit:
        ground_y = col_info.world_point.y

        # Si le joueur est proche du sol ou en dessous
        if joueur.y <= ground_y + 0.6:
            joueur.y = ground_y + 0.5  # snap précis au sol
            vertical_velocity = 0
            is_jumping = False
            on_ground = True
        else:
            on_ground = False
    else:
        on_ground = False

    # Sécurité : si le joueur tombe hors de la map
    if joueur.y < -50:
        joueur.position = (15, 3, 0)
        vertical_velocity = 0
        on_ground = True
        is_jumping = False


def mouvement_joueur():
    global current_stamina
    if is_dead:
        return

    is_moving = held_keys[touches['Move Forward']] or held_keys[touches['Move Backward']] or held_keys[touches['Move Left']] or held_keys[touches['Move Right']]
    is_sprinting = held_keys[touches['Sprint']] and current_stamina > 1 and is_moving

    if is_sprinting:
        current_stamina -= stamina_drain_rate * time.dt
        current_stamina = max(0, current_stamina)
        current_speed = base_speed * sprint_speed_multiplier if current_stamina > 0 else base_speed
    else:
        current_speed = base_speed
        if current_stamina < max_stamina:
            current_stamina += stamina_regen_rate * time.dt
            current_stamina = min(max_stamina, current_stamina)

    stamina_text.text = f'Stamina: {int(current_stamina)}'

    avance = Vec3(camera_pivot.forward.x, 0, camera_pivot.forward.z) * held_keys[touches['Move Forward']]
    recule = Vec3(camera_pivot.forward.x, 0, camera_pivot.forward.z) * -held_keys[touches['Move Backward']]
    droite = Vec3(camera_pivot.right.x,   0, camera_pivot.right.z  ) * held_keys[touches['Move Right']]
    gauche = Vec3(camera_pivot.right.x,   0, camera_pivot.right.z  ) * -held_keys[touches['Move Left']]
    move_vec = avance + recule + droite + gauche

    if move_vec.length_squared() > 0:
        direction = move_vec.normalized()
        move = direction * time.dt * current_speed
        right = Vec3(direction.z, 0, -direction.x)  # vecteur perpendiculaire

        # ── 6 raycasts : centre + gauche + droite, à 2 hauteurs ──
        origins = [
            joueur.position + Vec3(0, 0.3, 0),
            joueur.position + Vec3(0, 1.0, 0),
            joueur.position + Vec3(0, 0.3, 0) + right * 0.4,
            joueur.position + Vec3(0, 1.0, 0) + right * 0.4,
            joueur.position + Vec3(0, 0.3, 0) - right * 0.4,
            joueur.position + Vec3(0, 1.0, 0) - right * 0.4,
        ]

        bloque = False
        for origin in origins:
            col = raycast(origin, direction, distance=1.0, ignore=[joueur, sol])
            if col and col.hit:
                normal = col.world_normal
                if normal.y < 0.7:  # c'est un mur, pas une rampe
                    bloque = True
                    break

        if not bloque:
            joueur.position = joueur.position + move


def play_screamer(data):
    if "|" not in data:
        return
    img_path, snd_path = data.split("|", 1)
    overlay = Entity(
        model='quad',
        texture=res(img_path),
        scale=(camera.aspect_ratio * 2, 2),
        position=(0, 0),
        parent=camera.ui,
        z=-1
    )
    snd = Audio(res(snd_path), autoplay=True)
    destroy(overlay, delay=1.15)
    destroy(snd, delay=1.15)


def input(key):
    global is_jumping, vertical_velocity, rectangle_visible, on_ground
    if key == 'p':
        print(f"[POS] x={round(joueur.x, 2)}, y={round(joueur.y, 2)}, z={round(joueur.z, 2)}")

    if key == 'escape':
        network.disconnect()
        application.quit()

    if key == touches['Jump'] and on_ground and not is_dead:
        is_jumping = True
        vertical_velocity = jump_force

    if key == touches['Interact']:
        dist = distance(joueur.position, cube_proche.position)
        if dist <= distance_interaction:
            rectangle_visible = not rectangle_visible
            rectangle_ui.enabled = rectangle_visible

        dist_s = distance(joueur.position, cube_screamer.position)
        if dist_s <= distance_interaction:
            img, snd = random.choice(screamer_list)
            if network.connected:
                network.send_screamer(img + "|" + snd)

    if key == 'left mouse down':
        do_attack()

    # ← Touche T pour tester la mort en solo (debug)
    if key == 't':
        print("[DEBUG] Test dégâts forcé")
        receive_damage(999)


def update():
    global rectangle_visible, _send_timer, _son_timer, _attack_timer, _invincibility_timer, _death_timer

    mouvement_joueur()
    mouvement_camera()
    saut()

    # Cooldown attaque (feedback couleur)
    if _attack_timer > 0:
        _attack_timer -= time.dt
        ratio = max(0.0, _attack_timer / ATTACK_COOLDOWN)
        attack_indicator.color = lerp(color.white, color.dark_gray, ratio)

    # Invincibilité
    if _invincibility_timer > 0:
        _invincibility_timer -= time.dt


    # Interaction cube orange
    dist = distance(joueur.position, cube_proche.position)
    if dist > distance_interaction and rectangle_visible:
        rectangle_visible = False
        rectangle_ui.enabled = False

    # Réseau
    if network.connected:
        network_text.text = f'Réseau: connecté ({len(ghost_entities) + 1} joueur(s))'
        network_text.color = color.lime

        _send_timer += time.dt
        if _send_timer >= SEND_INTERVAL:
            _send_timer = 0
            network.send_position(joueur.x, joueur.y, joueur.z, joueur.rotation_y)

        update_ghosts(network.get_other_players())
    else:
        network_text.text = 'Réseau: déconnecté'
        network_text.color = color.red

    # Son ambiance aléatoire
    _son_timer -= time.dt
    if _son_timer <= 0:
        son_gare.play()
        _son_timer = random.uniform(30, 60)
    
    # Rôle : animation d'annonce + indicateur
    update_role_announce()
    update_role_indicator()


# ──────────────────────────────────────────────
# ATTRIBUTION DES RÔLES AU DÉMARRAGE
# ──────────────────────────────────────────────
# Petit délai pour laisser le réseau s'initialiser avant de tirer les rôles
invoke(assign_role, delay=1.5)


Five_nights_at_chatelet.run()