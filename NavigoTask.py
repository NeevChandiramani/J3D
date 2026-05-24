"""
NavigoTask.py — Mini-jeu "Swipe Pass Navigo" style Among Us
Compatible Ursina Engine (pip install ursina)

INTÉGRATION DANS TON PROJET :
    from NavigoTask import NavigoTask

    # Dans ton init, passe la référence à ton entité joueur :
    navigo_task = NavigoTask(player=joueur, position=(x, y, z))

    # Chaque frame dans ton update() principal :
    navigo_task.update()

    # Pour bloquer le mouvement du joueur, vérifie :
    if navigo_task.is_open:
        return  # ou skip ton mouvement_joueur()

    # Pour savoir si la tâche est réussie :
    if navigo_task.completed:
        # fait ce que tu veux (ouvrir une porte, etc.)
        navigo_task.completed = False  # reset si tu veux rejouer

    # Callback optionnel à la complétion :
    navigo_task = NavigoTask(player=joueur, on_complete=ma_fonction)
"""

from ursina import *
import time as _time


# ─────────────────────────────────────────────────────────
# CONSTANTES DE GAMEPLAY — modifie ces valeurs pour régler
# la difficulté du swipe
# ─────────────────────────────────────────────────────────
SWIPE_MIN_DURATION = 0.4   # secondes — en dessous = trop rapide
SWIPE_MAX_DURATION = 1.8   # secondes — au dessus  = trop lent
INTERACTION_DISTANCE = 3.5 # unités Ursina
CLOSE_DELAY = 1.2          # délai avant fermeture après succès (s)


