from ursina import *
#pip install ursina on oublie pas tu connais

Five_nights_at_chatelet = Ursina()

sol = Entity(
    model = 'plane',
    texture = 'shore',
    collider = 'box',
    scale = (50, 1, 50))

joueur = Entity(
    model = 'cube',    #Pour avoir d'autres model il faut télécharger des trucs sinon ça marche pas
    color = color.red,
    scale_y = 3,
    collider = 'box')


camera.parent = joueur
camera.position = (0, 2, -6)
camera.rotation_x = 15
camera.fov = 90
camera.clip_plane_near = 0.1
camera.clip_plane_far = 100

Five_nights_at_chatelet.run()
