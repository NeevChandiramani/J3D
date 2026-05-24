#lignes à commenter pour désactiver le menu = -


import threading
import math
import os
from pathlib import Path
import json
import sys
from tomlkit import key
from ursina import *
import pygame
import random
from ursina.shaders import lit_with_shadows_shader
from Rooms import Rooms
from NetworkClient import NetworkClient
from enigme_electrique import EnigmeElectrique
from NavigoTask import NavigoTask
from enigme_plomberie import EnigmePlomberie
from EnigmeLabyrintheSignalisation import EnigmeLabyrintheSignalisation



# CHEMINS RESSOURCES (compatibilité PyInstaller)

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
window.fullscreen = True

# Neutraliser le handler interne d'Ursina pour F11 (qui annulerait notre toggle)
if getattr(window, 'input_entity', None) is not None:
    _ursina_orig_input = window.input_entity.input
    def _filtered_window_input(key, _orig=_ursina_orig_input):
        if key in ('f11', 'f11 up'):
            return
        if _orig:
            _orig(key)
    window.input_entity.input = _filtered_window_input

# On change le répertoire de travail vers BASE_DIR
# pour que Ursina trouve les assets avec des chemins relatifs
os.chdir(BASE_DIR)
application.asset_folder = Path(BASE_DIR)
application.compressed_textures_folder = Path(BASE_DIR) / 'textures_compressed'

from ursina import texture_importer as _tex_imp
_tex_imp.folders = [
    application.compressed_textures_folder,
    application.asset_folder,
    application.internal_textures_folder,
]

try:                                                                            #-
    pygame.quit()                                                               #-
except Exception:                                                               #-
    pass                                                                        #-


# RÉSEAU

network = NetworkClient()
connection_ok = network.connect()

ghost_entities = {}   # {player_id: Entity racine du ghost (collider + position)}
ghost_parts = {}      # {player_id: {"corps","tete","bras_g","bras_d","jambe_g","jambe_d","model"}}
ghost_anim_state = {} # {player_id: {"prev_atk": int, "is_attack": bool, "attack_timer": float, "anim_timer": float}}
ghost_hp = {}         # {player_id: int}
ghost_role_by_pid = {} # {player_id: "Survivor"/"Infected"} — rôle réellement utilisé pour bâtir le ghost

SEND_INTERVAL = 0.05
_send_timer = 0

# RÔLES ET ATTRIBUTION

