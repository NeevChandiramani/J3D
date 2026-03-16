#lignes à commenter pour désactiver le menu = -

from ursina import *
import pygame
import random
from ursina.shaders import lit_with_shadows_shader
from Rooms import Rooms
from NetworkClient import NetworkClient
#pip install ursina on oublie pas tu connais

import sys
                                                                                #-
try:                                                                            #-
    from Menu import run_menu                                                   #-
except Exception as e:                                                          #-
    run_menu = None                                                             #-
    print("Warning: impossible d'importer `Menu.run_menu()`: ", e)              #-

if run_menu:                                                                    #-
    result = run_menu()                                                         #-
    if result != 'start':                                                       #-
        sys.exit()                                                              #-

Five_nights_at_chatelet = Ursina()

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
ghost_hp = {}         # {player_id: int}  ← HP des autres joueurs (côté local)

SEND_INTERVAL = 0.05
_send_timer = 0


def update_ghosts(other_players):
    """Crée, met à jour ou supprime les entités fantômes des autres joueurs."""
    for pid in list(ghost_entities.keys()):
        if pid not in other_players:
            destroy(ghost_entities.pop(pid))
            ghost_hp.pop(pid, None)

    for pid, pos in other_players.items():
        if pid not in ghost_entities:
            ghost_entities[pid] = Entity(
                model='ressources/Crackhead.obj',
                scale_y=3,
                color=color.red,
                collider='box'
            )
            ghost_hp[pid] = MAX_HP  # HP plein à la création

        ghost_entities[pid].position = Vec3(pos["x"], pos["y"], pos["z"])

    # ── Récupérer les dégâts reçus depuis le réseau ──
    # NetworkClient doit implémenter get_damage_events() → liste de dicts {"amount": int}
    if hasattr(network, 'get_damage_events'):
        for event in network.get_damage_events():
            receive_damage(event.get("amount", 10))


# ──────────────────────────────────────────────
# MONDE
# ──────────────────────────────────────────────
sol = Entity(
    model="ressources/Mall.obj",
    collider="mesh",
    shader=lit_with_shadows_shader,
    scale=Vec3(0.5, 1.5, 0.5)
)

sun = DirectionalLight()
sun.look_at(Vec3(1, -1, -1))
sun.color = color.rgb(1, 1, 1)
sun.shadows = False

joueur = Entity(
    position=(15, 3, 0),
    collider='box',
    scale_y=3
)
joueur_model = Entity(
    parent=joueur,
    model='ressources/Perso.obj',
    rotation_y=180   # ← retourne uniquement le visuel
)

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
# HP
# ──────────────────────────────────────────────
MAX_HP = 100
player_hp = MAX_HP

INVINCIBILITY_DURATION = 0.5   # secondes d'invincibilité après un coup
_invincibility_timer = 0.0
is_dead = False

def receive_damage(amount):
    """Applique des dégâts au joueur local."""
    global player_hp, _invincibility_timer, is_dead
    if _invincibility_timer > 0 or is_dead:
        return
    player_hp -= amount
    player_hp = max(0, player_hp)
    _invincibility_timer = INVINCIBILITY_DURATION
    update_hp_ui()
    # Flash rouge de l'écran
    damage_flash.enabled = True
    invoke(setattr, damage_flash, 'enabled', False, delay=0.15)

    if player_hp <= 0:
        player_death()

def player_death():
    global is_dead, player_hp
    is_dead = True
    hp_text.text = 'HP: 0  —  MORT'
    hp_text.color = color.red
    # Respawn après 3 secondes
    invoke(respawn_player, delay=3)

def respawn_player():
    global is_dead, player_hp, _invincibility_timer
    is_dead = False
    player_hp = MAX_HP
    _invincibility_timer = 1.0  # courte invincibilité au respawn
    joueur.position = (15, 3, 0)
    hp_text.color = color.lime
    update_hp_ui()

