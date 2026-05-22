from ursina import *
import math

# ──────────────────────────────────────────────
# ENIGME PLOMBERIE  —  Five Nights at Châtelet
# ──────────────────────────────────────────────
# Intégration dans ton main :
#
#   from enigme_plomberie import EnigmePlomberie
#   enigme = EnigmePlomberie(on_success=ma_fonction_callback)
#
#   # Ajouter dans input() :
#   enigme.handle_input(key)
#
#   # Ajouter dans update() :
#   enigme.update()
#
#   # Déclencher depuis la touche 'e' :
#   if enigme.can_interact(joueur.position, cube_vanne.position):
#       enigme.open()
# ──────────────────────────────────────────────

INTERACT_RANGE   = 3.0
REQUIRED_SUCCESS = 3       # succès consécutifs pour valider
BASE_SPEED       = 0.45    # vitesse de départ de l'aiguille (unités/s, 0→1)
SPEED_PENALTY    = 0.12    # accélération sur chaque échec
MAX_SPEED        = 1.6     # vitesse plafond
ZONE_START       = 0.35    # début zone verte (0 = haut, 1 = bas)
ZONE_END         = 0.55    # fin zone verte
AUTO_CLOSE_DELAY = 2.2     # délai fermeture auto après victoire (secondes)