# Définition des rôles disponibles
ROLES = {
    "Survivor": {
        "description": "Find the exits. Avoid the Infected.",
        "color_rgb": (80, 220, 100),
        "model_path": 'ressources/Perso.obj',
        "speed_mult": 1.0,
        "max_hp": 100,
        "can_attack": False,
    },
    "Infected": {
        "description": "Eliminate all Survivors.",
        "color_rgb": (220, 50, 50),
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
_pos_vanne = _pos_electrique = _pos_panneau = _pos_navigo = None

# État de l'écran de connexion (affiché au démarrage)
_connection_screen_active = True
_connection_phase = 0            # 0=fondu entrée, 1=lobby/attente, 2=fondu sortie
_connection_fade  = 0.0
_connection_timer = 0.5          # palier de fallback solo (jamais utilisé en multi)
_local_ready = False             # statut "prêt" du joueur local dans le lobby
CONNECTION_FADE_SPEED = 3.5      # fondu entrée/sortie de l'écran de connexion
_connection_status_rgb = (80, 220, 100)

# --- SYSTÈME DE TÂCHES ---
mes_taches_accomplies = 0
total_de_mes_taches = 4
mon_statut_fini = False

# Liste des IDs des survivants qui ont tout fini
survivants_ayant_fini = set()

# --- SYSTÈME DE VICTOIRE ---
mur_victoire = None
mur_cree = False
victoire_declenchee = False

_liberation_timer = 0.0
LIBERATION_DUREE = 5.0
_liberation_en_cours = False
_liberation_cible = None  # le joueur mort qu'on est en train de libérer
survivants_en_prison = set()  # IDs des survivants emprisonnés
defaite_declenchee = False

def _apply_role(role_name):
    """Applique le rôle décidé : stats, modèles 3D locaux, annonce, embuscadeur."""
    global player_role, MAX_HP, base_speed, _role_announced, _role_announce_timer
    player_role = role_name

    role_data = ROLES[player_role]
    MAX_HP = role_data["max_hp"]
    base_speed = 6.7 * role_data["speed_mult"]
    if player_role == "Infected":
        joueur_corps.model   = 'ressources/C_body.obj'
        joueur_tete.model    = 'ressources/C_head.obj'
        joueur_bras_g.model  = 'ressources/C_left_arm.obj'
        joueur_bras_d.model  = 'ressources/C_right_arm.obj'
        joueur_jambe_g.model = 'ressources/C_left_leg.obj'
        joueur_jambe_d.model = 'ressources/C_right_leg.obj'
    else:
        joueur_corps.model   = 'ressources/P_body.obj'
        joueur_tete.model    = 'ressources/P_head.obj'
        joueur_bras_g.model  = 'ressources/P_left_arm.obj'
        joueur_bras_d.model  = 'ressources/P_right_arm.obj'
        joueur_jambe_g.model = 'ressources/P_left_leg.obj'
        joueur_jambe_d.model = 'ressources/P_right_leg.obj'

    
    for part in [joueur_corps, joueur_tete, joueur_bras_g, joueur_bras_d, joueur_jambe_g, joueur_jambe_d]:
        part.shader = lit_with_shadows_shader

    attack_indicator.enabled = role_data["can_attack"]
    _role_announced = True
    _role_announce_timer = ROLE_ANNOUNCE_DURATION
    show_role_announce()
    print(f"[ROLE] Role attribué : {player_role}")
    init_embuscadeur()


def assign_role():
    """Attribue le rôle local. Préfère les rôles du serveur si déjà reçus,
    sinon tirage 70/30 local (mode solo / réseau indisponible)."""
    global all_assigned_roles
    server_roles = network.get_assigned_roles() if hasattr(network, 'get_assigned_roles') else None
    if server_roles:
        apply_roles_from_server(server_roles)
        return
    role = random.choices(["Survivor", "Infected"], weights=[70, 30])[0]
    if network.my_id is not None:
        all_assigned_roles[str(network.my_id)] = role
    _apply_role(role)


def apply_roles_from_server(roles_dict):
    """Mode multi : applique les rôles décidés par le serveur.
    Ne détruit que les ghosts dont le rôle a réellement changé."""
    global all_assigned_roles
    all_assigned_roles = {str(pid): r for pid, r in roles_dict.items()}
    my_str = str(network.my_id) if network.my_id is not None else None
    my_role = all_assigned_roles.get(my_str, "Survivor") if my_str else "Survivor"
    if player_role != my_role:
        _apply_role(my_role)

    for pid in list(ghost_entities.keys()):
        expected = all_assigned_roles.get(str(pid), "Survivor")
        if ghost_role_by_pid.get(pid) != expected:
            _destroy_ghost(pid)


def sync_roles_from_server():
    """À appeler chaque frame en multi : si le serveur a publié de nouveaux rôles
    (au démarrage ou quand un joueur rejoint), on les applique."""
    if not getattr(network, 'connected', False):
        return
    server_roles = network.get_assigned_roles() if hasattr(network, 'get_assigned_roles') else None
    if not server_roles:
        return
    normalized = {str(pid): r for pid, r in server_roles.items()}
    if normalized == all_assigned_roles:
        return
    apply_roles_from_server(server_roles)




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


def update_connection_screen():
    """Écran de connexion au démarrage : fondu entrée / palier / fondu sortie,
    puis enchaîne sur l'attribution du rôle."""
    global _connection_phase, _connection_fade, _connection_timer
    global _connection_screen_active
    if not _connection_screen_active:
        return

    r, g_c, b = _connection_status_rgb
    dt = time.dt

    if _connection_phase == 0:
        _connection_fade = min(1.0, _connection_fade + dt * CONNECTION_FADE_SPEED)
        a_bg   = int(_connection_fade * 210)
        a_text = int(_connection_fade * 255)
        connection_screen_bg.color     = color.rgba(0, 0, 0, a_bg)
        connection_screen_title.color  = color.rgba(180, 180, 180, a_text)
        connection_screen_status.color = color.rgba(r, g_c, b, a_text)
        connection_screen_sub.color    = color.rgba(120, 120, 120, int(a_text * 0.7))
        if _connection_fade >= 1.0:
            _connection_phase = 1

    elif _connection_phase == 1:
        # Multi : on attend que le serveur ait tiré les rôles (déclenché par
        # "tous prêts" ou par une demande "force_start" venant d'un client).
        # Solo offline : on attend juste le timer puis on passe en tirage local.
        if getattr(network, 'connected', False):
            connection_screen_title.text = 'LOBBY'
            lobby_snapshot = network.get_lobby_state() if hasattr(network, 'get_lobby_state') else {}
            total = len(lobby_snapshot) if lobby_snapshot else 1
            nb_prets = sum(1 for info in lobby_snapshot.values() if info.get('ready'))
            ready_label = 'PRÊT' if _local_ready else 'PAS PRÊT'
            connection_screen_status.text = f'{nb_prets} / {total} joueurs prêts  —  vous : {ready_label}'
            connection_screen_sub.text    = '[R] basculer prêt    [F] démarrer maintenant'
            if network.get_assigned_roles():
                _connection_phase = 2
                _connection_fade  = 1.0
        else:
            _connection_timer -= dt
            if _connection_timer <= 0:
                _connection_phase = 2
                _connection_fade  = 1.0

    elif _connection_phase == 2:
        _connection_fade = max(0.0, _connection_fade - dt * CONNECTION_FADE_SPEED)
        a_bg   = int(_connection_fade * 210)
        a_text = int(_connection_fade * 255)
        connection_screen_bg.color     = color.rgba(0, 0, 0, a_bg)
        connection_screen_title.color  = color.rgba(180, 180, 180, a_text)
        connection_screen_status.color = color.rgba(r, g_c, b, a_text)
        connection_screen_sub.color    = color.rgba(120, 120, 120, int(a_text * 0.7))
        if _connection_fade <= 0.0:
            connection_screen_root.enabled = False
            _connection_screen_active = False
            # Tirage local immédiat : on ne dépend plus du serveur pour les rôles.
            assign_role()


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


def _build_ghost(pid):
    """Crée un ghost articulé (6 pièces) calqué sur la structure du joueur local."""
    ghost_role = all_assigned_roles.get(str(pid), "Survivor")
    prefix = 'C' if ghost_role == "Infected" else 'P'

    # Racine = porteur du collider et de la position, sans modèle visible.
    root = Entity(scale_y=3, collider='box')
    # Pivot intermédiaire pour reproduire l'offset/rotation du joueur local.
    model_pivot = Entity(parent=root, position=(-0.5, 0, 0), rotation_y=180)

    parts = {
        'model':   model_pivot,
        'corps':   Entity(parent=model_pivot, model=f'ressources/{prefix}_body.obj'),
        'tete':    Entity(parent=model_pivot, model=f'ressources/{prefix}_head.obj'),
        'bras_g':  Entity(parent=model_pivot, model=f'ressources/{prefix}_left_arm.obj'),
        'bras_d':  Entity(parent=model_pivot, model=f'ressources/{prefix}_right_arm.obj'),
        'jambe_g': Entity(parent=model_pivot, model=f'ressources/{prefix}_left_leg.obj'),
        'jambe_d': Entity(parent=model_pivot, model=f'ressources/{prefix}_right_leg.obj'),
    }

    ghost_entities[pid] = root
    ghost_parts[pid] = parts
    ghost_anim_state[pid] = {"prev_atk": 0, "is_attack": False, "attack_timer": 0.0, "anim_timer": 0.0}
    ghost_hp[pid] = ROLES[ghost_role]["max_hp"]
    ghost_role_by_pid[pid] = ghost_role


def _destroy_ghost(pid):
    """Détruit toutes les pièces d'un ghost et nettoie les dicts."""
    parts = ghost_parts.pop(pid, None)
    if parts:
        for k, e in parts.items():
            try: destroy(e)
            except Exception: pass
    root = ghost_entities.pop(pid, None)
    if root:
        try: destroy(root)
        except Exception: pass
    ghost_anim_state.pop(pid, None)
    ghost_hp.pop(pid, None)
    ghost_role_by_pid.pop(pid, None)


def _animate_ghost(pid, mv, sp, atk):
    """Reproduit sur le ghost les mêmes animations que celles du joueur local
    (cf. update() lignes ~2132-2175). Utilise un timer local par ghost."""
    parts = ghost_parts.get(pid)
    st = ghost_anim_state.get(pid)
    if not parts or not st:
        return

    dt = time.dt

    # Détection front montant d'attaque : on déclenche la séquence locale
    prev_atk = st.get("prev_atk", 0)
    if atk == 1 and prev_atk == 0:
        st["is_attack"] = True
        st["attack_timer"] = 0.0
    st["prev_atk"] = atk

    if st["is_attack"]:
        st["attack_timer"] += dt * 14
        t = math.sin(st["attack_timer"])
        parts['bras_g'].rotation_x = -t * 45
        parts['bras_d'].rotation_x = -t * 45
        parts['corps'].rotation_x  =  t * 10
        parts['tete'].rotation_x   =  t * 8
        if st["attack_timer"] >= math.pi:
            st["is_attack"] = False
            st["attack_timer"] = 0.0
            parts['bras_g'].rotation_x = 0
            parts['bras_d'].rotation_x = 0
            parts['corps'].rotation_x  = 0
            parts['tete'].rotation_x   = 0
        return

    if mv == 1:
        anim_speed = 12 if sp == 1 else 7
        st["anim_timer"] += dt * anim_speed
        at = st["anim_timer"]
        parts['jambe_g'].rotation_x =  math.sin(at) * 6
        parts['jambe_d'].rotation_x = -math.sin(at) * 6
        parts['bras_g'].rotation_x  = -math.sin(at) * 5
        parts['bras_d'].rotation_x  =  math.sin(at) * 5
        parts['model'].y            =  math.sin(at * 2) * 0.01
        parts['corps'].rotation_z   =  math.sin(at) * 0.5
    else:
        st["anim_timer"] += dt * 1.5
        at = st["anim_timer"]
        parts['jambe_g'].rotation_x = lerp(parts['jambe_g'].rotation_x, 0, dt * 8)
        parts['jambe_d'].rotation_x = lerp(parts['jambe_d'].rotation_x, 0, dt * 8)
        parts['bras_g'].rotation_x  = lerp(parts['bras_g'].rotation_x,  0, dt * 8)
        parts['bras_d'].rotation_x  = lerp(parts['bras_d'].rotation_x,  0, dt * 8)
        parts['corps'].rotation_z   = lerp(parts['corps'].rotation_z,   0, dt * 8)
        parts['corps'].y  = math.sin(at) * 0.021
        parts['tete'].y   = math.sin(at) * 0.019
        parts['bras_g'].y = math.sin(at) * 0.019
        parts['bras_d'].y = math.sin(at) * 0.019
        parts['jambe_g'].y = math.sin(at) * 0.014
        parts['jambe_d'].y = math.sin(at) * 0.014


def update_ghosts(other_players):
    global mur_victoire, mur_cree

    for pid in list(ghost_entities.keys()):
        if pid not in other_players:
            _destroy_ghost(pid)

    for pid, data in other_players.items():
        if not isinstance(data, dict) or "x" not in data or "y" not in data or "z" not in data:
            continue

        if pid not in ghost_entities:
            _build_ghost(pid)

        root = ghost_entities[pid]
        root.position = Vec3(data["x"], data["y"], data["z"])
        if "ry" in data:
            root.rotation_y = data["ry"]

        _animate_ghost(
            pid,
            mv=int(data.get("mv", 0)),
            sp=int(data.get("sp", 0)),
            atk=int(data.get("atk", 0)),
        )

    if hasattr(network, 'get_damage_events'):
        for event in network.get_damage_events():
            if not isinstance(event, dict):
                continue
                
            # --- INTERCEPTION DU MESSAGE TÂCHES FINIES ---
            if event.get('type') == 'survivant_fini':
                id_joueur = event.get('id')
                survivants_ayant_fini.add(id_joueur)
                print(f"[RESEAU] Le joueur {id_joueur} a fini ses tâches !")
                
                # Calcul dynamique du nombre de survivants connectés
                nombre_total_survivants = sum(1 for p in all_assigned_roles.values() if p == 'Survivor')
                if nombre_total_survivants == 0:  # Sécurité si l'enchaînement n'est pas encore prêt
                    nombre_total_survivants = 1
                    
                print(f"Survivants prêts : {len(survivants_ayant_fini)} / {nombre_total_survivants}")
                
                # Si tous les survivants ont fini, apparition du mur vert
                if len(survivants_ayant_fini) >= nombre_total_survivants:
                    if not mur_cree:
                        mur_victoire = Entity(
                            model='cube',
                            color=color.green,
                            alpha=0.4,              # Semi-transparent 
                            position=(56.4, 2.97, 0.28),
                            scale=(0.5, 6.0, 22.68), # Dimensions basées sur tes positions
                            collider=None           # Pas de collider physique pour entrer dedans
                        )
                        mur_cree = True
                        print("[GAME] Le mur vert de la victoire est apparu ! Fuyez !")
                continue # Passe à l'événement suivant

            if event.get("type") == "screamer":
                play_screamer(event.get("screamer"))
                continue
                
            print(f"[NET] Event dégât reçu : {event}")
            if network.my_id is not None and str(event.get("target_id")) == str(network.my_id):
                print(f"[NET] Je suis la cible ! Appel receive_damage({event.get('amount', 10)})")
                receive_damage(event.get("amount", 10))

            target_pid = str(event.get("target_id"))
            if target_pid in ghost_parts:
                for k in ('corps', 'tete', 'bras_g', 'bras_d', 'jambe_g', 'jambe_d'):
                    part = ghost_parts[target_pid].get(k)
                    if part is None:
                        continue
                    part.color = color.red
                    invoke(setattr, part, 'color', color.white, delay=0.15)

SALLES = [
    Vec3(-73.42, 35.98, 4.77),
    Vec3(-48.25, 35.98, 49.44),
    Vec3(34.82,  35.98, 94.12),
    Vec3(61.85,  35.98, 34.84),
    Vec3(94.31,  35.98, 9.13),
    Vec3(65.81,  35.98, -49.09),
    Vec3(57.14,  93.36, 42.67),
    Vec3(26.36,  35.98, -61.61),
    Vec3(-23.41, 35.98, -73.21),
    Vec3(-72.82, 35.98, -37.3),
]
DISTANCE_MIN = 60

def choisir_salles_tasks(player_id):
    try:
        rng = random.Random(int(player_id))
    except:
        seed_int = sum(ord(c) for c in str(player_id))
        rng = random.Random(seed_int)
    
    tasks = ['navigo', 'vanne', 'electrique', 'panneau', 'screamer1', 'screamer2']
    
    for _ in range(1000):
        choix = rng.sample(range(len(SALLES)), 6)
        valide = True
        
        for i in range(len(choix)):
            for j in range(i + 1, len(choix)):
                a, b = SALLES[choix[i]], SALLES[choix[j]]
                dist = math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2 + (a.z-b.z)**2)
                if dist < DISTANCE_MIN:
                    valide = False
                    break
            if not valide:
                break
                
        if valide:
            return dict(zip(tasks, [SALLES[i] for i in choix]))
    
    return dict(zip(tasks, rng.sample(SALLES, 6)))


sol = Entity(
    model="ressources/Mall.obj",
    collider="mesh",
    shader=lit_with_shadows_shader,
    scale=Vec3(0.5, 1.5, 0.5)
)
meubles = Entity(
    model="ressources/Meubles.obj",
    shader=lit_with_shadows_shader,
    scale=Vec3(0.5, 1.5, 0.5)
)

panneau_1 = Entity(
    model="ressources/affiche1.obj",
    texture="ressources/visuel-epita.png",
    scale=Vec3(0.5, 1.5, 0.5)
)

panneau_3 = Entity(
    model="ressources/leo.obj",
    texture="ressources/leonardo.png",
    scale=Vec3(0.5, 1.5, 0.5)
)

panneau_4 = Entity(
    model="ressources/chatelet.obj",
    texture="ressources/image.png",
    scale=Vec3(0.5, 1.5, 0.5)
)

panneau_5 = Entity(
    model="ressources/karin1.obj",
    texture="ressources/260408-karina-for-kloud-krush-light-v0-0e3u9uoyzutg1",
    scale=Vec3(0.5, 1.5, 0.5)
)

panneau_6 = Entity(
    model="ressources/epi2.obj",
    texture="ressources/vignettepita.jpg",
    scale=Vec3(0.5, 1.5, 0.5)
)

panneau_7 = Entity(
    model="ressources/five.obj",
    texture="ressources/Affiche J3D.png",
    scale=Vec3(0.5, 1.5, 0.5)
)

panneau_8 = Entity(
    model="ressources/train.obj",
    texture="ressources/merlin_144336495_10bd9321-e5d9-40c3-b83d-d6a4b38f6685-superJumbo.png",
    scale=Vec3(0.5, 1.5, 0.5)
)

panneau_9 = Entity(
    model="ressources/j.obj",
    texture="ressources/un_juif_pour__exemple_thierry_piquet_theatre_mathurins_affiche_1741610827.png",
    scale=Vec3(0.5, 1.5, 0.5)
)

panneau_10 = Entity(
    model="ressources/kari2.obj",
    texture="ressources/news-p.v1.20260313.16306f6b54204a0390509c44508b55e3_P2.png",
    scale=Vec3(0.5, 1.5, 0.5)
)

panneau_11 = Entity(
    model="ressources/gare.obj",
    texture="ressources/gare.png",
    scale=Vec3(0.5, 1.5, 0.5)
)

joueur = Entity(
    position=(15, 3, 0),
    collider='box',
    scale_y=3
)

cube_vanne = Entity(
    model='cube', color=color.cyan,
    position=(0, 35, 0),
    collider='box', shader=lit_with_shadows_shader
)

cube_electrique = Entity(
    model='cube', color=color.yellow,
    position=(0, 35, 0),
    collider='box', shader=lit_with_shadows_shader
)

cube_panneau = Entity(
    model='cube', color=color.blue,
    position=(0, 35, 0),
    collider='box', shader=lit_with_shadows_shader
)

cube_screamer1 = Entity(
    model='cube', color=color.red, 
    position=(0, 0, 0),
    collider='box', shader=lit_with_shadows_shader
)

cube_screamer2 = Entity(
    model='cube', color=color.red,
    position=(0, 0, 0),
    collider='box', shader=lit_with_shadows_shader
)

_pos_screamer1 = None
_pos_screamer2 = None

calcul_termine = False # Nouvelle variable de sécurité
navigo_task = None

def purge_validee():
    print("[GAME] Égouts purgés !")
    valider_une_tache()

enigme_plomberie = EnigmePlomberie(on_success=purge_validee)

def enigme_resolue():
    print("[GAME] Puzzle électrique validé !")
    valider_une_tache()
    # mets ici ce que tu veux déclencher (ouvrir une porte, XP, etc.)

enigme = EnigmeElectrique(on_success=enigme_resolue)

def signalisation_restauree():
    print("[GAME] Signalisation restaurée !")
    valider_une_tache()

enigme_signalisation = EnigmeLabyrintheSignalisation(on_success=signalisation_restauree)

def init_tasks_math():
    global _pos_vanne, _pos_electrique, _pos_panneau, _pos_navigo, calcul_termine
    global _pos_screamer1, _pos_screamer2
    import time as pytime
    
    attente = 0
    while network.my_id is None and attente < 30:
        pytime.sleep(0.1)
        attente += 1
    
    seed_id = network.my_id if network.my_id is not None else random.randint(1, 99999)
    try:
        seed_int = int(seed_id)
    except ValueError:
        seed_int = sum(ord(c) for c in str(seed_id))
    
    pos = choisir_salles_tasks(seed_int)
    
    _pos_vanne      = pos['vanne']      + Vec3(0, 2.5, 0)
    _pos_electrique = pos['electrique'] + Vec3(0, 2.5, 0)
    _pos_panneau    = pos['panneau']    + Vec3(0, 2.5, 0)
    _pos_navigo     = pos['navigo']     + Vec3(0, 2.5, 0)
    
    _pos_screamer1  = pos['screamer1']  + Vec3(0, 2.5, 0)
    _pos_screamer2  = pos['screamer2']  + Vec3(0, 2.5, 0)
    
    calcul_termine = True
    print("[TASKS] Positions calculées avec succès en arrière-plan !")

threading.Thread(target=init_tasks_math, daemon=True).start()

def valider_une_tache():
    global mes_taches_accomplies, mon_statut_fini
    
    mes_taches_accomplies += 1
    print(f"[TÂCHES] Progression : {mes_taches_accomplies}/{total_de_mes_taches}")
    
    if mes_taches_accomplies >= total_de_mes_taches and not mon_statut_fini:
        mon_statut_fini = True
        print("[GAME] Toutes mes tâches finies, message envoyé !")
        if network and network.connected and network.my_id is not None:
            network.sock.sendall((json.dumps({"type": "survivant_fini", "id": network.my_id}) + "\n").encode())

def declencher_retour_menu():
    if run_menu:
        result = run_menu()
        if result == 'start':
            os.execv(sys.executable, [sys.executable] + sys.argv)
    sys.exit()

# SYSTEME AUDIO

if not pygame.mixer.get_init():
    pygame.mixer.init()

channel_ambiance = pygame.mixer.Channel(0)
channel_heartbeat = pygame.mixer.Channel(1)
channel_infected_breath = pygame.mixer.Channel(2)
channel_footsteps = pygame.mixer.Channel(3)

AUDIO_GAME = {
    'ambiance': pygame.mixer.Sound(res('ressources/sounds/ambiance.ogg')),
    'jump': pygame.mixer.Sound(res('ressources/sounds/jump.ogg')),
    'attack': pygame.mixer.Sound(res('ressources/sounds/attack.ogg')),
    'hit': pygame.mixer.Sound(res('ressources/sounds/hit.ogg')),
    'hurt': pygame.mixer.Sound(res('ressources/sounds/hurt.ogg')),
    'death': pygame.mixer.Sound(res('ressources/sounds/death.ogg')),
    'interact': pygame.mixer.Sound(res('ressources/sounds/interact.ogg')),
    'heartbeat': pygame.mixer.Sound(res('ressources/sounds/heartbeat.ogg')),
    'pas_survivor': pygame.mixer.Sound(res('ressources/sounds/footsteps_survivor.ogg')),
    'pas_infected': pygame.mixer.Sound(res('ressources/sounds/footsteps_infected.ogg')),
    'rale_infected': pygame.mixer.Sound(res('ressources/sounds/infected_breath.ogg')),
    'chuchotement': pygame.mixer.Sound(res('ressources/sounds/whispers.ogg')),
    'haunted': pygame.mixer.Sound(res('ressources/sounds/haunted.ogg'))
}

def play_sfx(name, volume=1.0):
    if name in AUDIO_GAME:
        s = AUDIO_GAME[name]
        s.set_volume(volume)
        s.play()

# Variables pour le suivi des boucles et timers audio
_heartbeat_playing = False
_breath_playing = False
_footstep_timer = 0.0
_whisper_timer = random.uniform(15.0, 40.0)
_son_timer = random.uniform(60, 120)
_anim_timer = 0.0
_is_attack_anim = False
_attack_anim_timer = 0.0
_son_timer = 0.0


AmbientLight(color=Vec4(0.01, 0.01, 0.01, 1))

metro_lights = [
    (Vec3(15, 8, 0),    Vec4(0.07, 0.08, 0.08, 1), 9),
    (Vec3(-10, 8, 10),  Vec4(0.05, 0.08, 0.06, 1), 9),
    (Vec3(-30, 8, -8),  Vec4(0.08, 0.04, 0.04, 1), 9),
    (Vec3(0, 8, -20),   Vec4(0.06, 0.07, 0.09, 1), 9),
    (Vec3(30, 8, 15),   Vec4(0.08, 0.08, 0.06, 1), 9),
    (Vec3(-45, 35, 0),  Vec4(0.06, 0.02, 0.02, 1), 12),
    (Vec3(0, 35, 0),    Vec4(0.05, 0.06, 0.08, 1), 12),
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
    position=(-0.5, 0, 0), 
    rotation_y=180
)
joueur_corps       = Entity(parent=joueur_model, model='ressources/C_body.obj')
joueur_tete        = Entity(parent=joueur_model, model='ressources/C_head.obj')
joueur_bras_g      = Entity(parent=joueur_model, model='ressources/C_left_arm.obj')
joueur_bras_d      = Entity(parent=joueur_model, model='ressources/C_right_arm.obj')
joueur_jambe_g     = Entity(parent=joueur_model, model='ressources/C_left_leg.obj')
joueur_jambe_d     = Entity(parent=joueur_model, model='ressources/C_right_leg.obj')


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
blocs_murs = [
    [Vec3(-60.47, 35.98, -0.31), Vec3(-61.32, 35.98, -3.73), Vec3(-84.4, 35.98, 0.1), Vec3(-81.12, 35.98, 20.23), Vec3(-58.07, 35.98, 16.71), Vec3(-57.51, 35.98, 13.7)],
    [Vec3(-47.54, 35.98, 30.95), Vec3(-50.39, 35.98, 29.76), Vec3(-66.23, 35.98, 48.68), Vec3(-50.61, 35.98, 61.59), Vec3(-35.03, 35.98, 42.96), Vec3(-36.29, 35.98, 40.04)],
    [Vec3(8.14, 35.98, 50.18), Vec3(4.37, 35.98, 50.43), Vec3(15.73, 35.98, 100.76), Vec3(38.99, 35.98, 97.7), Vec3(27.64, 35.98, 47.43), Vec3(23.08, 35.98, 46.37)],
    [Vec3(42.73, 35.98, 35.79), Vec3(41.52, 35.98, 39.76), Vec3(69.42, 35.98, 65.84), Vec3(84.73, 35.98, 48.76), Vec3(56.71, 35.98, 22.53), Vec3(51.95, 35.98, 25.21)],
    [Vec3(59.6, 35.98, 6.99), Vec3(60.11, 35.98, 12.81), Vec3(97.79, 35.98, 12.6), Vec3(98.14, 35.98, -12.51), Vec3(60.43, 35.98, -12.59), Vec3(59.73, 35.98, -7.17)],
    [Vec3(51.67, 35.98, -25.32), Vec3(56.2, 35.98, -21.98), Vec3(82.42, 35.98, -46.73), Vec3(68.02, 35.98, -62.81), Vec3(41.61, 35.98, -38.81), Vec3(42.36, 35.98, -35.21)],
    [Vec3(22.6, 35.98, -46.26), Vec3(27.26, 35.98, -46.62), Vec3(33.98, 35.98, -76.26), Vec3(12.45, 35.98, -80.95), Vec3(5.38, 35.98, -51.59), Vec3(8.56, 35.98, -49.4)],
    [Vec3(-16.11, 35.98, -48.61), Vec3(-12.94, 35.98, -51.98), Vec3(-21.83, 35.98, -77.37), Vec3(-43.33, 35.98, -68.5), Vec3(-34.72, 35.98, -43.41), Vec3(-30.45, 35.98, -43.57)],
    [Vec3(-47.72, 35.98, -30.76), Vec3(-45.69, 35.98, -35.89), Vec3(-67.14, 35.98, -51.22), Vec3(-80.07, 35.98, -30.47), Vec3(-58.93, 35.98, -15.29), Vec3(-55.54, 35.98, -19.31)],
    
    [Vec3(42.81, 93.36, 34.87), Vec3(60.31, 93.36, 50.99), Vec3(68.72, 93.36, 41.28), Vec3(50.98, 93.54, 25.25)],
    [Vec3(55.0, 93.54, 15.13), Vec3(44.5, 93.54, 15.36), Vec3(44.78, 93.54, 10.56), Vec3(43.04, 93.54, 11.91)]
]

points_ordonnes = [
    Vec3(-54.68, 2.97, -18.7), Vec3(-58.42, 2.97, -8.51), Vec3(-59.49, 2.97, -0.42),
    Vec3(-56.84, 2.97, 13.17), Vec3(-52.88, 2.97, 22.37), Vec3(-47.23, 2.97, 29.86),
    Vec3(-36.4, 2.97, 38.83), Vec3(-15.64, 2.97, 47.47), Vec3(8.06, 2.97, 49.17),
    Vec3(22.52, 2.97, 45.41), Vec3(31.38, 2.97, 41.93), Vec3(41.83, 2.97, 35.04),
    Vec3(51.21, 2.97, 24.59), Vec3(55.45, 2.97, 17.38), Vec3(58.68, 2.97, 7.43),
    Vec3(58.77, 2.97, -6.47), Vec3(55.36, 2.97, -16.81), Vec3(51.15, 2.97, -24.6),
    Vec3(41.61, 2.97, -34.68), Vec3(34.01, 2.97, -40.23), Vec3(23.05, 2.97, -45.35),
    Vec3(8.42, 2.97, -48.57), Vec3(-4.52, 2.97, -48.73), Vec3(-15.51, 2.97, -47.52),
    Vec3(-30.0, 2.97, -42.63), Vec3(-36.88, 2.97, -38.68), Vec3(-47.14, 2.97, -30.29)
]

murs_coordonnees = [
    (Vec3(-54.68, 35.98, -18.7), Vec3(-58.42, 35.98, -8.51)), (Vec3(-58.42, 35.98, -8.51), Vec3(-59.49, 35.56, -0.42)),
    (Vec3(-56.84, 35.98, 13.17), Vec3(-52.88, 35.98, 22.37)), (Vec3(-52.88, 35.98, 22.37), Vec3(-47.23, 35.98, 29.86)),
    (Vec3(-36.4, 35.98, 38.83), Vec3(-15.64, 35.98, 47.47)), (Vec3(-15.64, 35.98, 47.47), Vec3(8.06, 35.98, 49.17)),
    (Vec3(22.52, 35.98, 45.41), Vec3(31.38, 35.98, 41.93)), (Vec3(31.38, 35.98, 41.93), Vec3(41.83, 35.98, 35.04)),
    (Vec3(51.21, 35.98, 24.59), Vec3(55.45, 35.98, 17.38)), (Vec3(55.45, 35.98, 17.38), Vec3(58.68, 35.98, 7.43)),
    (Vec3(58.77, 35.98, -6.47), Vec3(55.36, 35.98, -16.81)), (Vec3(55.36, 35.98, -16.81), Vec3(51.15, 35.98, -24.6)),
    (Vec3(41.61, 35.98, -34.68), Vec3(34.01, 35.98, -40.23)), (Vec3(34.01, 35.98, -40.23), Vec3(23.05, 35.98, -45.35)),
    (Vec3(8.42, 35.98, -48.57), Vec3(-4.52, 35.98, -48.73)), (Vec3(-4.52, 35.98, -48.73), Vec3(-15.51, 35.98, -47.52)),
    (Vec3(-30.0, 35.98, -42.63), Vec3(-36.88, 35.98, -38.68)), (Vec3(-36.88, 35.98, -38.68), Vec3(-47.14, 35.98, -30.29)),
    (Vec3(-15.93, 93.54, 29.18), Vec3(-13.53, 93.54, 46.81))
]

murs_boucles = [
    [Vec3(7.9, 93.54, 48.54), Vec3(21.78, 93.54, 45.87), Vec3(27.65, 93.49, 69.08), Vec3(13.89, 93.49, 71.36)]
]

mur_cylindre = []

def ajouter_segment(p1, p2, force_hauteur=None, force_y_centre=None):
    centre = (p1 + p2) / 2
    if force_hauteur is not None and force_y_centre is not None:
        hauteur = force_hauteur
        centre.y = force_y_centre
    else:
        hauteur = 150.0 - p1.y
        centre.y = p1.y + (hauteur / 2)
        
    longueur = math.sqrt((p2.x - p1.x)**2 + (p2.z - p1.z)**2)
    angle = math.degrees(math.atan2(p2.x - p1.x, p2.z - p1.z))
    
    segment = Entity(
        model='cube',
        collider='box',
        visible=False,
        position=centre,
        scale=(0.3, hauteur, longueur),
        rotation_y=angle,
        color=color.rgba32(0, 255, 100, 90)
    )
    mur_cylindre.append(segment)

for points_du_mur in blocs_murs:
    for idx in range(len(points_du_mur) - 1):
        ajouter_segment(points_du_mur[idx], points_du_mur[idx + 1])

h_totale = 35.0 - 2.97
y_mid = 2.97 + (h_totale / 2)
nb_points = len(points_ordonnes)
for idx in range(nb_points):
    ajouter_segment(points_ordonnes[idx], points_ordonnes[(idx + 1) % nb_points], force_hauteur=h_totale, force_y_centre=y_mid)

for p1, p2 in murs_coordonnees:
    ajouter_segment(p1, p2)

for points_du_mur in murs_boucles:
    nb = len(points_du_mur)
    for idx in range(nb):
        ajouter_segment(points_du_mur[idx], points_du_mur[(idx + 1) % nb])

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


# CUBE SCREAMER

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


# ── EMBUSCADEUR (IA) ────────────────────────────────────────────────────────────
# Positions candidates dans les couloirs et les coins de la map.
# Dérivées de points_ordonnes (y≈2.97 sol) et SALLES (y≈35.98 étage).
EMBUSCADE_POSITIONS = [
    Vec3(-62.18, 35.98,  -2.44),
    Vec3(-58.68, 35.98,  15.42),
    Vec3(-63.60, 35.98,  12.92),
    Vec3(-58.50, 35.98, -17.37),
    Vec3(-47.42, 35.98, -35.85),
    Vec3(-32.78, 35.98, -44.47),
    Vec3(-15.17, 35.98, -50.76),
    Vec3(-32.14, 35.98, -58.42),
    Vec3(-24.61, 35.98, -62.90),
    Vec3(  7.75, 35.98, -50.90),
    Vec3( 26.25, 35.98, -47.41),
    Vec3( 13.70, 35.98, -54.77),
    Vec3( 42.67, 35.98, -38.27),
    Vec3( 54.41, 35.98, -25.21),
    Vec3( 56.92, 35.98, -30.63),
    Vec3( 61.31, 35.98, -10.83),
    Vec3( 60.98, 35.98,   9.35),
    Vec3( 53.73, 35.98,  25.28),
    Vec3( 42.71, 35.98,  39.24),
    Vec3( 53.03, 35.98,  38.90),
    Vec3( 24.34, 35.98,  47.64),
    Vec3(  6.03, 35.98,  52.20),
    Vec3( 14.75, 35.98,  58.22),
    Vec3(-36.72, 35.98,  41.70),
    Vec3(-50.41, 35.98,  31.26),
    Vec3(-50.61, 35.98,  41.39),
    Vec3(-43.01, 35.98,  42.13),
]

EMBUSCADE_DAMAGE        = 15    # HP retirés lors d'un bond
EMBUSCADE_DETECT_WALK   = 3.5   # rayon de détection (marche)
EMBUSCADE_DETECT_SPRINT = 9.0   # rayon de détection (sprint — beaucoup de bruit)
EMBUSCADE_TENSION_TIME  = 0.7   # secondes dans la zone avant le déclenchement
EMBUSCADE_COOLDOWN      = 30.0  # secondes de pause après chaque attaque
EMBUSCADE_LEAP_SPEED    = 20.0  # vitesse du bond vers le joueur
EMBUSCADE_LEAP_DURATION = 0.35  # durée du bond (secondes)

_emb_pos_order    = []     # ordre shufflé propre au joueur (seed = my_id)
_emb_pos_index    = 0
_emb_state        = "wait" # "wait" | "hidden" | "tension" | "leap" | "cooldown"
_emb_tension_timer  = 0.0
_emb_cooldown_timer = 0.0
_emb_leap_timer     = 0.0
_emb_leap_target    = Vec3(0, 0, 0)
_emb_entity         = None  # entité 3D de l'embuscadeur (créée après assign_role)


def _emb_current_pos():
    idx = _emb_pos_order[_emb_pos_index % len(_emb_pos_order)]
    return EMBUSCADE_POSITIONS[idx]


def _emb_advance():
    """Passe à la prochaine position dans l'ordre shufflé."""
    global _emb_pos_index
    _emb_pos_index = (_emb_pos_index + 1) % len(_emb_pos_order)


def init_embuscadeur():
    """
    Appelé une seule fois depuis assign_role(), après que network.my_id est connu.
    Crée l'entité et calcule l'ordre des positions (seed = my_id → unique par joueur).
    """
    global _emb_pos_order, _emb_pos_index, _emb_entity, _emb_state

    seed_id = network.my_id if network.my_id is not None else random.randint(1, 99999)
    try:
        seed_int = int(seed_id)
    except (ValueError, TypeError):
        seed_int = sum(ord(c) for c in str(seed_id))

    rng = random.Random(seed_int + 31337)
    _emb_pos_order = list(range(len(EMBUSCADE_POSITIONS)))
    rng.shuffle(_emb_pos_order)
    _emb_pos_index = 0

    start_pos = _emb_current_pos()

    _emb_entity = Entity(
        model='cube',
        color=color.red,
        scale=(0.8, 2.5, 0.8),
        position=start_pos,
        collider=None,
        shader=lit_with_shadows_shader,
        enabled=True,
    )

    _emb_state = "hidden"
    print(f"[EMBUSCADE] Initialisé à {start_pos}")


def _emb_trigger():
    """Déclenche le bond, le screamer et les dégâts."""
    global _emb_state, _emb_leap_timer, _emb_leap_target

    if _emb_entity is None:
        return

    _emb_state      = "leap"
    _emb_leap_timer = EMBUSCADE_LEAP_DURATION
    # Cible = tête du joueur
    _emb_leap_target = Vec3(joueur.x, joueur.y + 1.5, joueur.z)

    _emb_entity.enabled = True

    # Orienter l'embuscadeur vers le joueur
    delta = _emb_leap_target - _emb_entity.position
    if delta.length() > 0.01:
        _emb_entity.look_at(joueur)

    # Screamer + dégâts
    img, snd = random.choice(screamer_list)
    play_screamer(img + "|" + snd)
    if network.connected:
        network.send_screamer(img + "|" + snd)

    receive_damage(EMBUSCADE_DAMAGE)
    print(f"[EMBUSCADE] BOND ! -{EMBUSCADE_DAMAGE} HP")


def update_embuscadeur():
    """Appelée chaque frame depuis update()."""
    global _emb_state, _emb_tension_timer, _emb_cooldown_timer, _emb_leap_timer

    if _emb_entity is None or _emb_state == "wait" or is_dead or player_role is None:
        return

    # ── COOLDOWN : repositionnement après attaque ──────────────────────────────
    if _emb_state == "cooldown":
        _emb_cooldown_timer -= time.dt
        if _emb_cooldown_timer <= 0:
            _emb_advance()
            new_pos = _emb_current_pos()
            _emb_entity.position = new_pos
            _emb_entity.enabled  = True
            _emb_state = "hidden"
            print(f"[EMBUSCADE] Repositionné → {new_pos}")
        return

    # ── BOND : l'embuscadeur se précipite vers le joueur ──────────────────────
    if _emb_state == "leap":
        _emb_leap_timer -= time.dt
        if _emb_leap_timer > 0:
            delta = _emb_leap_target - _emb_entity.position
            if delta.length() > 0.1:
                _emb_entity.position += delta.normalized() * EMBUSCADE_LEAP_SPEED * time.dt
        else:
            _emb_entity.enabled  = True
            _emb_state           = "cooldown"
            _emb_cooldown_timer  = EMBUSCADE_COOLDOWN
            print(f"[EMBUSCADE] En cooldown {EMBUSCADE_COOLDOWN}s")
        return

    # ── CACHÉ ou TENSION : calcul bruit joueur ─────────────────────────────────
    is_moving = (
        held_keys[touches['Move Forward']]  or held_keys[touches['Move Backward']] or
        held_keys[touches['Move Left']]     or held_keys[touches['Move Right']]
    )
    is_sprinting_now = held_keys[touches['Sprint']] and is_moving and current_stamina > 1

    if is_sprinting_now:
        detect_r = EMBUSCADE_DETECT_SPRINT
    elif is_moving:
        detect_r = EMBUSCADE_DETECT_WALK
    else:
        detect_r = 0.0          # immobile = silencieux = indétectable

    dist = distance(joueur.position, _emb_entity.position)

    if _emb_state == "hidden":
        if detect_r > 0 and dist <= detect_r:
            _emb_state        = "tension"
            _emb_tension_timer = EMBUSCADE_TENSION_TIME
            print(f"[EMBUSCADE] Tension ! dist={dist:.1f} rayon={detect_r:.1f}")

    elif _emb_state == "tension":
        if detect_r == 0 or dist > detect_r:
            # Joueur s'est arrêté / éloigné → l'embuscadeur se rendort
            _emb_state = "hidden"
            return
        _emb_tension_timer -= time.dt
        if _emb_tension_timer <= 0:
            _emb_trigger()

def bouton_respawn():
    respawn_player()

def bouton_menu():
    network.disconnect()
    import subprocess, sys, os
    subprocess.Popen([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "Five_Nights_At_Chatelet.py")])
    application.quit()

