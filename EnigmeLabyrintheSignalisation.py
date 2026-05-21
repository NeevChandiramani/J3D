"""
EnigmeLabyrintheSignalisation.py
─────────────────────────────────────────────────────────────────────────────
Mini-jeu "Labyrinthe des Lignes" — style Wiring d'Among Us, version RATP.
Association par clics successifs (gauche = ligne, droite = terminus).
Aucun drag-and-drop.

INTÉGRATION dans Five_Nights_At_Chatelet.py :
─────────────────────────────────────────────
    from EnigmeLabyrintheSignalisation import EnigmeLabyrintheSignalisation

    cube_panneau = Entity(
        model='cube', color=color.blue,
        position=(X, Y, Z),
        collider='box', shader=lit_with_shadows_shader
    )

    def signalisation_restauree():
        print("[GAME] Signalisation restaurée !")

    enigme_signalisation = EnigmeLabyrintheSignalisation(
        on_success=signalisation_restauree
    )

Dans input(key) :
    if key == touches['Interact']:
        if enigme_signalisation.can_interact(joueur.position, cube_panneau.position):
            enigme_signalisation.open()
        enigme_signalisation.handle_input(key)

Dans update() :
    enigme_signalisation.update()
    if enigme_signalisation.is_open:
        return   # bloque les mouvements pendant l'énigme
─────────────────────────────────────────────────────────────────────────────
"""

from ursina import (
    Entity, Button, Text, camera, color, mouse,
    destroy, invoke, time, Vec3
)
import random


# ── Couleurs (rgb32 pour éviter les rectangles blancs Ursina) ──────────────

C_BG            = color.rgba32(10,  12,  20,  210)   # fond semi-transparent
C_TITRE         = color.rgba32(220, 220, 240, 255)
C_LIGNE_NORMAL  = color.rgba32(40,  60,  110, 230)
C_TERM_NORMAL   = color.rgba32(60,  35,  90,  230)
C_SELECTED      = color.rgba32(200, 160, 20,  255)   # jaune sélection
C_SUCCESS       = color.rgba32(30,  160, 60,  255)   # vert validé
C_ERROR         = color.rgba32(180, 30,  30,  255)   # rouge erreur
C_HL_LIGNE      = color.rgba32(70,  100, 180, 255)
C_HL_TERM       = color.rgba32(100, 60,  150, 255)
C_PRESS         = color.rgba32(20,  20,  50,  255)
C_TEXTE_BTN     = color.rgba32(235, 235, 255, 255)
C_TEXTE_VALIDE  = color.rgba32(255, 255, 255, 255)
C_SUCCES_MSG    = color.rgba32(80,  220, 120, 255)
C_TITRE_PANEL   = color.rgba32(180, 200, 255, 255)


