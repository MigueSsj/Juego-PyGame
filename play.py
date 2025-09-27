import pygame
from pathlib import Path

BACKGROUND_FILE = "Background_fondo.jpeg"

def run(screen: pygame.Surface, assets_dir: Path):
    """
    Pantalla del juego básica:
    - Reutiliza la ventana del main.
    - Fondo con scroll.
    - Regresa al menú con clic izquierdo.
    """
    clock = pygame.time.Clock()
    W, H = screen.get_size()

    # Ya existe video mode, así que podemos convertir
    background = pygame.image.load(str(assets_dir / BACKGROUND_FILE)).convert()
    bw, bh = background.get_size()

    scroll_x = 0
    SCROLL_SPEED = 2

    font = pygame.font.SysFont("arial", 36)
    label = font.render("NIVEL 1 - (clic para volver)", True, (255, 255, 255))

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); raise SystemExit
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                running = False

        # Fondo con scroll
        scroll_x -= SCROLL_SPEED
        if scroll_x <= -bw:
            scroll_x = 0
        screen.blit(background, (scroll_x, 0))
        screen.blit(background, (scroll_x + bw, 0))

        # Texto
        screen.blit(label, (W//2 - label.get_width()//2, int(H * 0.12)))

        pygame.display.flip()
        clock.tick(60)


    return {}