interaction_text = Text(
    text='Maintenez sur E pour libérer',
    parent=scene,
    position=(14.89, 95, 45.97),
    scale=5,
    color=color.white,
    billboard=True,
    enabled=True
)

# HP

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
    
    play_sfx('hurt')

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
    global is_dead
    is_dead = True
    hp_text.text = 'HP: 0  —  EMPRISONNÉ'
    hp_text.color = color.red
    play_sfx('death')
    
    joueur.position = (17.34, 98.17, 60.4)
    mouse.locked = True
    mouse.visible = False

    if network and network.connected and network.my_id is not None:
        network.sock.sendall((json.dumps({
            "type": "survivant_emprisonne",
            "id": str(network.my_id)
        }) + "\n").encode())

def respawn_player():
    global is_dead, player_hp, _invincibility_timer
    is_dead = False
    player_hp = MAX_HP
    _invincibility_timer = 1.0
    joueur.position = (15, 3, 0)
    hp_text.color = color.lime
    update_hp_ui()
    mouse.locked = True
    mouse.visible = False

def update_liberation():
    global _liberation_timer, _liberation_en_cours, _liberation_cible, is_dead

    POS_LEVIER = Vec3(14.89, 93.54, 45.97)
    RAYON = 3.0

    # Si le joueur local est mort, il ne peut pas libérer
    if player_role == 'Infected':
        _liberation_en_cours = False
        _liberation_timer = 0.0
        return

    # Chercher un joueur mort proche du levier
    cible_trouvee = None
    for pid, ghost in ghost_entities.items():
        if pid in survivants_en_prison:
            dist_levier = distance(ghost.position, POS_LEVIER)
            dist_joueur = distance(joueur.position, POS_LEVIER)
            if dist_levier < RAYON and dist_joueur < RAYON:
                cible_trouvee = pid
                break

    if held_keys[touches['Interact']] and cible_trouvee:
        if not _liberation_en_cours or _liberation_cible != cible_trouvee:
            _liberation_en_cours = True
            _liberation_cible = cible_trouvee
            _liberation_timer = 0.0

        _liberation_timer += time.dt
        # Afficher progression
        pct = int((_liberation_timer / LIBERATION_DUREE) * 100)
        interaction_text.text = f'Libération : {pct}%'
        interaction_text.enabled = True

        if _liberation_timer >= LIBERATION_DUREE:
            # Libérer le joueur via réseau
            if network and network.connected:
                network.sock.sendall((json.dumps({
                    "type": "liberer_joueur",
                    "target_id": _liberation_cible
                }) + "\n").encode())
            _liberation_en_cours = False
            _liberation_timer = 0.0
            _liberation_cible = None
            interaction_text.enabled = False
    else:
        _liberation_en_cours = False
        _liberation_timer = 0.0
        if cible_trouvee is None:
            interaction_text.enabled = False