def update_hp_ui():
    ratio = player_hp / MAX_HP
    hp_text.text = f'HP: {player_hp}'
    if ratio > 0.5:
        hp_text.color = color.lime
    elif ratio > 0.25:
        hp_text.color = color.orange
    else:
        hp_text.color = color.red
    # Barre de vie
    hp_bar_fill.scale_x = ratio * 0.3   # 0.3 = largeur max de la barre

# ──────────────────────────────────────────────
# ATTAQUE
# ──────────────────────────────────────────────
ATTACK_DAMAGE   = 10
ATTACK_RANGE    = 3.0    # profondeur de la hitbox (en unités)
ATTACK_WIDTH    = 2.0    # largeur de la hitbox carrée
ATTACK_HEIGHT   = 3.0    # hauteur de la hitbox
ATTACK_COOLDOWN = 0.6    # secondes entre deux coups
_attack_timer   = 0.0

def do_attack():
    """Déclenche une attaque : hitbox carrée devant le joueur."""
    global _attack_timer
    if _attack_timer > 0 or is_dead:
        return
    _attack_timer = ATTACK_COOLDOWN

    # Direction forward dans le plan horizontal
    forward = Vec3(camera_pivot.forward.x, 0, camera_pivot.forward.z).normalized()
    right   = Vec3(camera_pivot.right.x,   0, camera_pivot.right.z  ).normalized()

    # ── Feedback visuel : boîte semi-transparente ──
    center = joueur.position + Vec3(0, 1, 0) + forward * (ATTACK_RANGE * 0.5)
    hitbox_vis = Entity(
        model='cube',
        color=color.rgba(1, 0.1, 0.1, 0.35),
        position=center,
        rotation=joueur.rotation,
        scale=(ATTACK_WIDTH, ATTACK_HEIGHT, ATTACK_RANGE),
    )
    destroy(hitbox_vis, delay=0.12)

    # ── Détection des hits sur les fantômes ──
    for pid, ghost in ghost_entities.items():
        delta = ghost.position - joueur.position

        # Projection sur les axes forward / right / vertical
        f_dist = delta.dot(forward)
        s_dist = abs(delta.dot(right))
        h_dist = abs((ghost.position.y + 1.5) - (joueur.position.y + 1.5))

        in_range = (
            0 < f_dist <= ATTACK_RANGE
            and s_dist <= ATTACK_WIDTH  * 0.5
            and h_dist <= ATTACK_HEIGHT * 0.5
        )

        if in_range:
            # ── Côté local : déduire les HP du fantôme ──
            ghost_hp[pid] = max(0, ghost_hp.get(pid, MAX_HP) - ATTACK_DAMAGE)
            print(f"[ATTACK] Touché joueur {pid} → HP restants (local) : {ghost_hp[pid]}")

            # Flash blanc sur le fantôme touché
            ghost.color = color.white
            invoke(setattr, ghost, 'color', color.red, delay=0.15)

            # ── Réseau : envoyer les dégâts ──
            if hasattr(network, 'send_damage'):
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

# Son ambiance gare (se déclenche aléatoirement toutes les 30-60 secondes)
son_gare = Audio('ressources/sounds/son_gare.mp3', autoplay=False)
_son_timer = random.uniform(30, 60)

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

