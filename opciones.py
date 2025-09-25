# opciones.py (versión sencilla)
import pygame
from pathlib import Path

# Cambia esto al nombre real de tu imagen en /assets
BACKGROUND_FILE = "Background_fondo.jpeg"   # ej. "Background_f.png" o el que tengas

def run(screen: pygame.Surface, assets_dir: Path):
    """
    Pantalla de OPCIONES sencilla:
    - Reutiliza la pantalla del main.
    - Muestra el fondo con scroll infinito.
    - Regresa al menú con clic izquierdo.
    """
    clock = pygame.time.Clock()
    W, H = screen.get_size()

    # 1) Cargar la imagen de fondo (usa tu ruta directa)
    bg_path = assets_dir / BACKGROUND_FILE
    background = pygame.image.load(str(bg_path)).convert()
    bw, bh = background.get_size()  # ancho/alto del fondo

    # 2) Variables para el scroll
    scroll_x = 0
    SCROLL_SPEED = 2  # velocidad del desplazamiento

    # 3) Un texto simple para saber que estamos en OPCIONES
    font = pygame.font.SysFont("arial", 36)
    label = font.render("OPCIONES  (clic izquierdo para volver)", True, (255, 255, 255))

    running = True
    while running:
        # --- Eventos ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Clic izquierdo: regresar al menú
                running = False

        # --- Dibujar fondo con scroll infinito ---
        scroll_x -= SCROLL_SPEED
        if scroll_x <= -bw:
            scroll_x = 0
        screen.blit(background, (scroll_x, 0))
        screen.blit(background, (scroll_x + bw, 0))


        # --- Mostrar en pantalla ---
        pygame.display.flip()
        clock.tick(60)

    return {}