def verifier_defaite():
    global defaite_declenchee
    if defaite_declenchee:
        return

    nombre_total_survivants = sum(1 for r in all_assigned_roles.values() if r == 'Survivor')
    if nombre_total_survivants == 0:
        return

    # Compter les survivants locaux emprisonnés
    survivants_emprisonnes = set(survivants_en_prison)
    if is_dead and player_role == 'Survivor':
        survivants_emprisonnes.add(str(network.my_id))

    if len(survivants_emprisonnes) >= nombre_total_survivants:
        defaite_declenchee = True
        if player_role == 'Survivor':
            msg_fin = Text(
                text="DÉFAITE...\nVous avez tous été emprisonnés !",
                origin=(0, 0),
                scale=2.5,
                color=color.red,
                background=True
            )
        else:
            msg_fin = Text(
                text="VICTOIRE !\nTous les survivants sont emprisonnés !",
                origin=(0, 0),
                scale=2.5,
                color=color.green,
                background=True
            )
        invoke(declencher_retour_menu, delay=4.0)

def update_hp_ui():
    ratio = player_hp / MAX_HP
    hp_text.text = f'HP: {player_hp}'
    if ratio > 0.5:
        hp_text.color = color.lime
    elif ratio > 0.25:
        hp_text.color = color.orange
    else:
        hp_text.color = color.red


