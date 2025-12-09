from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.shaders import lit_with_shadows_shader


#pip install ursina on oublie pas tu connais

Five_nights_at_chatelet = Ursina()

sol = Entity(
    model="Mall.obj",
    collider="mesh",
    shader=lit_with_shadows_shader,
    scale=Vec3(1,3,1)
)

sun = DirectionalLight()
sun.look_at(Vec3(1, -1, -1))
#sun.color = color.rgb(0.04,0.04,0.04)
sun.color = color.rgb(1,1,1)
sun.shadows = False

joueur = Entity(
    position= (0,5,0),
    model = 'cube', 
    color = color.red,
    scale_y = 3,
    collider = 'box'
)

test_cube = Entity(
    model='cube',
    color=color.azure,
    position=(2,1,2),
    shader=lit_with_shadows_shader
)

mouse.locked = True
mouse.visible = False 

camera_pivot = Entity(parent=joueur, y=2)
camera.parent = camera_pivot
camera.fov = 90
camera.rotation = (15, 0, 0)

def mouvement_camera():
    camera_pivot.rotation_y += mouse.velocity[0] * 80
    camera_pivot.rotation_x -= mouse.velocity[1] * 80
    camera_pivot.rotation_x = clamp(camera_pivot.rotation_x, -30, 45)
    camera.position = (0, 0, -5)

def mouvement_joueur() :
    avance = Vec3(camera_pivot.forward.x, 0, camera_pivot.forward.z) * held_keys['w']
    recule = Vec3(camera_pivot.forward.x, 0, camera_pivot.forward.z) * -held_keys['s']
    droite = Vec3(camera_pivot.right.x, 0, camera_pivot.right.z) * held_keys['d']
    gauche = Vec3(camera_pivot.right.x, 0, camera_pivot.right.z) * -held_keys['a']   #touche de qwerty mais ça marche en azerty
    direction = (avance + recule + droite + gauche).normalized() * time.dt * 6.7
    joueur.position += direction

def input(key):
    if key == 'escape':
        application.quit()

def update():
    mouvement_joueur()
    mouvement_camera()

Five_nights_at_chatelet.run()