class EnigmePlomberie:
    """
    Mini-jeu de timing 2D pour Ursina.

    L'aiguille oscille automatiquement de haut en bas dans une jauge.
    Le joueur doit cliquer sur le bouton PURGER quand l'aiguille
    est dans la zone verte. 3 succès consécutifs = victoire.
    Un échec retire un succès et accélère l'aiguille.
    """

    def __init__(self, on_success=None):
        self.on_success  = on_success
        self.is_open     = False
        self.solved      = False

        # État interne
        self._needle_pos = 0.0      # 0.0 (haut) → 1.0 (bas)
        self._needle_dir = 1        # +1 descend, -1 monte
        self._speed      = BASE_SPEED
        self._successes  = 0
        self._close_timer = 0.0
        self._flash_timer = 0.0     # durée du flash couleur aiguille
        self._flash_color = None    # color.lime ou color.red

        self._build_ui()
        self._set_visible(False)

    # ──────────────────────────────────────────
    # API publique
    # ──────────────────────────────────────────

    def can_interact(self, player_pos, cube_pos):
        return distance(player_pos, cube_pos) <= INTERACT_RANGE

    def open(self):
        if self.is_open:
            return
        self._reset_state()
        self.is_open = True
        self._set_visible(True)
        mouse.locked  = False
        mouse.visible = True

    def close(self):
        if not self.is_open:
            return
        self.is_open = False
        self._set_visible(False)
        mouse.locked  = True
        mouse.visible = False

    def handle_input(self, key):
        """Appelle depuis le input() de ton main."""
        if not self.is_open or self.solved:
            return
        if key == 'escape':
            self.close()

    def update(self):
        """Appelle depuis le update() de ton main."""
        if not self.is_open:
            return

        # Timer fermeture automatique post-victoire
        if self._close_timer > 0:
            self._close_timer -= time.dt
            if self._close_timer <= 0:
                self.close()
            return

        if self.solved:
            return

        # Mouvement de l'aiguille
        self._needle_pos += self._needle_dir * self._speed * time.dt
        if self._needle_pos >= 1.0:
            self._needle_pos = 1.0
            self._needle_dir = -1
        elif self._needle_pos <= 0.0:
            self._needle_pos = 0.0
            self._needle_dir = 1

        self._update_needle_visual()

        # Flash couleur aiguille
        if self._flash_timer > 0:
            self._flash_timer -= time.dt
            if self._flash_timer <= 0:
                self._needle_bar.color = color.rgba32(220, 210, 170, 255)

        # Mise à jour barre de vitesse
        self._update_speed_bar()

    # ──────────────────────────────────────────
    # Logique interne
    # ──────────────────────────────────────────

    def _reset_state(self):
        self.solved       = False
        self._needle_pos  = 0.0
        self._needle_dir  = 1
        self._speed       = BASE_SPEED
        self._successes   = 0
        self._close_timer = 0.0
        self._flash_timer = 0.0
        self._status_text.text  = ''
        self._purge_btn.disabled = False
        self._refresh_dots()
        self._update_speed_bar()

    def _in_zone(self):
        return ZONE_START <= self._needle_pos <= ZONE_END

    def _on_purge_click(self):
        if self.solved or not self.is_open:
            return

        if self._in_zone():
            self._successes += 1
            self._flash(success=True)
            self._refresh_dots()
            if self._successes >= REQUIRED_SUCCESS:
                self._on_win()
            else:
                self._status_text.text  = 'PARFAIT !'
                self._status_text.color = color.rgba32(40, 200, 80, 255)
                invoke(self._clear_status, delay=0.6)
        else:
            self._successes = max(0, self._successes - 1)
            self._speed     = min(MAX_SPEED, self._speed + SPEED_PENALTY)
            self._flash(success=False)
            self._refresh_dots()
            self._status_text.text  = 'HORS ZONE !'
            self._status_text.color = color.rgba32(200, 40, 30, 255)
            invoke(self._clear_status, delay=0.7)

    def _on_win(self):
        self.solved = True
        self._purge_btn.disabled = True
        self._status_text.text  = 'PURGE EFFECTUÉE'
        self._status_text.color = color.rgba32(40, 255, 100, 255)
        self._needle_bar.color  = color.rgba32(40, 255, 100, 255)
        self._close_timer = AUTO_CLOSE_DELAY
        if callable(self.on_success):
            self.on_success()

    def _flash(self, success):
        self._needle_bar.color = color.lime if success else color.red
        self._flash_timer = 0.25

    def _clear_status(self):
        if not self.solved:
            self._status_text.text = ''

    # ──────────────────────────────────────────
    # Construction UI
    # ──────────────────────────────────────────

    # ── Palette de couleurs (rgba32) ──
    _C_BG        = color.rgba32(  8,  14,  10, 220)
    _C_BORDER    = color.rgba32( 20,  60,  30, 200)
    _C_PANEL     = color.rgba32( 12,  22,  14, 230)
    _C_GAUGE_BG  = color.rgba32( 10,  22,  12, 255)
    _C_ZONE      = color.rgba32( 15, 100,  35, 140)
    _C_ZONE_BDR  = color.rgba32( 20, 150,  50, 200)
    _C_NEEDLE    = color.rgba32(220, 210, 170, 255)
    _C_DOT_OFF   = color.rgba32( 15,  50,  20, 255)
    _C_DOT_ON    = color.rgba32( 20, 140,  50, 255)
    _C_SPBAR_BG  = color.rgba32( 10,  25,  12, 255)
    _C_SPBAR     = color.rgba32(140,  70,  10, 255)
    _C_BTN       = color.rgba32( 10,  45,  20, 220)
    _C_BTN_H     = color.rgba32( 20,  80,  35, 220)
    _C_TITLE     = color.rgba32(120, 200, 140, 255)
    _C_LABEL     = color.rgba32( 60, 130,  80, 255)

    # ── Dimensions de la jauge ──
    GAUGE_W   = 0.045   # largeur en unités UI
    GAUGE_H   = 0.45    # hauteur en unités UI
    NEEDLE_H  = 0.012
    DOT_SIZE  = 0.022

    def _build_ui(self):
        self._root = Entity(parent=camera.ui)

        # Fond + bordure
        Entity(parent=self._root, model='quad', color=self._C_BORDER,
               scale=(0.55, 0.72), position=(0, 0), z=0.52)
        Entity(parent=self._root, model='quad', color=self._C_BG,
               scale=(0.53, 0.70), position=(0, 0), z=0.50)

        # Titres
        Text(parent=self._root, text='VANNE DE PURGE B2',
             position=(0, 0.325), scale=1.1, color=self._C_TITLE,
             origin=(0, 0), font='VeraMono.ttf')
        Text(parent=self._root, text='CHÂTELET — ÉGOUTS NIV.-3',
             position=(0, 0.285), scale=0.75, color=self._C_LABEL,
             origin=(0, 0), font='VeraMono.ttf')

        # ── Jauge (fond) ──
        gauge_x = -0.12
        gauge_y = 0.02
        Entity(parent=self._root, model='quad', color=self._C_GAUGE_BG,
               scale=(self.GAUGE_W, self.GAUGE_H),
               position=(gauge_x, gauge_y), z=0.40)

        # ── Zone verte ──
        zone_h     = (ZONE_END - ZONE_START) * self.GAUGE_H
        zone_cy    = gauge_y + self.GAUGE_H * 0.5 - ZONE_START * self.GAUGE_H - zone_h * 0.5
        self._zone = Entity(parent=self._root, model='quad', color=self._C_ZONE,
                            scale=(self.GAUGE_W, zone_h),
                            position=(gauge_x, zone_cy), z=0.39)
        # Bordures de la zone verte (haut + bas)
        Entity(parent=self._root, model='quad', color=self._C_ZONE_BDR,
               scale=(self.GAUGE_W, 0.003),
               position=(gauge_x, zone_cy + zone_h * 0.5), z=0.38)
        Entity(parent=self._root, model='quad', color=self._C_ZONE_BDR,
               scale=(self.GAUGE_W, 0.003),
               position=(gauge_x, zone_cy - zone_h * 0.5), z=0.38)

        # ── Aiguille ──
        self._needle_bar = Entity(
            parent=self._root, model='quad', color=self._C_NEEDLE,
            scale=(self.GAUGE_W * 0.82, self.NEEDLE_H),
            position=(gauge_x, gauge_y + self.GAUGE_H * 0.5),
            z=0.37
        )
        self._gauge_top = gauge_y + self.GAUGE_H * 0.5
        self._gauge_bot = gauge_y - self.GAUGE_H * 0.5

        # ── Labels jauge ──
        for label, pct in [('MAX', 0.0), ('MID', 0.5), ('MIN', 1.0)]:
            y = self._gauge_top - pct * self.GAUGE_H
            Text(parent=self._root, text=label,
                 position=(gauge_x + self.GAUGE_W * 0.5 + 0.025, y),
                 scale=0.65, color=self._C_LABEL,
                 origin=(-0.5, 0), font='VeraMono.ttf')

        # ── Dots de succès ──
        info_x = 0.08
        Text(parent=self._root, text='SUCCÈS',
             position=(info_x, 0.18), scale=0.7, color=self._C_LABEL,
             origin=(0, 0), font='VeraMono.ttf')

        self._dots = []
        dot_spacing = 0.038
        dots_start  = info_x - dot_spacing
        for i in range(REQUIRED_SUCCESS):
            d = Entity(parent=self._root, model='circle', color=self._C_DOT_OFF,
                       scale=self.DOT_SIZE,
                       position=(dots_start + i * dot_spacing, 0.14),
                       z=0.38)
            self._dots.append(d)

        # ── Barre de vitesse ──
        Text(parent=self._root, text='PRESSION',
             position=(info_x, 0.08), scale=0.7, color=self._C_LABEL,
             origin=(0, 0), font='VeraMono.ttf')

        sp_w, sp_h = 0.18, 0.018
        Entity(parent=self._root, model='quad', color=self._C_SPBAR_BG,
               scale=(sp_w, sp_h), position=(info_x, 0.05), z=0.40)
        self._speed_bar = Entity(parent=self._root, model='quad', color=self._C_SPBAR,
                                 scale=(0.001, sp_h),
                                 position=(info_x - sp_w * 0.5, 0.05), z=0.39)
        self._sp_w     = sp_w
        self._sp_left  = info_x - sp_w * 0.5

        # ── Texte de statut ──
        self._status_text = Text(
            parent=self._root, text='',
            position=(0, -0.21), scale=1.1,
            color=color.rgba32(40, 200, 80, 255),
            origin=(0, 0), font='VeraMono.ttf'
        )

        # ── Bouton PURGER ──
        self._purge_btn = Button(
            parent=self._root,
            text='PURGER / ARRÊT',
            text_color=color.rgba32(80, 200, 110, 255),
            color=self._C_BTN,
            highlight_color=self._C_BTN_H,
            pressed_color=color.rgba32(5, 25, 12, 220),
            scale=(0.42, 0.07),
            position=(0, -0.275),
            on_click=self._on_purge_click,
            font='VeraMono.ttf'
        )
        self._purge_btn.text_entity.scale *= 0.9

        # ── Bouton Fermer ──
        self._close_btn = Button(
            parent=self._root,
            text='FERMER',
            text_color=self._C_LABEL,
            color=color.rgba32(8, 22, 12, 180),
            highlight_color=color.rgba32(15, 40, 20, 200),
            pressed_color=color.rgba32(4, 12, 6, 200),
            scale=(0.26, 0.05),
            position=(0, -0.345),
            on_click=self.close,
            font='VeraMono.ttf'
        )
        self._close_btn.text_entity.scale *= 0.8

    def _set_visible(self, v):
        self._root.enabled = v

    def _update_needle_visual(self):
        """Positionne l'aiguille selon _needle_pos (0=haut, 1=bas)."""
        y = self._gauge_top - self._needle_pos * self.GAUGE_H
        self._needle_bar.y = y

    def _refresh_dots(self):
        for i, d in enumerate(self._dots):
            d.color = self._C_DOT_ON if i < self._successes else self._C_DOT_OFF

    def _update_speed_bar(self):
        ratio = (self._speed - BASE_SPEED) / (MAX_SPEED - BASE_SPEED)
        ratio = max(0.0, min(1.0, ratio))
        bar_w = max(0.001, ratio * self._sp_w)
        self._speed_bar.scale_x = bar_w
        self._speed_bar.x = self._sp_left + bar_w * 0.5