# ATTAQUE

ATTACK_DAMAGE   = 10
ATTACK_RANGE    = 3.0
ATTACK_WIDTH    = 2.0
ATTACK_HEIGHT   = 3.0
ATTACK_COOLDOWN = 0.6
_attack_timer   = 0.0

def do_attack():
    global _attack_timer, _attack_anim_timer, _is_attack_anim
    if player_role is None or not ROLES[player_role]["can_attack"]:
        return
    if _attack_timer > 0 or is_dead:
        return
    _attack_timer = ATTACK_COOLDOWN
    _is_attack_anim = True
    _attack_anim_timer = 0.0
   

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

    hit_someone = False

    for pid, ghost in list(ghost_entities.items()):
        delta  = ghost.position - joueur.position
        f_dist = delta.dot(forward)
        s_dist = abs(delta.dot(right))
        h_dist = abs((ghost.position.y + 1.5) - (joueur.position.y + 1.5))

        if (0 < f_dist <= ATTACK_RANGE) and (s_dist <= ATTACK_WIDTH * 0.5) and (h_dist <= ATTACK_HEIGHT * 0.5):
            hit_someone = True
            ghost_hp[pid] = max(0, ghost_hp.get(pid, MAX_HP) - ATTACK_DAMAGE)
            print(f"[ATTACK] HIT sur {pid} ! HP restant : {ghost_hp[pid]}")

            if ghost_hp[pid] <= 0:
                print(f"[ATTACK] Ghost {pid} est mort !")
                destroy(ghost_entities.pop(pid))
                ghost_hp.pop(pid, None)
            else:
                parts = ghost_parts.get(pid)
                if parts:
                    for k in ('corps', 'tete', 'bras_g', 'bras_d', 'jambe_g', 'jambe_d'):
                        part = parts.get(k)
                        if part is None:
                            continue
                        part.color = color.red
                        invoke(setattr, part, 'color', color.white, delay=0.15)

            if network.connected:
                network.send_damage(pid, ATTACK_DAMAGE)





