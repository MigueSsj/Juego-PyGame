# opciones.py
import pygame
from pathlib import Path

# =========================
# Helpers mínimos locales
# =========================
def find_by_stem(assets_dir: Path, stem: str):
    """Busca una imagen por prefijo en /assets y retorna Path o None."""
    exts = (".png", ".jpg", ".jpeg")
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists():
            return p
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{stem}*{ext}"))
    return min(cands, key=lambda p: len(p.name)) if cands else None

def load_image(assets_dir: Path, stems: list[str]) -> pygame.Surface:
    """Carga la primera coincidencia de stems y hace convert/convert_alpha."""
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
    raise FileNotFoundError(f"No se encontró ninguna imagen con stems: {stems}")

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height()*r)))

# =========================
# Pantalla de OPCIONES
# =========================
def run(screen: pygame.Surface, assets_dir: Path):
    """
    Pantalla de OPCIONES:
    - Fondo con scroll infinito.
    - Muestra botón 'Back' en esquina inferior izquierda.
    - SOLO regresa si haces click en el botón 'Back'.
    """
    clock = pygame.time.Clock()
    W, H = screen.get_size()

    # Fondo (prefijo usado en tu main)
    background = load_image(assets_dir, ["Background_f", "Background_fondo"])
    # Escalar fondo al tamaño de pantalla para evitar bandas
    background = pygame.transform.smoothscale(background, (W, H))
    bw, bh = background.get_size()

    # Botón Back (admite varios nombres)
    back_img = load_image(assets_dir, ["btn_back", "regresar", "btn_regresar", "back"])
    desired_w = max(120, min(int(W * 0.12), 240))
    back_img = scale_to_width(back_img, desired_w)
    back_img_hover = scale_to_width(back_img, int(back_img.get_width() * 1.08))

    # Posición del botón: esquina inferior izquierda con margen
    back_rect = back_img.get_rect()
    margin_x, margin_y = 10, 12
    back_rect.bottomleft = (margin_x, H - margin_y)

    # Scroll del fondo
    scroll_x = 0
    SCROLL_SPEED = 2

    running = True
    while running:
        mouse = pygame.mouse.get_pos()
        clicked = False

        # --- Eventos ---
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                clicked = True  # sólo registramos el click

        # --- Fondo con scroll infinito ---
        scroll_x -= SCROLL_SPEED
        if scroll_x <= -bw:
            scroll_x = 0
        screen.blit(background, (scroll_x, 0))
        screen.blit(background, (scroll_x + bw, 0))

        # --- Botón Back con hover zoom ---
        if back_rect.collidepoint(mouse):
            r = back_img_hover.get_rect(center=back_rect.center)
            screen.blit(back_img_hover, r)
            current_back_rect = r
        else:
            screen.blit(back_img, back_rect)
            current_back_rect = back_rect

        # --- Click: SOLO si fue sobre el botón Back regresamos ---
        if clicked and current_back_rect.collidepoint(mouse):
            return {}  # ← volver al menú principal

        # --- Refresco ---
        pygame.display.flip()
        clock.tick(60)