class EnigmeLabyrintheSignalisation:
    """
    Énigme d'association Ligne ↔ Terminus, UI 2D Ursina, 4 paires.
    """

    # Correspondances correctes  {ligne: terminus}
    SOLUTIONS = {
        "Ligne 1":  "La Défense",
        "Ligne 4":  "Bagneux",
        "Ligne 14": "Aéroport CDG",
        "RER A":    "Marne-la-Vallée",
    }

    INTERACTION_DISTANCE = 4.0

    def __init__(self, on_success=None):
        self.on_success   = on_success
        self.is_open      = False
        self._validated   = set()        # lignes déjà correctement associées
        self._selected    = None         # ligne en attente d'un terminus
        self._error_timer = 0.0          # durée restante du flash rouge
        self._error_btns  = []           # boutons à flasher
        self._success_shown = False      # message final affiché

        # ── Listes ordonnées (terminus mélangé à chaque ouverture) ────────
        self._lignes  = list(self.SOLUTIONS.keys())
        self._termini = list(self.SOLUTIONS.values())

        # ── Racine UI ─────────────────────────────────────────────────────
        self._root = Entity(parent=camera.ui, enabled=False)

        # Fond semi-transparent
        self._bg = Entity(
            parent=self._root,
            model='quad',
            color=C_BG,
            scale=(1.0, 0.72),
            z=0.1
        )

        # Titre du panneau
        self._titre = Text(
            parent=self._root,
            text="⚡ LABYRINTHE DES LIGNES",
            origin=(0, 0),
            position=(0, 0.30),
            scale=1.35,
            color=C_TITRE_PANEL,
        )

        self._sous_titre = Text(
            parent=self._root,
            text="Cliquez sur une LIGNE, puis sur son TERMINUS",
            origin=(0, 0),
            position=(0, 0.23),
            scale=0.75,
            color=C_TITRE,
        )

        # Labels colonnes
        Text(parent=self._root, text="LIGNES", origin=(0,0),
             position=(-0.30, 0.17), scale=0.8,
             color=color.rgba32(150, 180, 255, 200))
        Text(parent=self._root, text="TERMINUS", origin=(0,0),
             position=(0.30, 0.17), scale=0.8,
             color=color.rgba32(200, 150, 255, 200))

        # Message succès (caché par défaut)
        self._msg_succes = Text(
            parent=self._root,
            text="✔  SIGNALISATION RESTAURÉE",
            origin=(0, 0),
            position=(0, -0.30),
            scale=1.5,
            color=C_SUCCES_MSG,
            enabled=False,
        )

        # Bouton fermeture (ESC)
        self._btn_close = Button(
            parent=self._root,
            text="✕  FERMER  [ESC]",
            position=(0, -0.38),
            scale=(0.30, 0.055),
            color=color.rgba32(60, 60, 80, 200),
            highlight_color=color.rgba32(100, 100, 130, 255),
            pressed_color=color.rgba32(30, 30, 50, 255),
            text_color=color.rgba32(200, 200, 220, 255),
            on_click=self.close,
            z=-0.05
        )

        # Dicts  {label: Button}
        self._btns_lignes  = {}
        self._btns_termini = {}
        self._build_buttons()

    # ──────────────────────────────────────────────────────────────────────
    # Construction des boutons
    # ──────────────────────────────────────────────────────────────────────

    def _build_buttons(self):
        """Crée (ou recrée) les 4+4 boutons de l'UI."""
        # Nettoyage si rebuild
        for b in list(self._btns_lignes.values()) + list(self._btns_termini.values()):
            destroy(b)
        self._btns_lignes.clear()
        self._btns_termini.clear()

        N = len(self._lignes)
        spacing = 0.095
        y_start = 0.10

        for i, ligne in enumerate(self._lignes):
            y = y_start - i * spacing
            btn = Button(
                parent=self._root,
                text=ligne,
                position=(-0.30, y),
                scale=(0.26, 0.075),
                color=C_LIGNE_NORMAL,
                highlight_color=C_HL_LIGNE,
                pressed_color=C_PRESS,
                text_color=C_TEXTE_BTN,
                on_click=lambda l=ligne: self._click_ligne(l),
                z=-0.05
            )
            self._btns_lignes[ligne] = btn

        for i, terminus in enumerate(self._termini):
            y = y_start - i * spacing
            btn = Button(
                parent=self._root,
                text=terminus,
                position=(0.30, y),
                scale=(0.26, 0.075),
                color=C_TERM_NORMAL,
                highlight_color=C_HL_TERM,
                pressed_color=C_PRESS,
                text_color=C_TEXTE_BTN,
                on_click=lambda t=terminus: self._click_terminus(t),
                z=-0.05
            )
            self._btns_termini[terminus] = btn

    # ──────────────────────────────────────────────────────────────────────
    # Logique de clics
    # ──────────────────────────────────────────────────────────────────────

    def _click_ligne(self, ligne):
        if ligne in self._validated:
            return                           # déjà validé, ignoré
        self._deselect_all_lignes()
        self._selected = ligne
        btn = self._btns_lignes[ligne]
        btn.color = C_SELECTED

    def _click_terminus(self, terminus):
        if self._selected is None:
            return                           # aucune ligne sélectionnée

        ligne = self._selected
        # Terminus déjà validé → ignoré
        if terminus in [self.SOLUTIONS[l] for l in self._validated]:
            return

        # ── Bonne association ──
        if self.SOLUTIONS.get(ligne) == terminus:
            self._validated.add(ligne)
            self._selected = None

            bl = self._btns_lignes[ligne]
            bt = self._btns_termini[terminus]
            for b in (bl, bt):
                b.color           = C_SUCCESS
                b.highlight_color = C_SUCCESS
                b.pressed_color   = C_SUCCESS
                b.text_color      = C_TEXTE_VALIDE
                b.on_click        = lambda: None    # désactivation douce

            if len(self._validated) == len(self.SOLUTIONS):
                self._on_all_validated()

        # ── Mauvaise association ──
        else:
            bl = self._btns_lignes[ligne]
            bt = self._btns_termini[terminus]
            self._error_btns  = [bl, bt]
            self._error_timer = 0.55
            for b in (bl, bt):
                b.color = C_ERROR
            self._selected = None

    def _deselect_all_lignes(self):
        for l, btn in self._btns_lignes.items():
            if l not in self._validated:
                btn.color = C_LIGNE_NORMAL

    # ──────────────────────────────────────────────────────────────────────
    # Succès global
    # ──────────────────────────────────────────────────────────────────────

    def _on_all_validated(self):
        self._success_shown = True
        self._msg_succes.enabled = True
        self._btn_close.text = "✔  FERMER"
        # Fermeture automatique après 2.2 s
        invoke(self.close, delay=2.2)

    # ──────────────────────────────────────────────────────────────────────
    # Ouverture / fermeture
    # ──────────────────────────────────────────────────────────────────────

    def open(self):
        if self.is_open:
            return
        # Mélanger les terminus à chaque ouverture (sauf si déjà commencé)
        if not self._validated:
            random.shuffle(self._termini)
            self._build_buttons()

        self.is_open       = True
        self._root.enabled = True
        mouse.locked       = False
        mouse.visible      = True

    def close(self):
        self.is_open       = False
        self._root.enabled = False
        mouse.locked       = True
        mouse.visible      = False

        if self._success_shown and self.on_success:
            self.on_success()

    # ──────────────────────────────────────────────────────────────────────
    # Update (appeler depuis le update() principal)
    # ──────────────────────────────────────────────────────────────────────

    def update(self):
        # Flash rouge → retour couleur normale
        if self._error_timer > 0:
            self._error_timer -= time.dt
            if self._error_timer <= 0:
                for b in self._error_btns:
                    # Identifier si c'est une ligne ou un terminus
                    for l, bl in self._btns_lignes.items():
                        if b is bl and l not in self._validated:
                            b.color = C_LIGNE_NORMAL
                    for t, bt in self._btns_termini.items():
                        if b is bt and t not in [self.SOLUTIONS[l] for l in self._validated]:
                            b.color = C_TERM_NORMAL
                self._error_btns = []

    # ──────────────────────────────────────────────────────────────────────
    # Helpers pour le script principal
    # ──────────────────────────────────────────────────────────────────────

    def can_interact(self, player_pos: Vec3, object_pos: Vec3) -> bool:
        """Renvoie True si le joueur est assez proche du panneau."""
        return (player_pos - object_pos).length() <= self.INTERACTION_DISTANCE

    def handle_input(self, key: str):
        """Ferme l'UI sur Échap si elle est ouverte."""
        if self.is_open and key == 'escape':
            self.close()