# STAMINA

max_stamina = 100
current_stamina = max_stamina
stamina_drain_rate = 25
stamina_regen_rate = 15
sprint_speed_multiplier = 2.0
base_speed = 6.7


# UI

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


# UI — ANNONCE DU RÔLE

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


# UI — ÉCRAN DE CONNEXION AU SERVEUR (démarrage)

connection_screen_root = Entity(parent=camera.ui, enabled=True, z=-0.5)

connection_screen_bg = Entity(
    parent=connection_screen_root,
    model='quad',
    color=color.rgba(0, 0, 0, 0),
    scale=(3, 2),
    z=0.1
)

connection_screen_title = Text(
    parent=connection_screen_root,
    text='CONNEXION',
    origin=(0, 0),
    position=(0, 0.10),
    scale=3,
    color=color.rgba(180, 180, 180, 0),
    font='VeraMono.ttf'
)

connection_screen_status = Text(
    parent=connection_screen_root,
    text='',
    origin=(0, 0),
    position=(0, -0.02),
    scale=2,
    color=color.rgba(80, 220, 100, 0),
    font='VeraMono.ttf'
)

connection_screen_sub = Text(
    parent=connection_screen_root,
    text='',
    origin=(0, 0),
    position=(0, -0.14),
    scale=1.4,
    color=color.rgba(120, 120, 120, 0),
    font='VeraMono.ttf'
)

if connection_ok:
    connection_screen_status.text = 'Serveur connecté'
    connection_screen_sub.text    = 'Mode multijoueur'
    _connection_status_rgb        = (80, 220, 100)
else:
    connection_screen_status.text = 'Connexion échouée'
    connection_screen_sub.text    = 'Mode solo'
    _connection_status_rgb        = (220, 50, 50)


# Indicateur de rôle permanent (coin haut droit)
role_indicator = Text(
    text='',
    position=(0.62, 0.44),
    scale=1.2,
    parent=camera.ui,
    color=color.white
)


# UI — OVERLAY D'AIDE

help_overlay_root = Entity(parent=camera.ui, enabled=False, z=-0.6)

# Fond plein écran assombri
Entity(
    parent=help_overlay_root,
    model='quad',
    color=color.rgba(0, 0, 0, 0.82),
    scale=(2, 1),
    z=0.1,
)

# Panneau central
Entity(
    parent=help_overlay_root,
    model='quad',
    color=color.rgb32(28, 28, 36),
    scale=(1.05, 0.86),
    z=0.05,
)

help_title = Text(
    parent=help_overlay_root,
    text='AIDE  —  COMMANDES',
    origin=(0, 0),
    position=(0, 0.35),
    scale=1.8,
    color=color.white,
    font='VeraMono.ttf',
)

help_body = Text(
    parent=help_overlay_root,
    text='',
    origin=(-0.5, 0),
    position=(-0.35, 0.03),
    scale=1.1,
    color=color.rgb32(220, 220, 220),
    font='VeraMono.ttf',
)

help_objective = Text(
    parent=help_overlay_root,
    text='',
    origin=(0, 0),
    position=(0, -0.30),
    scale=1.0,
    color=color.rgb32(120, 200, 255),
    font='VeraMono.ttf',
)

help_footer = Text(
    parent=help_overlay_root,
    text='Appuyez sur  H  pour fermer',
    origin=(0, 0),
    position=(0, -0.38),
    scale=1.0,
    color=color.yellow,
    font='VeraMono.ttf',
)

# Indicateur permanent pour faire découvrir l'overlay
help_hint = Text(
    text='[H] Aide',
    position=(0, -0.47),
    origin=(0, 0),
    scale=1.0,
    parent=camera.ui,
    color=color.rgba(1, 1, 1, 0.6),
)


def build_help_text():
    """Génère le contenu de l'overlay d'aide à partir des touches courantes."""
    noms_affichage = {
        'space': 'Espace',
        'left shift': 'Maj gauche',
        'right shift': 'Maj droite',
        'left control': 'Ctrl gauche',
        'right control': 'Ctrl droite',
        'enter': 'Entrée',
    }

    # Inverse du mapping AZERTY -> Ursina appliqué par Menu.py au moment
    # de la sauvegarde : on retrouve le libellé physique de la touche
    # qu'aperçoit l'utilisateur sur un clavier AZERTY.
    ursina_to_azerty = {
        'q': 'a',
        'a': 'q',
        'w': 'z',
        'z': 'w',
        ';': 'm',
        'up arrow': 'up',
        'down arrow': 'down',
        'left arrow': 'left',
        'right arrow': 'right',
    }

    def libelle_touche(t):
        t = ursina_to_azerty.get(t, t)
        return noms_affichage.get(t, t.upper())

    lignes = [
        ('Avancer',   libelle_touche(touches['Move Forward'])),
        ('Reculer',   libelle_touche(touches['Move Backward'])),
        ('Gauche',    libelle_touche(touches['Move Left'])),
        ('Droite',    libelle_touche(touches['Move Right'])),
        ('Sauter',    libelle_touche(touches['Jump'])),
        ('Sprint',    libelle_touche(touches['Sprint'])),
        ('Interagir', libelle_touche(touches['Interact'])),
        ('Attaquer',  'Clic gauche'),
        ('Aide',      'H'),
        ('Plein écran','F11'),
        ('Pause',     'Échap'),
    ]
    help_body.text = '\n'.join(
        f"{nom.ljust(12)} :  {touche}" for nom, touche in lignes
    )

    if player_role and player_role in ROLES:
        help_objective.text = (
            f"Objectif ({player_role}) : {ROLES[player_role]['description']}"
        )
    else:
        help_objective.text = (
            "Objectif : Survivants, trouvez les sorties.  "
            "Infectés, éliminez les survivants."
        )


def toggle_help():
    """Affiche ou masque l'overlay d'aide."""
    if not help_overlay_root.enabled:
        build_help_text()
        help_overlay_root.enabled = True
        mouse.locked = False
        mouse.visible = True
    else:
        help_overlay_root.enabled = False
        if not is_dead and not pause_overlay_root.enabled:
            mouse.locked = True
            mouse.visible = False


