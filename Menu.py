import pygame
import random
import sys
import os
import json

# configuration de base
WIDTH, HEIGHT = 1280, 720
FPS = 60
FONT_MAIN = "Courier New"
COLOR_BG = (5, 5, 10)
COLOR_TEXT = (140, 140, 140)
COLOR_SELECTED = (255, 255, 255)
COLOR_WAITING = (255, 100, 100) # pour indiquer l'attente d'une touche

# Chemin de base pour les ressources (compatibilité PyInstaller)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def res(path):
    return os.path.join(BASE_DIR, path)

def draw_fnaf_static(surface):
    """génère l'effet visuel de grain/neige pour l'immersion"""
    static_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for _ in range(4000):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        alpha = random.randint(10, 70)
        static_surf.set_at((x, y), (255, 255, 255, alpha))
    if random.random() < 0.1:
        for _ in range(5):
            h = random.randint(1, 3)
            y = random.randint(0, HEIGHT)
            pygame.draw.line(static_surf, (255, 255, 255, 30), (0, y), (WIDTH, y), h)
    surface.blit(static_surf, (0, 0))

def draw_scanlines(surface):
    """simule le "balayage" d'un écran ancien"""
    for y in range(0, HEIGHT, 3):
        pygame.draw.line(surface, (0, 0, 0, 100), (0, y), (WIDTH, y))

def glitch_offset(chance=0.04, power=8):
    """calcule un décalage aléatoire pour l'effet de glitch visuel"""
    if random.random() < chance:
        return random.randint(-power, power), random.randint(-2, 2)
    return 0, 0

class Menu:
    def __init__(self):
        # permet de switch entre l'écran principal et les paramètres
        self.state = "MAIN"
        self.main_options = ["START", "OPTIONS", "EXIT"]
        self.options = []
        self.selected_index = 0
        self.volume = 7

        # gestion des touches
        # touches par défaut
        self.keybinds = {
            'Avancer': pygame.K_z,
            'Reculer': pygame.K_s,
            'Gauche': pygame.K_q,
            'Droite': pygame.K_d,
            'Interagir': pygame.K_e,
            'Sauter': pygame.K_SPACE
        }
        self.bind_order = ['Avancer', 'Gauche', 'Reculer', 'Droite', 'Interagir', 'Sauter']
        self.waiting_for_key = None # indique si on attend une saisie de touche

        self.font_title = pygame.font.SysFont(FONT_MAIN, 90, bold=True)
        self.font_menu = pygame.font.SysFont(FONT_MAIN, 50, bold=True)
        self.font_small = pygame.font.SysFont(FONT_MAIN, 22)

        self.option_rects = []
        self.vol_rect = pygame.Rect(0, 0, 0, 0)
        self.align_x = 100
        self.last_vol_change = 0

        self.update_options_list()

    def update_options_list(self):
        """change les textes affichés selon l'état (main ou options)"""
        if self.state == "MAIN":
            self.options = self.main_options
        elif self.state == "OPTIONS":
            self.options = []
            for action in self.bind_order:
                if self.waiting_for_key == action:
                    self.options.append(f"{action} : [ APPUYEZ ]")
                else:
                    key_name = pygame.key.name(self.keybinds[action]).upper()
                    self.options.append(f"{action} : {key_name}")
            self.options.append("RETOUR")

    def update_volume(self, delta):
        """modifie le volume"""
        now = pygame.time.get_ticks()
        if now - self.last_vol_change > 150:
            self.volume = max(0, min(10, self.volume + delta))
            pygame.mixer.music.set_volume(self.volume / 10.0)
            self.last_vol_change = now

    def set_volume_by_mouse(self, mouse_x):
        """modifie le volume avec la souris"""
        rel_x = mouse_x - self.vol_rect.x
        new_vol = int((rel_x / self.vol_rect.width) * 11)
        self.volume = max(0, min(10, new_vol))
        pygame.mixer.music.set_volume(self.volume / 10.0)

    def activate_selected(self):
        """déclenche l'action selon l'option choisie"""
        if self.state == "MAIN":
            opt = self.main_options[self.selected_index]
            if opt == "OPTIONS":
                self.state = "OPTIONS"
                self.selected_index = 0
                self.update_options_list()
            else:
                return opt
        elif self.state == "OPTIONS":
            if self.selected_index == len(self.bind_order):
                self.state = "MAIN"
                self.selected_index = 0
                self.update_options_list()
            else:
                self.waiting_for_key = self.bind_order[self.selected_index]
                self.update_options_list()
        return None

    def handle_input(self, event):
        # changement de touche
        if self.waiting_for_key:
            if event.type == pygame.KEYDOWN:
                if event.key != pygame.K_ESCAPE:
                    # vérifie si la touche est déjà utilisée
                    if event.key not in self.keybinds.values():
                        self.keybinds[self.waiting_for_key] = event.key
                    else:
                        print("Erreur : Touche déjà utilisée !")
                self.waiting_for_key = None
                self.update_options_list()
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                return self.activate_selected()

        # gestion souris
        if event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.option_rects):
                if rect.collidepoint(event.pos):
                    self.selected_index = i
            if pygame.mouse.get_pressed()[0] and self.vol_rect.collidepoint(event.pos):
                self.set_volume_by_mouse(event.pos[0])

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.vol_rect.collidepoint(event.pos):
                self.set_volume_by_mouse(event.pos[0])
            else:
                for i, rect in enumerate(self.option_rects):
                    if rect.collidepoint(event.pos):
                        self.selected_index = i
                        return self.activate_selected()
        return None

    def draw(self, surface):
        """rendu graphique du menu et des effets"""
        t_off_x, t_off_y = glitch_offset(0.1, 5)

        if self.state == "MAIN":
            title_lines = ["FIVE", "NIGHTS", "AT", "CHATELET"]
            start_y, spacing = 440, 60
        else:
            title_lines = ["OPTIONS"]
            start_y, spacing = 220, 50

        for idx, line in enumerate(title_lines):
            color = COLOR_SELECTED if random.random() > 0.05 else (180, 180, 180)
            t_surf = self.font_title.render(line, True, color)
            surface.blit(t_surf, (self.align_x + t_off_x, 50 + (idx * 85) + t_off_y))

        self.option_rects = []
        for i, option in enumerate(self.options):
            is_sel = (i == self.selected_index)
            if self.state == "OPTIONS" and self.waiting_for_key and is_sel:
                color = COLOR_WAITING
            else:
                color = COLOR_SELECTED if is_sel else COLOR_TEXT

            m_off_x, _ = glitch_offset(0.02, 3) if is_sel else (0, 0)
            y_pos = start_y + (i * spacing)

            if is_sel:
                prefix_surf = self.font_menu.render(">> ", True, color)
                opt_text_surf = self.font_menu.render(option, True, color)
                surface.blit(prefix_surf, (self.align_x - 75 + m_off_x, y_pos))
                rect = opt_text_surf.get_rect(topleft=(self.align_x + m_off_x, y_pos))
                surface.blit(opt_text_surf, rect)
            else:
                opt_text_surf = self.font_menu.render(option, True, color)
                rect = opt_text_surf.get_rect(topleft=(self.align_x, y_pos))
                surface.blit(opt_text_surf, rect)
            self.option_rects.append(rect)

        vol_text = f"VOL [{'|'*self.volume}{'.'*(10-self.volume)}]"
        vol_surf = self.font_small.render(vol_text, True, (120, 120, 120))
        self.vol_rect = vol_surf.get_rect(bottomright=(WIDTH - 50, HEIGHT - 40))
        surface.blit(vol_surf, self.vol_rect)
        ver_surf = self.font_small.render("v 1.0 (RER B)", True, (60, 60, 60))
        surface.blit(ver_surf, (30, HEIGHT - 40))

