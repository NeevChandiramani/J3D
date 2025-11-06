from ursina import *
#pip install ursina on oublie pas tu connais

Five_nights_at_chatelet = Ursina()

sol = Entity(
    model = 'plane',
    texture = 'shore',
    collider = 'box',
    scale = (50, 1, 50))

joueur = Entity(
    model = 'arrow',
    color = color.red,
    scale_y = 3,
    collider = 'box')

camera.parent = joueur
camera.position = (1, 1.5, 1)
camera.rotation = (1, 1, 1)

Five_nights_at_chatelet.run()
