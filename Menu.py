import pygame
import random
import sys
import os

WIDTH, HEIGHT = 1280, 720
FPS = 60
FONT_MAIN = "Courier New"
COLOR_BG = (5, 5, 10)
COLOR_TEXT = (140, 140, 140)
COLOR_SELECTED = (255, 255, 255)

# Chemin de base pour les ressources (compatibilité PyInstaller)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def res(path):
    return os.path.join(BASE_DIR, path)

def draw_fnaf_static(surface):
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
    for y in range(0, HEIGHT, 3):
        pygame.draw.line(surface, (0, 0, 0, 100), (0, y), (WIDTH, y))

def glitch_offset(chance=0.04, power=8):
    if random.random() < chance:
        return random.randint(-power, power), random.randint(-2, 2)
    return 0, 0

class Menu:
    def __init__(self):
        self.options = ["START", "OPTIONS", "EXIT"]
        self.selected_index = 0
        self.volume = 7
        self.font_title = pygame.font.SysFont(FONT_MAIN, 90, bold=True)
        self.font_menu = pygame.font.SysFont(FONT_MAIN, 50, bold=True)
        self.font_small = pygame.font.SysFont(FONT_MAIN, 22)
        self.option_rects = []
        self.vol_rect = pygame.Rect(0, 0, 0, 0)
        self.align_x = 100
        self.last_vol_change = 0

    def update_volume(self, delta):
        now = pygame.time.get_ticks()
        if now - self.last_vol_change > 150:
            self.volume = max(0, min(10, self.volume + delta))
            pygame.mixer.music.set_volume(self.volume / 10.0)
            self.last_vol_change = now

    def set_volume_by_mouse(self, mouse_x):
        rel_x = mouse_x - self.vol_rect.x
        new_vol = int((rel_x / self.vol_rect.width) * 11)
        self.volume = max(0, min(10, new_vol))
        pygame.mixer.music.set_volume(self.volume / 10.0)

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                return self.options[self.selected_index]

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
                        return self.options[i]
        return None

    def draw(self, surface):
        t_off_x, t_off_y = glitch_offset(0.1, 5)
        title_lines = ["FIVE", "NIGHTS", "AT", "CHATELET"]
        for idx, line in enumerate(title_lines):
            color = COLOR_SELECTED if random.random() > 0.05 else (180, 180, 180)
            t_surf = self.font_title.render(line, True, color)
            surface.blit(t_surf, (self.align_x + t_off_x, 50 + (idx * 85) + t_off_y))

        self.option_rects = []
        for i, option in enumerate(self.options):
            is_sel = (i == self.selected_index)
            color = COLOR_SELECTED if is_sel else COLOR_TEXT
            m_off_x, _ = glitch_offset(0.02, 3) if is_sel else (0, 0)

            if is_sel:
                prefix_surf = self.font_menu.render(">> ", True, color)
                opt_text_surf = self.font_menu.render(option, True, color)
                surface.blit(prefix_surf, (self.align_x - 75 + m_off_x, 440 + (i * 60)))
                rect = opt_text_surf.get_rect(topleft=(self.align_x + m_off_x, 440 + (i * 60)))
                surface.blit(opt_text_surf, rect)
            else:
                opt_text_surf = self.font_menu.render(option, True, color)
                rect = opt_text_surf.get_rect(topleft=(self.align_x, 440 + (i * 60)))
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
                elif result == "OPTIONS":
                    print("Menu Options ouvert")

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
            screen.fill((0, 0, 0))
            # écran de chargement
            font = pygame.font.SysFont(FONT_MAIN, 40)
            txt = font.render('LOADING...', True, (200, 200, 200))
            txt_rect = txt.get_rect(center=(WIDTH//2, HEIGHT//2))
            screen.blit(txt, txt_rect)
            pygame.display.flip()
            pygame.time.delay(1000)  # Délai pour l'effet de chargement
        except: pass

    pygame.quit()
    return action

if __name__ == "__main__":
    result = run_menu()
    if result == 'start':
        print('Démarrage du jeu...')
    else:
        print('Sortie du menu')
