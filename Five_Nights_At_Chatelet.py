from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.shaders import lit_with_shadows_shader


#pip install ursina on oublie pas tu connais

Five_nights_at_chatelet = Ursina()

def input(key):
    if key == 'escape':
        application.quit()

sun = DirectionalLight()
sun.look_at(Vec3(1, -1, -1))
#sun.color = color.rgb(0.04,0.04,0.04)
sun.color = color.rgb(1,1,1)
sun.shadows = True 

test_cube = Entity(
    model='cube',
    color=color.azure,
    position=(2,1,2),
    shader=lit_with_shadows_shader
)

sol = Entity(
    model="Mall.obj",
    collider="mesh",
    shader=lit_with_shadows_shader,
    scale=Vec3(1,3,1)
)


Five_nights_at_chatelet.run()