def run_menu():
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("FIVE NIGHTS AT CHATELET")
    clock = pygame.time.Clock()

    try:
        # musique ambiente
        pygame.mixer.music.load(res("ressources/sounds/menu_music.ogg"))
        pygame.mixer.music.set_volume(0.7)
        pygame.mixer.music.play(-1)
    except: pass

    try:
        # arrière plan
        bg = pygame.image.load(res("ressources/images/chatelet.jpg"))
        bg = pygame.transform.scale(bg, (WIDTH, HEIGHT))
        has_background = True
    except:
        has_background = False

    menu = Menu()
    running = True
    action = None

    while running:
        keys = pygame.key.get_pressed()
        if not menu.waiting_for_key:
            if keys[pygame.K_RIGHT]: menu.update_volume(1)
            if keys[pygame.K_LEFT]: menu.update_volume(-1)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                action = 'exit'
                running = False

            result = menu.handle_input(event)
            if result:
                if result == "EXIT":
                    action = 'exit'
                    running = False
                elif result == "START":
                    action = 'start'
                    running = False

        if has_background:
            screen.blit(bg, (0, 0))
            dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dark.fill((0, 0, 0, 220))
            screen.blit(dark, (0, 0))
        else:
            screen.fill(COLOR_BG)

        menu.draw(screen)
        draw_fnaf_static(screen)
        draw_scanlines(screen)
        pygame.display.flip()
        clock.tick(FPS)

    if action == 'start':
        try:
            azerty_to_ursina = {
                "a": "q",
                "q": "a",
                "z": "w",
                "w": "z",
                "m": ";",
                "up": "up arrow",
                "down": "down arrow",
                "left": "left arrow",
                "right": "right arrow",
                "return": "enter",
                "page up": "page up",
                "page down": "page down",
            }
            binds_export = {
                k: azerty_to_ursina.get(pygame.key.name(v), pygame.key.name(v))
                for k, v in menu.keybinds.items()
            }

            # sauvegarde dans un fichier json
            with open("config_touches.json", "w") as f:
                json.dump(binds_export, f)

            screen.fill((0, 0, 0))
            font = pygame.font.SysFont(FONT_MAIN, 40)
            txt = font.render('LOADING...', True, (200, 200, 200))
            screen.blit(txt, txt.get_rect(center=(WIDTH//2, HEIGHT//2)))
            pygame.display.flip()
            pygame.time.delay(1000)  # Délai pour l'effet de chargement
        except: pass

    pygame.quit()
    return action

if __name__ == "__main__":
    run_menu()
