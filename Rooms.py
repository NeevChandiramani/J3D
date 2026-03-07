from ursina import *

class Rooms:

    salles = []

    def __init__(self, nom, position, taille):

        self.nom = nom

        self.zone = Entity(
            model='cube',
            position=position,
            scale=taille,
            collider='box',
            visible=False
        )

        Rooms.salles.append(self)

    @staticmethod  #Définir une méthode sans utiliser l'objet self
    def salle_du_joueur(joueur):

        for salle in Rooms.salles:
            if salle.zone.intersects(joueur).hit:
                return salle

        return None
