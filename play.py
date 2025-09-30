# play.py
import pygame
from pathlib import Path

# ---------------------------------------
# FUNCIONES DE APOYO (para cargar imágenes)
# ---------------------------------------

def find_by_stem(assets_dir: Path, stem: str) -> Path | None:
    """
    Busca un archivo de imagen en la carpeta assets que comience
    con el nombre (stem) y tenga extensión .png, .jpg o .jpeg.
    """
    exts = (".png", ".jpg", ".jpeg")
    # 1) Primero intenta coincidencia exacta (stem.png, stem.jpg...)
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists():
            return p
    # 2) Si no existe exacto, busca cualquier archivo que empiece con stem
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{stem}*{ext}"))
    if not cands:
        return None
    # 3) Devuelve el de nombre más corto (más probable que sea el principal)
    return sorted(cands, key=lambda p: len(p.name))[0]

def load_bg(assets_dir: Path, stem="Background_f") -> pygame.Surface:
    """
    Carga la imagen de fondo del menú.  
    Si no la encuentra, lanza un error.
    """
    p = find_by_stem(assets_dir, stem)
    if not p:
        raise FileNotFoundError(f"No encontré fondo '{stem}*.png/.jpg/.jpeg' en {assets_dir}")
    img = pygame.image.load(str(p))
    return img.convert()   # convert para que se dibuje más rápido

# ---------------------------------------
# FUNCIÓN PRINCIPAL DE ESTA PANTALLA
# ---------------------------------------

def run(screen: pygame.Surface, assets_dir: Path):
    """
    Pantalla provisional de PLAY:
    - Muestra el mismo fondo del inicio con scroll infinito.
    - El jugador puede salir con ESC o clic izquierdo.
    - De momento NO hay botones de niveles.
    """
    clock = pygame.time.Clock()
    W, H = screen.get_size()   # dimensiones de la ventana

    # ---- Cargar el fondo ----
    bg = load_bg(assets_dir, "Background_f")
    # Si el fondo no tiene el mismo tamaño que la ventana, lo escalamos
    if bg.get_size() != (W, H):
        bg = pygame.transform.smoothscale(bg, (W, H))

    # ---- Configuración del scroll ----
    scroll_x = 0             # posición inicial del scroll en X
    SCROLL_SPEED = 2         # velocidad con la que se mueve el fondo

    running = True
    while running:
        clicked = False
        # ---- Revisar eventos de teclado/ratón ----
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return None             # si cierran la ventana, salimos
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return None             # tecla ESC → volver al menú
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                clicked = True          # clic izquierdo → volver al menú

        if clicked:
            return None   # al hacer clic salimos de esta pantalla

        # ---- Dibujar fondo con scroll infinito ----
        scroll_x -= SCROLL_SPEED       # mover la posición hacia la izquierda
        if scroll_x <= -W:             # si se desplazó todo el ancho
            scroll_x = 0               # reiniciamos (efecto de bucle)
        screen.blit(bg, (scroll_x, 0))       # dibuja fondo en la pos actual
        screen.blit(bg, (scroll_x + W, 0))   # dibuja un segundo fondo al lado

        # ---- Actualizar pantalla ----
        pygame.display.flip()
        clock.tick(60)   # limitar a 60 FPS
