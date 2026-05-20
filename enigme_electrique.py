from ursina import *
import random

# ──────────────────────────────────────────────
# ENIGME ELECTRIQUE  —  Five Nights at Châtelet
# ──────────────────────────────────────────────
# Intégration dans ton main :
#   from enigme_electrique import EnigmeElectrique
#   enigme = EnigmeElectrique(on_success=ma_fonction_callback)
#   # Dans input() ou update() de ton main :
#   enigme.handle_input(key)   # pour 'escape'
#   enigme.update()            # si tu veux le cooldown de fermeture
#
# Déclencher l'ouverture (depuis ta touche 'e') :
#   if enigme.can_interact(joueur.position, cube_electrique.position):
#       enigme.open()
# ──────────────────────────────────────────────

N_SWITCHES = 5
INTERACT_RANGE = 3.0


class EnigmeElectrique:
    """
    Puzzle d'interrupteurs 2D pour Ursina.

    Règle : cliquer sur l'interrupteur i inverse i-1, i, i+1.
    Victoire : tous les 5 sur ON (haut / vert).
    """

    def __init__(self, on_success=None):
        self.on_success = on_success        # callback appelé quand le puzzle est résolu
        self.is_open    = False
        self.solved     = False
        self._close_timer = 0.0             # délai avant fermeture auto après succès

        # ── État logique des interrupteurs ──
        self.states = [True] * N_SWITCHES   # sera mélangé à l'ouverture

        # ── Construction de l'UI ──
        self._build_ui()
        self._set_ui_visible(False)

    # ──────────────────────────────────────────
    # API publique
    # ──────────────────────────────────────────

    def can_interact(self, player_pos, cube_pos):
        return distance(player_pos, cube_pos) <= INTERACT_RANGE

    def open(self):
        if self.is_open:
            return
        self.is_open = True
        self.solved  = False
        self._randomize()
        self._refresh_buttons()
        self._set_ui_visible(True)
        self._status_text.text  = ''
        mouse.locked  = False
        mouse.visible = True

    def close(self):
        if not self.is_open:
            return
        self.is_open = False
        self._set_ui_visible(False)
        mouse.locked  = True
        mouse.visible = False

    def handle_input(self, key):
        """Appelle ça depuis le input() de ton main."""
        if self.is_open and key == 'escape':
            self.close()

    def update(self):
        """Appelle ça depuis le update() de ton main (pour le timer de fermeture)."""
        if self._close_timer > 0:
            self._close_timer -= time.dt
            if self._close_timer <= 0:
                self.close()

    # ──────────────────────────────────────────
    # Logique interne
    # ──────────────────────────────────────────

    def _randomize(self):
        """
        Génère un état aléatoire garanti résolvable et pas déjà gagné.
        Résolvabilité : on simule la stratégie gloutonne de gauche à droite.
        """
        for _ in range(1000):
            self.states = [random.choice([True, False]) for _ in range(N_SWITCHES)]
            if not all(self.states) and self._is_solvable():
                return
        # fallback : état connu résolvable (ex: tout OFF)
        self.states = [False] * N_SWITCHES

    def _is_solvable(self):
        """
        Vérifie si l'état courant est résolvable.
        Stratégie : on fixe chaque interrupteur de gauche à droite
        en cliquant sur i+1 si i est encore OFF.
        """
        a = list(self.states)
        for i in range(N_SWITCHES - 1):
            if not a[i]:
                # "cliquer" sur i+1
                for j in (i, i + 1, i + 2):
                    if 0 <= j < N_SWITCHES:
                        a[j] = not a[j]
        return all(a)

    def _toggle(self, index):
        if self.solved:
            return
        for j in (index - 1, index, index + 1):
            if 0 <= j < N_SWITCHES:
                self.states[j] = not self.states[j]
        self._refresh_buttons()
        if all(self.states):
            self._on_win()

    def _on_win(self):
        self.solved       = True
        self._status_text.text  = '[ CIRCUIT RÉTABLI ]'
        self._status_text.color = color.lime
        self._close_timer = 2.0          # fermeture automatique dans 2 s
        if callable(self.on_success):
            self.on_success()

    # ──────────────────────────────────────────
    # Construction de l'UI
    # ──────────────────────────────────────────

    # Couleurs
