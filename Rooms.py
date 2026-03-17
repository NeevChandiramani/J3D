from ursina import *

class Rooms:

    salles = []

    def __init__(self, nom, position, taille, etape):

        self.nom = nom
        self.etape = etape

        self.zone = Entity(
            model='cube',
            position=position,
            scale=taille,
            collider='box',
            visible=False
        )

        Rooms.salles.append(self)

    def choisir_salles_quete():
        """choisit une salle au hasard pour chaque étape (1, 2 et 3)"""
        salle_e1 = random.choice([s for s in Rooms.salles if s.etape == 1])
        salle_e2 = random.choice([s for s in Rooms.salles if s.etape == 2])
        salle_e3 = random.choice([s for s in Rooms.salles if s.etape == 3])
        return [salle_e1, salle_e2, salle_e3]

    @staticmethod  #Définir une méthode sans utiliser l'objet self
    def salle_du_joueur(joueur):

        for salle in Rooms.salles:
            if salle.zone.intersects(joueur).hit:
                return salle

        return None
