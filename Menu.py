import pygame
import random
import sys

WIDTH, HEIGHT = 1280, 720
FPS = 60
FONT_MAIN = "Courier New"
COLOR_BG = (10, 10, 15)
COLOR_TEXT = (150, 150, 150)
COLOR_SELECTED = (255, 255, 255)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("FIVE NIGHTS AT CHATELET")
clock = pygame.time.Clock()

try:
    background_img = pygame.image.load("fnac_background.jpg")
    background_img = pygame.transform.scale(background_img, (WIDTH, HEIGHT))
    has_background = True
except:
    has_background = False  

def draw_scanlines(surface):
    scan_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(0, HEIGHT, 6):
        pygame.draw.line(scan_surf, (0, 0, 0, 80), (0, y), (WIDTH, y))
    surface.blit(scan_surf, (0, 0))

def draw_static_noise(surface):
    for _ in range(300):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        alpha = random.randint(50, 200)
        pygame.draw.rect(surface, (255, 255, 255, alpha), (x, y, 2, 2))

def glitch_offset():
    if random.random() < 0.02:
        return random.randint(-4, 4), random.randint(-4, 4)
    return 0, 0

class Menu:
    def __init__(self):
        self.options = ["START", "OPTIONS", "EXIT"]
        self.selected_index = 0
        self.volume = 5
        
        self.font_title = pygame.font.SysFont(FONT_MAIN, 90, bold=True)
        self.font_menu = pygame.font.SysFont(FONT_MAIN, 50, bold=True)
        self.font_small = pygame.font.SysFont(FONT_MAIN, 25)

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % len(self.options)
            
            elif event.key == pygame.K_RIGHT:
                if self.volume < 10: self.volume += 1
            elif event.key == pygame.K_LEFT:
                if self.volume > 0: self.volume -= 1
            
            elif event.key == pygame.K_RETURN:
                if self.options[self.selected_index] == "EXIT":
                    pygame.quit(); sys.exit()
                else:
                    print(f"Action : {self.options[self.selected_index]}")

    def draw(self, surface):
        off_x, off_y = glitch_offset()
        
        title_lines = ["FIVE", "NIGHTS", "AT", "CHATELET"]
        for idx, line in enumerate(title_lines):
            t_surf = self.font_title.render(line, True, COLOR_SELECTED)
            surface.blit(t_surf, (100 + off_x, 50 + (idx * 80) + off_y))

        start_y = 450 
        for i, option in enumerate(self.options):
            color = COLOR_TEXT
            prefix = ""

            if i == self.selected_index:
                color = COLOR_SELECTED
                prefix = ">> "
            
            opt_surf = self.font_menu.render(prefix + option, True, color)
            surface.blit(opt_surf, (100, start_y + (i * 60)))

 
        bar_filled = "|" * self.volume
        bar_empty = "." * (10 - self.volume)
        vol_text = f"VOLUME {bar_filled}{bar_empty}"
        
        vol_surf = self.font_small.render(vol_text, True, COLOR_SELECTED)
        rect = vol_surf.get_rect()
        rect.bottomright = (WIDTH - 50, HEIGHT - 30)
        surface.blit(vol_surf, rect)

        ver_surf = self.font_small.render("v 1.0 (RER B)", True, (100, 100, 100))
        surface.blit(ver_surf, (20, HEIGHT - 40))

def main():
    menu = Menu()
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            menu.handle_input(event)

        if has_background:
            screen.blit(background_img, (0, 0))
            veil = pygame.Surface((WIDTH, HEIGHT))
            veil.set_alpha(100)
            veil.fill((0,0,0))
            screen.blit(veil, (0,0))
        else:
            screen.fill(COLOR_BG)

        menu.draw(screen)

        draw_scanlines(screen)
        draw_static_noise(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