# UI — MENU PAUSE

pause_overlay_root = Entity(parent=camera.ui, enabled=False, z=-0.7)

Entity(
    parent=pause_overlay_root,
    model='quad',
    color=color.rgba(0, 0, 0, 0.82),
    scale=(2, 1),
    z=0.1,
)

Entity(
    parent=pause_overlay_root,
    model='quad',
    color=color.rgb32(28, 28, 36),
    scale=(0.65, 0.7),
    z=0.05,
)

Text(
    parent=pause_overlay_root,
    text='PAUSE',
    origin=(0, 0),
    position=(0, 0.22),
    scale=2.2,
    color=color.white,
    font='VeraMono.ttf',
)


def quitter_jeu():
    network.disconnect()
    application.quit()


def toggle_pause():
    """Affiche ou masque le menu pause et gère la souris."""
    pause_overlay_root.enabled = not pause_overlay_root.enabled
    if pause_overlay_root.enabled:
        mouse.locked = False
        mouse.visible = True
    elif not is_dead and not help_overlay_root.enabled:
        mouse.locked = True
        mouse.visible = False


def ouvrir_aide_depuis_pause():
    pause_overlay_root.enabled = False
    if not help_overlay_root.enabled:
        build_help_text()
        help_overlay_root.enabled = True
    mouse.locked = False
    mouse.visible = True


Button(
    parent=pause_overlay_root,
    text='Reprendre',
    text_color=color.black,
    position=(0, 0.05),
    scale=(0.36, 0.08),
    color=color.rgba(180, 180, 180, 0.95),
    highlight_color=color.rgba(220, 220, 220, 1),
    pressed_color=color.rgba(140, 140, 140, 1),
    on_click=toggle_pause,
)

Button(
    parent=pause_overlay_root,
    text='Aide',
    text_color=color.black,
    position=(0, -0.06),
    scale=(0.36, 0.08),
    color=color.rgba(180, 180, 180, 0.95),
    highlight_color=color.rgba(220, 220, 220, 1),
    pressed_color=color.rgba(140, 140, 140, 1),
    on_click=ouvrir_aide_depuis_pause,
)

Button(
    parent=pause_overlay_root,
    text='Quitter',
    text_color=color.black,
    position=(0, -0.17),
    scale=(0.36, 0.08),
    color=color.rgba(140, 0, 0, 0.95),
    highlight_color=color.rgba(200, 30, 30, 1),
    pressed_color=color.rgba(80, 0, 0, 1),
    on_click=quitter_jeu,
)



# CAMÉRA & JOUEUR

mouse.locked = True
mouse.visible = False

camera_pivot = Entity(parent=joueur, y=2)
camera.parent = camera_pivot
camera.fov = 90
camera.rotation = (15, 0, 0)

def mouvement_camera():
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

    vertical_velocity += gravity * time.dt
    joueur.y += vertical_velocity * time.dt

    col_info = raycast(
        joueur.position + Vec3(0, 0.1, 0), 
        Vec3(0, -1, 0),
        distance=1.5,
        ignore=[joueur]
    )

    if col_info and col_info.hit:
        ground_y = col_info.world_point.y

        if joueur.y <= ground_y + 0.6:
            joueur.y = ground_y + 0.5  
            vertical_velocity = 0
            is_jumping = False
            on_ground = True
        else:
            on_ground = False
    else:
        on_ground = False

    if joueur.y < -50:
        joueur.position = (15, 3, 0)
        vertical_velocity = 0
        on_ground = True
        is_jumping = False


def mouvement_joueur():
    global current_stamina, _footstep_timer

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

    # Gestion dynamique du rythme et type des bruits de pas (SFX)
    if is_moving and on_ground:
        _footstep_timer += time.dt
        # L'Infected ou le sprint réduit l'intervalle entre les pas (rythme plus rapide)
        step_interval = 0.25 if is_sprinting else 0.45
        if player_role == "Infected":
            step_interval *= 0.85 # Rythme légèrement plus frénétique pour le monstre

        if _footstep_timer >= step_interval:
            _footstep_timer = 0.0
            # Sélection du type de pas selon le rôle
            sound_type = 'pas_infected' if player_role == "Infected" else 'pas_survivor'
            vol = 0.4 if is_sprinting else 0.3
            play_sfx(sound_type, volume=vol)
    else:
        _footstep_timer = 0.0

    if not is_moving:
        AUDIO_GAME['pas_survivor'].stop()
        AUDIO_GAME['pas_infected'].stop()
        
    avance = Vec3(camera_pivot.forward.x, 0, camera_pivot.forward.z) * held_keys[touches['Move Forward']]
    recule = Vec3(camera_pivot.forward.x, 0, camera_pivot.forward.z) * -held_keys[touches['Move Backward']]
    droite = Vec3(camera_pivot.right.x,   0, camera_pivot.right.z  ) * held_keys[touches['Move Right']]
    gauche = Vec3(camera_pivot.right.x,   0, camera_pivot.right.z  ) * -held_keys[touches['Move Left']]
    move_vec = avance + recule + droite + gauche

    if move_vec.length_squared() > 0:
        direction = move_vec.normalized()
        move = direction * time.dt * current_speed
        right = Vec3(direction.z, 0, -direction.x) 

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
                if normal.y < 0.7:  
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
        texture=img_path,
        scale=(camera.aspect_ratio * 2, 2),
        position=(0, 0),
        parent=camera.ui,
        z=-1
    )

    # Lecture stable via le Mixeur Pygame
    try:
        pygame_sound = pygame.mixer.Sound(res(snd_path))
        pygame_sound.play()
    except Exception as e:
        print(f"[SCREAMER ERROR] Erreur audio Pygame : {e}")

    destroy(overlay, delay=1.15)


def input(key):
    global is_jumping, vertical_velocity, rectangle_visible, on_ground, _local_ready

    # Touches du lobby : actives uniquement pendant l'attente des rôles serveur,
    # quand on est réellement connecté au serveur (sinon le mode solo offline
    # gère tout via son timer).
    if key in ('r', 'f'):
        print(f"[LOBBY-DBG] touche={key!r} active={_connection_screen_active} "
              f"phase={_connection_phase} connected={getattr(network, 'connected', False)}")
    if (_connection_screen_active and _connection_phase == 1
            and getattr(network, 'connected', False)):
        if key == 'r':
            _local_ready = not _local_ready
            print(f"[LOBBY-DBG] _local_ready -> {_local_ready}")
            if hasattr(network, 'send_ready'):
                network.send_ready(_local_ready)
            return
        if key == 'f':
            print("[LOBBY-DBG] envoi force_start")
            if hasattr(network, 'send_force_start'):
                network.send_force_start()
            return

    if key == 'p':
        print(f"[POS] x={round(joueur.x, 2)}, y={round(joueur.y, 2)}, z={round(joueur.z, 2)}")

    if key == 'escape':
        if enigme.is_open or enigme_plomberie.is_open or enigme_signalisation.is_open:
            enigme.handle_input(key)
            enigme_plomberie.handle_input(key)
            enigme_signalisation.handle_input(key)
            return
        if help_overlay_root.enabled:
            toggle_help()
        else:
            toggle_pause()

    if key == 'h':
        toggle_help()

    if key == 'f11':
        from panda3d.core import WindowProperties
        wp = WindowProperties()
        currently_full = bool(application.base.win.getProperties().getFullscreen())
        new_full = not currently_full
        wp.setFullscreen(new_full)
        if new_full:
            try:
                mon = window.main_monitor
                wp.setSize(int(mon.width), int(mon.height))
            except Exception:
                pass
        else:
            wp.setSize(1280, 720)
        application.base.win.requestProperties(wp)

    if key == touches['Jump'] and on_ground and not is_dead:
        is_jumping = True
        vertical_velocity = jump_force

    if key == touches['Interact']:
        dist = distance(joueur.position, cube_proche.position)
        dist_s = distance(joueur.position, cube_screamer.position)

        if dist <= distance_interaction:
            rectangle_visible = not rectangle_visible
            rectangle_ui.enabled = rectangle_visible

        if dist_s <= distance_interaction:
            img, snd = random.choice(screamer_list)
            screamer_data = img + "|" + snd
            
            play_screamer(screamer_data)

        if enigme.can_interact(joueur.position, cube_electrique.position):
            enigme.open()
        enigme.handle_input(key) 

        if enigme_plomberie.can_interact(joueur.position, cube_vanne.position):
            enigme_plomberie.open()
        enigme_plomberie.handle_input(key)

        if enigme_signalisation.can_interact(joueur.position, cube_panneau.position):
            enigme_signalisation.open()
        enigme_signalisation.handle_input(key)

        if cube_screamer1.visible and distance(joueur.position, cube_screamer1.position) < 3.5:
            cube_screamer1.visible = False
            cube_screamer1.collider = None

            img, snd = random.choice(screamer_list)
            screamer_data = img + "|" + snd

            play_screamer(screamer_data)
            
        if cube_screamer2.visible and distance(joueur.position, cube_screamer2.position) < 3.5:
            cube_screamer2.visible = False
            cube_screamer2.collider = None

            img, snd = random.choice(screamer_list)
            screamer_data = img + "|" + snd

            play_screamer(screamer_data)

    if key == 'left mouse down':
        do_attack()

    if key == 't':
        print("[DEBUG] Test dégâts forcé")
        receive_damage(999)

    if key == 'k':
        for mur in mur_cylindre:
            mur.visible = not mur.visible

tasks_placees = False

