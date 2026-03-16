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

# Entités représentant les autres joueurs (fantômes réseau)
# {player_id: Entity}
ghost_entities = {}

SEND_INTERVAL = 0.05   # Envoyer la position toutes les 50ms
_send_timer = 0


def update_ghosts(other_players):
    """Crée, met à jour ou supprime les entités fantômes des autres joueurs."""
    # Supprimer les joueurs déconnectés
    for pid in list(ghost_entities.keys()):
        if pid not in other_players:
            destroy(ghost_entities.pop(pid))

    # Créer ou déplacer les joueurs existants
    for pid, pos in other_players.items():
        if pid not in ghost_entities:
            ghost_entities[pid] = Entity(
                model='ressources/Crackhead.obj',
                scale_y=3,
                color=color.red,   # Rouge pour distinguer les autres joueurs
                collider='box'
            )
        ghost_entities[pid].position = Vec3(pos["x"], pos["y"], pos["z"])


sol = Entity(
    model="ressources/Mall.obj",
    collider="mesh",
    shader=lit_with_shadows_shader,
    scale=Vec3(0.5,1.5,0.5)
)

sun = DirectionalLight()
sun.look_at(Vec3(1, -1, -1))
#sun.color = color.rgb(0.04,0.04,0.04)
sun.color = color.rgb(1,1,1)
sun.shadows = False

joueur = Entity(
    position= (15,3,0),
    model = 'ressources/Crackhead.obj',
    #color = color.red,
    scale_y = 3,
    collider = 'box'
)

test_cube = Entity(
    model='cube',
    color=color.azure,
    position=(2,1,2),
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


max_stamina = 100
current_stamina = max_stamina
stamina_drain_rate = 25 
stamina_regen_rate = 15  
sprint_speed_multiplier = 2.0
base_speed = 6.7

# Son ambiance gare (se déclenche aléatoirement toutes les 30-60 secondes)
son_gare = Audio('ressources/sounds/son_gare.mp3', autoplay=False)
_son_timer = random.uniform(30, 60)  # Premier déclenchement aléatoire

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

# Stamina UI (à modifier)
stamina_text = Text(
    text='Stamina: 100',
    position=(-0.8, -0.45),
    scale=1.5,
    parent=camera.ui,
    color=color.white
)

# Indicateur de connexion réseau
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

mouse.locked = True
mouse.visible = False 

camera_pivot = Entity(parent=joueur, y=2)
camera.parent = camera_pivot
camera.fov = 90
camera.rotation = (15, 0, 0)

# W.I.P C'est pas très fluide pour la rotation du perso
def mouvement_camera():
    camera_pivot.rotation_y += mouse.velocity[0] * 80
    camera_pivot.rotation_x -= mouse.velocity[1] * 80
    camera_pivot.rotation_x = clamp(camera_pivot.rotation_x, -30, 45)
    camera.position = (0, 0, -5)
    joueur.rotation = Vec3(0, camera_pivot.rotation_y, 0)

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
    
    is_moving = held_keys['w'] or held_keys['s'] or held_keys['a'] or held_keys['d']
    is_sprinting = held_keys['shift'] and current_stamina > 1 and is_moving

    if is_sprinting:
        current_stamina -= stamina_drain_rate * time.dt
        current_stamina = max(0, current_stamina)
        
        if current_stamina > 0:
            current_speed = base_speed * sprint_speed_multiplier
          
        else:
            current_speed = base_speed
          
    else:
        current_speed = base_speed
        
        if current_stamina < max_stamina:
            current_stamina += stamina_regen_rate * time.dt
            current_stamina = min(max_stamina, current_stamina)
    
    stamina_text.text = f'Stamina: {int(current_stamina)}'
    
    avance = Vec3(camera_pivot.forward.x, 0, camera_pivot.forward.z) * held_keys['w']
    recule = Vec3(camera_pivot.forward.x, 0, camera_pivot.forward.z) * -held_keys['s']
    droite = Vec3(camera_pivot.right.x, 0, camera_pivot.right.z) * held_keys['d']
    gauche = Vec3(camera_pivot.right.x, 0, camera_pivot.right.z) * -held_keys['a']
    move_vec = (avance + recule + droite + gauche)
  
    if move_vec.length_squared() > 0:
        direction = move_vec.normalized() * time.dt * current_speed
        new_pos = joueur.position + direction
        col_wall = raycast(joueur.position, direction.normalized(), distance=1.5, ignore=[joueur, sol])
      
        if not (col_wall and col_wall.hit):
            joueur.position = new_pos
          
    else:
        direction = Vec3(0,0,0)


def input(key):
    global is_jumping, vertical_velocity, rectangle_visible, on_ground
    
    if key == 'escape':
        network.disconnect()
        application.quit()
    
    if key == 'space' and on_ground:
        is_jumping = True
        vertical_velocity = jump_force
    
    if key == 'e':
        dist = distance(joueur.position, cube_proche.position)
        
        if dist <= distance_interaction:
            rectangle_visible = not rectangle_visible
            rectangle_ui.enabled = rectangle_visible
          

def update():
    mouvement_joueur()
    mouvement_camera()
    saut()
    
    global rectangle_visible, _send_timer, _son_timer
    dist = distance(joueur.position, cube_proche.position)
    
    if dist > distance_interaction and rectangle_visible:
        rectangle_visible = False
        rectangle_ui.enabled = False

#    salle_actuelle = Rooms.salle_du_joueur(joueur)

#    if salle_actuelle:
#      salle_ui.text = salle_actuelle.nom

    # ── Réseau ──
    if network.connected:
        network_text.text = f'Réseau: connecté ({len(ghost_entities)+1} joueur(s))'
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
        _son_timer = random.uniform(30, 60)  # Prochain déclenchement aléatoire


Five_nights_at_chatelet.run()