# ── Couleurs (Correction avec rgba32) ──
    _COL_BG        = color.rgba32( 10,  14,  20, 210)  # fond du panneau
    _COL_BORDER    = color.rgba32( 30,  80,  30, 200)  # bordure verte sombre
    _COL_ON        = color.rgba32( 20, 160,  20, 255)  # interrupteur ON  (vert)
    _COL_ON_H      = color.rgba32( 40, 200,  40, 255)  # ON hovered
    _COL_OFF       = color.rgba32(160,  20,  20, 255)  # interrupteur OFF (rouge)
    _COL_OFF_H     = color.rgba32(200,  40,  40, 255)  # OFF hovered
    _COL_LABEL     = color.rgba32(100, 180, 100, 255)  # texte secondaire
    _COL_TITLE     = color.rgba32(160, 220, 160, 255)  # titre panneau

    def _build_ui(self):
        # ── Conteneur racine (invisible, sert de parent) ──
        self._root = Entity(parent=camera.ui)

        # ── Fond semi-transparent ──
        self._bg = Entity(
            parent   = self._root,
            model    = 'quad',
            color    = self._COL_BG,
            scale    = (0.82, 0.52),
            position = (0, 0),
            z        = 0.5
        )

        # Bordure (entité légèrement plus grande, même position, z=0.51)
        self._border = Entity(
            parent   = self._root,
            model    = 'quad',
            color    = self._COL_BORDER,
            scale    = (0.84, 0.54),
            position = (0, 0),
            z        = 0.51
        )
        # On repasse le fond devant (z plus petit = devant en Ursina UI)
        self._bg.z = 0.49

        # ── Titres ──
        self._title = Text(
            parent   = self._root,
            text     = 'PANNEAU ÉLECTRIQUE',
            position = (0, 0.215),
            scale    = 1.4,
            color    = self._COL_TITLE,
            origin   = (0, 0),
            font     = 'VeraMono.ttf'
        )
        self._subtitle = Text(
            parent   = self._root,
            text     = 'mettre tous les circuits sur ON',
            position = (0, 0.165),
            scale    = 0.9,
            color    = self._COL_LABEL,
            origin   = (0, 0),
            font     = 'VeraMono.ttf'
        )

        # ── Interrupteurs ──
        self._buttons   = []
        self._btn_texts = []
        self._sw_labels = []

        sw_width  = 0.09
        sw_height = 0.16
        spacing   = 0.13
        total_w   = (N_SWITCHES - 1) * spacing
        start_x   = -total_w / 2

        for i in range(N_SWITCHES):
            x = start_x + i * spacing
            y = 0.01

            # Numéro de l'interrupteur (au-dessus)
            lbl = Text(
                parent   = self._root,
                text     = f'SW-{i + 1}',
                position = (x, y + sw_height / 2 + 0.025),
                scale    = 0.75,
                color    = self._COL_LABEL,
                origin   = (0, 0),
                font     = 'VeraMono.ttf'
            )

            # Bouton
            idx = i  # capture pour le lambda
            btn = Button(
                parent          = self._root,
                model           = 'quad',
                color           = self._COL_OFF,
                highlight_color = self._COL_OFF_H,
                pressed_color   = self._COL_OFF,
                scale           = (sw_width, sw_height),
                position        = (x, y),
                on_click        = lambda captured=idx: self._toggle(captured)
            )

            # Texte ON/OFF sur le bouton
            txt = Text(
                parent   = btn,
                text     = 'OFF',
                position = (0, 0),
                scale    = 8,
                color    = color.white,
                origin   = (0, 0),
                font     = 'VeraMono.ttf'
            )

            self._buttons.append(btn)
            self._btn_texts.append(txt)
            self._sw_labels.append(lbl)

        # ── Message de statut (succès / vide) ──
        self._status_text = Text(
            parent   = self._root,
            text     = '',
            position = (0, -0.16),
            scale    = 1.2,
            color    = color.lime,
            origin   = (0, 0),
            font     = 'VeraMono.ttf'
        )

        # ── Bouton Fermer ──
        self._close_btn = Button(
            parent          = self._root,
            text            = 'FERMER  [ESC]',
            text_color      = self._COL_LABEL,
            color           = color.rgba(15, 30, 15, 200),
            highlight_color = color.rgba(25, 60, 25, 220),
            pressed_color   = color.rgba(8,  20,  8, 220),
            scale           = (0.25, 0.055),
            position        = (0, -0.21),
            on_click        = self.close,
            font            = 'VeraMono.ttf'
        )
        self._close_btn.text_entity.scale *= 0.85

    def _set_ui_visible(self, visible):
        self._root.enabled = visible

    def _refresh_buttons(self):
        """Met à jour la couleur et le texte de chaque bouton selon self.states."""
        for i, btn in enumerate(self._buttons):
            on = self.states[i]
            btn.color           = self._COL_ON  if on else self._COL_OFF
            btn.highlight_color = self._COL_ON_H if on else self._COL_OFF_H
            self._btn_texts[i].text = 'ON ' if on else 'OFF'

# ══════════════════════════════════════════════
#  DÉMO STANDALONE  —  supprime ce bloc quand
#  tu intègres dans Five_Nights_At_Chatelet.py
# ══════════════════════════════════════════════
if __name__ == '__main__':
    app = Ursina()
    window.title = 'Énigme électrique — démo'
    mouse.locked  = False
    mouse.visible = True

    def on_win():
        print("[ENIGME] Puzzle résolu ! Callback déclenché.")

    enigme = EnigmeElectrique(on_success=on_win)
    enigme.open()

    def input(key):
        enigme.handle_input(key)

    def update():
        enigme.update()

    app.run()