# ── Barre de vie (fond + remplissage) ──
hp_bar_bg = Entity(
    model='quad',
    color=color.dark_gray,
    scale=(0.305, 0.028),
    position=(-0.648, -0.38),
    parent=camera.ui
)
hp_bar_fill = Entity(
    model='quad',
    color=color.lime,
    scale=(0.3, 0.022),
    position=(-0.648, -0.38),
    parent=camera.ui
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
    text='[CLIC] Attaque',
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
    joueur.rotation_y      += mouse.velocity[0] * 80        # rotation horizontale sur le modèle
    camera_pivot.rotation_x -= mouse.velocity[1] * 80       # inclinaison verticale caméra seulement
    camera_pivot.rotation_x  = clamp(camera_pivot.rotation_x, -30, 45)
    camera_pivot.rotation_y  = 0                            # on force le pivot à rester droit
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
    col_info = raycast(joueur.position, Vec3(0, -1, 0), distance=2, ignore=[joueur])
    on_ground = col_info.hit if col_info else False
    if on_ground:
        joueur.y = max(joueur.y, col_info.world_point.y + 0.5)
        if vertical_velocity < 0:
            vertical_velocity = 0
            is_jumping = False
    if joueur.y < -50:
        joueur.position = (15, 3, 0)
        vertical_velocity = 0
        on_ground = True


def mouvement_joueur():
    global current_stamina
    if is_dead:
        return

    is_moving = held_keys['w'] or held_keys['s'] or held_keys['a'] or held_keys['d']
    is_sprinting = held_keys['shift'] and current_stamina > 1 and is_moving

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

    avance = Vec3(camera_pivot.forward.x, 0, camera_pivot.forward.z) *  held_keys['w']
    recule = Vec3(camera_pivot.forward.x, 0, camera_pivot.forward.z) * -held_keys['s']
    droite = Vec3(camera_pivot.right.x,   0, camera_pivot.right.z  ) *  held_keys['d']
    gauche = Vec3(camera_pivot.right.x,   0, camera_pivot.right.z  ) * -held_keys['a']
    move_vec = avance + recule + droite + gauche

    if move_vec.length_squared() > 0:
        direction = move_vec.normalized() * time.dt * current_speed
        new_pos = joueur.position + direction
        col_wall = raycast(joueur.position, direction.normalized(), distance=1.5, ignore=[joueur, sol])
        if not (col_wall and col_wall.hit):
            joueur.position = new_pos


def input(key):
    global is_jumping, vertical_velocity, rectangle_visible, on_ground

    if key == 'escape':
        network.disconnect()
        application.quit()

    if key == 'space' and on_ground and not is_dead:
        is_jumping = True
        vertical_velocity = jump_force

    if key == 'e':
        dist = distance(joueur.position, cube_proche.position)
        if dist <= distance_interaction:
            rectangle_visible = not rectangle_visible
            rectangle_ui.enabled = rectangle_visible

    # ── Attaque au clic gauche ──
    if key == 'left mouse down':
        do_attack()


def update():
    global rectangle_visible, _send_timer, _son_timer, _attack_timer, _invincibility_timer

    mouvement_joueur()
    mouvement_camera()
    saut()

    # ── Timers ──
    if _attack_timer > 0:
        _attack_timer -= time.dt
        # Feedback visuel : texte grisé pendant le cooldown
        ratio = max(0.0, _attack_timer / ATTACK_COOLDOWN)
        attack_indicator.color = lerp(color.white, color.dark_gray, ratio)

    if _invincibility_timer > 0:
        _invincibility_timer -= time.dt

    # ── Interaction cube ──
    dist = distance(joueur.position, cube_proche.position)
    if dist > distance_interaction and rectangle_visible:
        rectangle_visible = False
        rectangle_ui.enabled = False

#    salle_actuelle = Rooms.salle_du_joueur(joueur)
#    if salle_actuelle:
#      salle_ui.text = salle_actuelle.nom

    # ── Réseau ──
    if network.connected:
        network_text.text = f'Réseau: connecté ({len(ghost_entities) + 1} joueur(s))'
        network_text.color = color.lime

        _send_timer += time.dt
        if _send_timer >= SEND_INTERVAL:
            _send_timer = 0
            p = joueur.position
            network.send_position(p.x, p.y, p.z)

        update_ghosts(network.get_other_players())
    else:
        network_text.text = 'Réseau: déconnecté'
        network_text.color = color.red

    # ── Son ambiance aléatoire ──
    _son_timer -= time.dt
    if _son_timer <= 0:
        son_gare.play()
        _son_timer = random.uniform(30, 60)


Five_nights_at_chatelet.run()