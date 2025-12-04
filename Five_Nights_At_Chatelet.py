from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.shaders import lit_with_shadows_shader


#pip install ursina on oublie pas tu connais

Five_nights_at_chatelet = Ursina()

def input(key):
    if key == 'escape':
        application.quit()



# --- Joueur ---
player = FirstPersonController(position=(0,10,0), mouse_sensitivity=Vec2(100,100))

sun = DirectionalLight()
sun.look_at(Vec3(1, -1, -1))
#sun.color = color.rgb(0.04,0.04,0.04)
sun.color = color.rgb(1,1,1)
sun.shadows = True 

# --- Cube test ---
test_cube = Entity(
    model='cube',
    color=color.azure,
    position=(2,1,2),
    shader=lit_with_shadows_shader
    
)


# --- Map ---
ground = Entity(
    model="Mall.obj",
    collider="mesh",
    shader=lit_with_shadows_shader,
    scale=1
)


Five_nights_at_chatelet.run()