def update():
    global tasks_placees, navigo_task, rectangle_visible, _send_timer, _son_timer, _attack_timer, _invincibility_timer, _death_timer
    global _heartbeat_playing, _breath_playing, _whisper_timer, _anim_timer, _attack_anim_timer, _is_attack_anim
    global mur_victoire, mur_cree


    enigme.update()
    enigme_signalisation.update()
    enigme_plomberie.update()

    update_connection_screen()

    if calcul_termine and player_role is not None and not tasks_placees:
        
        # 1. On déplace les cubes simples
        cube_vanne.position      = _pos_vanne
        cube_electrique.position = _pos_electrique
        cube_panneau.position    = _pos_panneau
        if _pos_screamer1 is not None and _pos_screamer2 is not None:
            cube_screamer1.position  = _pos_screamer1
            cube_screamer2.position  = _pos_screamer2
        
        navigo_task = NavigoTask(
            player=joueur,
            position=_pos_navigo,
            on_complete=valider_une_tache,
            interaction_key=touches['Interact'],
        )
        
        # 3. Masquage pour l'Infecté
        if player_role == "Infected":
            cube_vanne.visible = False
            cube_vanne.collider = None
            cube_electrique.visible = False
            cube_electrique.collider = None
            cube_panneau.visible = False
            cube_panneau.collider = None

            cube_screamer1.visible = False
            cube_screamer1.collider = None
            cube_screamer2.visible = False
            cube_screamer2.collider = None
            
            if hasattr(navigo_task, 'visible'):
                navigo_task.visible = False
            for attr in ['entity', 'model', 'cube', 'borne']:
                if hasattr(navigo_task, attr) and getattr(navigo_task, attr):
                    obj = getattr(navigo_task, attr)
                    obj.visible = False
                    obj.collider = None
                    
            print("[GAME] Infecté : Tâches masquées correctement.")
        else:
            print("[GAME] Survivant : Tâches visibles et en place.")
            
        tasks_placees = True


    if enigme.is_open or enigme_signalisation.is_open or enigme_plomberie.is_open:
        return
    
    if navigo_task:
        if hasattr(navigo_task, 'update'):
            navigo_task.update()
        elif navigo_task.is_open:
            return
        
    mouvement_joueur()
    mouvement_camera()
    saut()

    # Cooldown attaque
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

        sync_roles_from_server()

        _send_timer += time.dt
        if _send_timer >= SEND_INTERVAL:
            _send_timer = 0
            _is_moving_now = (held_keys[touches['Move Forward']] or held_keys[touches['Move Backward']]
                              or held_keys[touches['Move Left']] or held_keys[touches['Move Right']])
            _is_sprinting_now = held_keys[touches['Sprint']] and _is_moving_now
            network.send_position(
                joueur.x, joueur.y, joueur.z, joueur.rotation_y,
                mv=int(_is_moving_now),
                sp=int(_is_sprinting_now),
                atk=int(_is_attack_anim),
                at=round(_anim_timer, 2),
            )

        update_ghosts(network.get_other_players())
    else:
        network_text.text = 'Réseau: déconnecté'
        network_text.color = color.red


    
    # Heartbeat (Battements de cœur si hp < 30%)
    if player_hp <= 30 and not is_dead:
        if not _heartbeat_playing:
            channel_heartbeat.play(AUDIO_GAME['heartbeat'], loops=-1)
            channel_heartbeat.set_volume(0.8)
            _heartbeat_playing = True
    else:
        if _heartbeat_playing:
            channel_heartbeat.stop()
            _heartbeat_playing = False

    # Infected Breathing 
    if player_role == "Infected" and not is_dead:
        if not _breath_playing:
            channel_infected_breath.play(AUDIO_GAME['rale_infected'], loops=-1)
            channel_infected_breath.set_volume(0.2)
            _breath_playing = True
    else:
        if _breath_playing:
            channel_infected_breath.stop()
            _breath_playing = False

    # Distant Whispers
    _whisper_timer -= time.dt
    if _whisper_timer <= 0 and not is_dead:
        son_aleatoire = random.choice(['chuchotement', 'haunted'])
        play_sfx(son_aleatoire, volume=0.2)
        _whisper_timer = random.uniform(20.0, 50.0)

    _son_timer -= time.dt
    if _son_timer <= 0:
        channel_ambiance.play(AUDIO_GAME['ambiance'])
        channel_ambiance.set_volume(0.5)
        _son_timer = random.uniform(60, 120)

    
    # Rôle : animation d'annonce + indicateur
    update_role_announce()
    update_role_indicator()

    # IA Embuscadeur
    update_embuscadeur()

    # ── Animation personnage ──

    is_moving = (held_keys[touches['Move Forward']] or held_keys[touches['Move Backward']]
                 or held_keys[touches['Move Left']] or held_keys[touches['Move Right']])
    is_sprinting = held_keys[touches['Sprint']] and is_moving

    anim_speed = 12 if is_sprinting else 7

    if is_moving and on_ground and not _is_attack_anim:
        _anim_timer += time.dt * anim_speed

        joueur_jambe_g.rotation_x =  math.sin(_anim_timer) * 6
        joueur_jambe_d.rotation_x = -math.sin(_anim_timer) * 6
        joueur_bras_g.rotation_x  = -math.sin(_anim_timer) * 5
        joueur_bras_d.rotation_x  =  math.sin(_anim_timer) * 5
        joueur_model.y             =  math.sin(_anim_timer * 2) * 0.01
        joueur_corps.rotation_z    =  math.sin(_anim_timer) * 0.5

    elif not _is_attack_anim:
        _anim_timer += time.dt * 1.5
        joueur_jambe_g.rotation_x = lerp(joueur_jambe_g.rotation_x, 0, time.dt * 8)
        joueur_jambe_d.rotation_x = lerp(joueur_jambe_d.rotation_x, 0, time.dt * 8)
        joueur_bras_g.rotation_x  = lerp(joueur_bras_g.rotation_x,  0, time.dt * 8)
        joueur_bras_d.rotation_x  = lerp(joueur_bras_d.rotation_x,  0, time.dt * 8)
        joueur_corps.rotation_z   = lerp(joueur_corps.rotation_z,   0, time.dt * 8)
        joueur_corps.y = math.sin(_anim_timer) * 0.021
        joueur_tete.y  = math.sin(_anim_timer) * 0.019
        joueur_bras_g.y = math.sin(_anim_timer) * 0.019
        joueur_bras_d.y = math.sin(_anim_timer) * 0.019
        joueur_jambe_g.y =  math.sin(_anim_timer) * 0.014
        joueur_jambe_d.y = math.sin(_anim_timer) * 0.014

    if _is_attack_anim:
        _attack_anim_timer += time.dt * 14

        t = math.sin(_attack_anim_timer)

        # Les deux bras vers l'avant
        joueur_bras_g.rotation_x = -t * 45
        joueur_bras_d.rotation_x = -t * 45

        # Corps et tête légèrement vers l'avant
        joueur_corps.rotation_x = t * 10
        joueur_tete.rotation_x  = t * 8

        if _attack_anim_timer >= math.pi:
            _is_attack_anim = False
            _attack_anim_timer = 0.0
            joueur_bras_g.rotation_x = 0
            joueur_bras_d.rotation_x = 0
            joueur_corps.rotation_x  = 0
            joueur_tete.rotation_x   = 0
        
    for msg in network.get_game_events():
        if msg['type'] == 'survivant_fini':
            id_joueur = msg['id']
            survivants_ayant_fini.add(id_joueur)
            print(f"[RESEAU] Le joueur {id_joueur} a fini ses tâches !")
        elif msg['type'] == 'survivant_emprisonne':
            survivants_en_prison.add(msg['id'])
            print(f"[PRISON] Joueur {msg['id']} emprisonné")
        elif msg['type'] == 'liberer_joueur':
            if msg.get('target_id') == str(network.my_id):
                respawn_player()
                print("[PRISON] Tu as été libéré !")
            survivants_en_prison.discard(msg.get('target_id'))

    if not mur_cree and player_role == 'Survivor':
        nombre_total_survivants = sum(1 for r in all_assigned_roles.values() if r == 'Survivor')
        if nombre_total_survivants == 0:
            nombre_total_survivants = 1

        if len(survivants_ayant_fini) >= nombre_total_survivants:
            print("--- TOUTES LES TÂCHES SONT REUSSITES ! ---")
            mur_victoire = Entity(
                model='cube',
                color=color.green,
                alpha=0.4,
                position=(56.4, 2.97, 0.28),
                scale=(0.5, 32.0, 22.68),
                collider=None
            )
            mur_cree = True
            print("[GAME] Le mur vert de la victoire est apparu ! Fuyez !")

    global victoire_declenchee
    if mur_cree and not victoire_declenchee:
        # On vérifie si le joueur est proche du mur (X proche de 56.4)
        # Et s'il est bien situé sur la longueur du mur (Z entre -11.5 et 12.0)
        if abs(joueur.x - 56.4) < 1.3 and -11.5 <= joueur.z <= 12.0:
            victoire_declenchee = True
            print("[VICTOIRE] Vous avez traversé le mur !")
            
            # 1. Message de victoire
            Text(
                text="VICTOIRE ! Vous vous êtes échappés du Châtelet !",
                origin=(0, 0),
                scale=2.3,
                color=color.green,
                background=True
            )
            
            # 2. Retour au menu après un délai de 4 secondes
            invoke(declencher_retour_menu, delay=4.0)
        
    update_liberation()



        



# ATTRIBUTION DES RÔLES AU DÉMARRAGE
# assign_role() est appelé par update_connection_screen() une fois
# l'écran de connexion disparu, pour éviter le chevauchement des deux écrans.

Five_nights_at_chatelet.run()