class NavigoTask:
    """
    Mini-jeu de swipe de carte Navigo.

    Paramètres
    ----------
    player      : Entity — référence à ton entité joueur (pour la détection de distance)
    position    : tuple  — position (x, y, z) du boîtier dans le monde 3D
    on_complete : callable | None — fonction appelée sans argument à la réussite
    interaction_key : str — touche d'interaction (default 'e')
    """

    def __init__(self, player: Entity, position=(0, 1, 0),
                 on_complete=None, interaction_key='e'):

        self.player           = player
        self.on_complete      = on_complete
        self.interaction_key  = interaction_key
        self.is_open          = False   # True quand l'UI est ouverte
        self.completed        = False   # passe à True après un swipe réussi

        # ── état interne du swipe ──
        self._swipe_start_time = None   # timestamp quand la carte commence à bouger
        self._is_swiping       = False
        self._close_timer      = 0.0
        self._closing          = False
        self._card_start_x     = None   # position X de départ de la carte

        # ── entité 3D dans le monde (le boîtier de validation) ──
        self._world_entity = Entity(
            model='cube',
            color=color.rgb32(40, 40, 55),
            position=position,
            scale=(0.25, 0.4, 0.08),
            collider='box',
        )
        # Petit écran LED sur le boîtier
        self._world_screen = Entity(
            parent=self._world_entity,
            model='quad',
            color=color.rgb32(10, 200, 80),
            scale=(0.6, 0.3),
            position=(0, 0.2, -0.52),   # face avant du cube
        )
        # Logo RATP stylisé (simple texte)
        self._world_label = Text(
            parent=self._world_entity,
            text='NAVIGO',
            scale=3,
            position=(0, -0.1, -0.52),
            origin=(0, 0),
            color=color.white,
            billboard=False,
        )

        # ── UI 2D ──
        self._build_ui()

    # ─────────────────────────────────────────────────────────
    # CONSTRUCTION DE L'INTERFACE 2D
    # ─────────────────────────────────────────────────────────
    def _build_ui(self):
        """Crée tous les éléments de l'interface 2D (camera.ui)."""

        # Conteneur racine — désactivé par défaut
        self.ui_root = Entity(parent=camera.ui, enabled=False)

        # Fond semi-transparent
        Entity(
            parent=self.ui_root,
            model='quad',
            color=color.rgba32(0, 0, 0, 183),
            scale=(2, 1),
            z=0.2,
        )

        # ── Boîtier RATP (rectangle gris central) ──
        boitier = Entity(
            parent=self.ui_root,
            model='quad',
            color=color.rgb32(55, 55, 68),
            scale=(0.55, 0.38),
            position=(0, 0),
            z=0.1,
        )

        # Bordure colorée RATP (liseré rouge/bleu)
        Entity(
            parent=self.ui_root,
            model='quad',
            color=color.rgb32(210, 30, 40),
            scale=(0.56, 0.005),
            position=(0, 0.195),
            z=0.09,
        )
        Entity(
            parent=self.ui_root,
            model='quad',
            color=color.rgb32(0, 70, 160),
            scale=(0.56, 0.005),
            position=(0, -0.195),
            z=0.09,
        )

        # ── Mini écran LCD sur le boîtier ──
        self._screen_bg = Entity(
            parent=self.ui_root,
            model='quad',
            color=color.rgb32(20, 30, 20),
            scale=(0.35, 0.09),
            position=(0, 0.1),
            z=0.08,
        )
        self._screen_text = Text(
            parent=self.ui_root,
            text='SWIPE YOUR PASS',
            color=color.rgb32(100, 230, 100),
            scale=0.9,
            position=(0, 0.1),
            origin=(0, 0),
            z=0.07,
        )

        # ── Glissière (le lecteur de carte physique) ──
        # Fond de la glissière
        Entity(
            parent=self.ui_root,
            model='quad',
            color=color.rgb32(30, 30, 40),
            scale=(0.44, 0.055),
            position=(0, -0.02),
            z=0.08,
        )
        # Trait guide central
        Entity(
            parent=self.ui_root,
            model='quad',
            color=color.rgb32(60, 60, 80),
            scale=(0.44, 0.008),
            position=(0, -0.02),
            z=0.075,
        )

        # Marqueurs gauche / droite
        Text(
            parent=self.ui_root,
            text='◄',
            color=color.rgb32(180, 180, 200),
            scale=0.8,
            position=(-0.215, -0.02),
            origin=(0, 0),
            z=0.07,
        )
        Text(
            parent=self.ui_root,
            text='►',
            color=color.rgb32(180, 180, 200),
            scale=0.8,
            position=(0.215, -0.02),
            origin=(0, 0),
            z=0.07,
        )

        # ── Carte Navigo (l'élément à glisser) ──
        # Limites horizontales de la glissière en coordonnées UI
        self._card_x_min = -0.195   # bord gauche
        self._card_x_max =  0.195   # bord droit
        self._card_start_x = self._card_x_min

        self._card = Draggable(
            parent=self.ui_root,
            model='quad',
            color=color.rgba32(100, 220, 200, 114),   # violet Navigo
            scale=(0.09, 0.05),
            position=(self._card_x_min, -0.02),
            z=0.06,
        )
        # Hologramme sur la carte (petit quad clair)
        Entity(
            parent=self._card,
            model='quad',
            color=color.rgba32(100, 220, 200, 0.45),
            scale=(0.4, 0.5),
            position=(-0.2, 0.1),
            z=-0.01,
        )
        Text(
            parent=self._card,
            text='NAVIGO',
            color=color.white,
            scale=4,
            position=(0, 0),
            origin=(0, 0),
            z=-0.01,
        )

        # Instructions en bas du boîtier
        Text(
            parent=self.ui_root,
            text='Swipe your card →',
            color=color.rgb32(190, 190, 210),
            scale=0.8,
            position=(0, -0.135),
            origin=(0, 0),
            z=0.07,
        )

        # Bouton fermer (croix discrète en haut à droite)
        close_btn = Button(
            parent=self.ui_root,
            text='✕',
            color=color.rgba32(80, 80, 100, 178),
            highlight_color=color.rgba32(160, 40, 40, 229),
            scale=(0.04, 0.04),
            position=(0.285, 0.205),
            z=0.06,
            on_click=self.close,
        )

    # ─────────────────────────────────────────────────────────
    # BOUCLE PRINCIPALE — à appeler dans ton update() global
    # ─────────────────────────────────────────────────────────
    def update(self):
        """À appeler chaque frame depuis le update() principal d'Ursina."""

        # ── Timer de fermeture après succès ──
        if self._closing:
            self._close_timer -= time.dt
            if self._close_timer <= 0:
                self._closing = False
                self.close()
            return  # on ne traite plus rien pendant la fermeture

        # ── Détection d'interaction dans le monde 3D ──
        if not self.is_open:
            dist = distance(self.player.position, self._world_entity.position)
            if dist <= INTERACTION_DISTANCE and held_keys[self.interaction_key]:
                self.open()
            return

        # ── Logique de swipe ──
        self._process_swipe()

    # ─────────────────────────────────────────────────────────
    # LOGIQUE DE SWIPE
    # ─────────────────────────────────────────────────────────
    def _process_swipe(self):
        """Gère la physique/logique de la carte Navigo."""

        card = self._card

        # Contrainte : la carte ne peut bouger que sur l'axe X
        card.y = -0.02
        card.z =  0.06

        # Clampe la position X dans la glissière
        card.x = clamp(card.x, self._card_x_min, self._card_x_max)

        # Détecte le début du swipe (carte bougée depuis la gauche)
        card_moving = card.dragging  # True quand l'utilisateur clique et drag

        if card_moving and not self._is_swiping:
            # La carte commence à bouger
            if card.x <= self._card_x_min + 0.02:
                self._is_swiping = True
                self._swipe_start_time = _time.time()

        # Détecte que la carte a atteint le bord droit
        if self._is_swiping and card.x >= self._card_x_max - 0.01:
            elapsed = _time.time() - self._swipe_start_time
            self._evaluate_swipe(elapsed)

        # Si l'utilisateur relâche la carte sans atteindre le bord droit
        if self._is_swiping and not card_moving and card.x < self._card_x_max - 0.01:
            self._set_message('TRY AGAIN', color.rgb32(220, 150, 0))
            self._reset_card()

    def _evaluate_swipe(self, duration: float):
        """Évalue la vitesse du swipe et applique le résultat."""
        self._is_swiping = False

        if duration < SWIPE_MIN_DURATION:
            self._set_message('ERROR: TOO FAST', color.rgb32(220, 50, 50))
            self._reset_card()

        elif duration > SWIPE_MAX_DURATION:
            self._set_message('ERROR: TOO SLOW', color.rgb32(220, 50, 50))
            self._reset_card()

        else:
            # Succès !
            self._set_message('VALIDATED  ✓  THANKS', color.rgb32(60, 220, 100))
            self._screen_bg.color = color.rgb32(10, 50, 20)
            self._world_screen.color = color.rgb32(10, 220, 80)
            self.completed = True
            self._closing = True
            self._close_timer = CLOSE_DELAY
            if self.on_complete:
                self.on_complete()

    def _reset_card(self):
        """Remet la carte à gauche de la glissière."""
        self._card.x = self._card_x_min
        self._swipe_start_time = None

    def _set_message(self, msg: str, col):
        self._screen_text.text  = msg
        self._screen_text.color = col

    # ─────────────────────────────────────────────────────────
    # OUVERTURE / FERMETURE
    # ─────────────────────────────────────────────────────────
    def open(self):
        """Ouvre le mini-jeu."""
        if self.is_open:
            return
        self.is_open = True
        self._reset_card()
        self._set_message('SWIPE YOUR PASS', color.rgb32(100, 230, 100))
        self._screen_bg.color = color.rgb32(20, 30, 20)
        self.ui_root.enabled = True
        mouse.locked  = False
        mouse.visible = True

    def close(self):
        """Ferme le mini-jeu et rend le contrôle au joueur."""
        self.is_open  = False
        self._is_swiping = False
        self._closing    = False
        self._reset_card()
        self.ui_root.enabled = False
        mouse.locked  = True
        mouse.visible = False

    def destroy(self):
        """Nettoie toutes les entités (si tu supprimes la task en cours de partie)."""
        destroy(self._world_entity)
        destroy(self.ui_root)
