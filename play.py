import pygame
from pathlib import Path

# ---------- helpers ----------
def find_by_stem(assets_dir: Path, stem: str) -> Path | None:
    """Busca archivos por prefijo (stem) en assets."""
    exts = (".png", ".jpg", ".jpeg")
    # 1) Buscar coincidencia exacta (stem.png/jpg/jpeg)
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists():
            return p
    # 2) Buscar archivos que empiecen con stem
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{stem}*{ext}"))
    if not cands:
        return None
    # 3) Devolver el de nombre más corto
    return sorted(cands, key=lambda p: len(p.name))[0]

def load_image(assets_dir: Path, stems: list[str]) -> pygame.Surface | None:
    """Carga la primera imagen válida de una lista de posibles nombres."""
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            # Si es PNG mantiene transparencia
            return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
    return None

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    """Escala la imagen a un ancho fijo manteniendo proporción."""
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height()*r)))

# ---------- pantalla PLAY ----------
def run(screen: pygame.Surface, assets_dir: Path):
    clock = pygame.time.Clock()
    W, H = screen.get_size()   # Tamaño de la ventana

    # =========================
    # Fondo con scroll
    # =========================
    background = load_image(assets_dir, ["Background_f"])
    if background is None:
        raise FileNotFoundError("No encontré el fondo 'Background_f*.png/jpg/jpeg'.")
    background = pygame.transform.smoothscale(background, (W, H))
    scroll_x = 0
    SCROLL_SPEED = 2

    # =========================
    # Tarjetas de niveles
    # =========================
    card1 = load_image(assets_dir, ["btn_nivel_1", "nivel_1"])
    card2 = load_image(assets_dir, ["btn_nivel_2", "nivel_2"])
    card3 = load_image(assets_dir, ["btn_nivel_3", "nivel_3"])
    if not all([card1, card2, card3]):
        raise FileNotFoundError("Faltan imágenes de niveles (btn_nivel_1/2/3*).")

    # Escalar tarjetas
    target_w = int(W * 0.26)  # ancho de cada tarjeta
    gap = int(W * 0.02)       # espacio entre tarjetas
    card1 = scale_to_width(card1, target_w)
    card2 = scale_to_width(card2, target_w)
    card3 = scale_to_width(card3, target_w)

    # Posiciones centradas
    total_w = card1.get_width() + card2.get_width() + card3.get_width() + 2*gap
    start_x = (W - total_w) // 2
    center_y = int(H * 0.55)

    r1 = card1.get_rect(midleft=(start_x, center_y))
    r2 = card2.get_rect(midleft=(r1.right + gap, center_y))
    r3 = card3.get_rect(midleft=(r2.right + gap, center_y))

    # =========================
    # Título como imagen
    # =========================
    title_img = load_image(assets_dir, ["title_levels", "seleccione", "title_niveles"])
    if not title_img:
        raise FileNotFoundError("Falta la imagen del título (title_levels.png).")
    title_img = scale_to_width(title_img, int(W * 0.45))  # escala título
    title_rect = title_img.get_rect(center=(W // 2, int(H * 0.18)))

    # =========================
    # Botón BACK (abajo-izquierda con hover zoom)
    # =========================
    back_img = load_image(assets_dir, ["btn_back", "regresar", "btn_regresar", "back"])
    back_rect = None
    HOVER_SCALE = 1.08
    if back_img:
        # Escala adaptativa
        desired_w = max(120, min(int(W * 0.12), 240))
        back_img = scale_to_width(back_img, desired_w)
        back_img_hover = scale_to_width(back_img, int(back_img.get_width() * HOVER_SCALE))

        # Posición esquina inferior izquierda
        back_rect = back_img.get_rect()
        margin_x, margin_y = 10, 12
        back_rect.bottomleft = (margin_x, H - margin_y)

    # =========================
    # Función auxiliar para tarjetas
    # =========================
    def draw_card(img, rect, mouse):
        """Dibuja la tarjeta y borde si el mouse está encima."""
        if rect.collidepoint(mouse):
            pygame.draw.rect(screen, (255, 255, 255), rect.inflate(10, 10), 3, border_radius=10)
        screen.blit(img, rect)

    # =========================
    # Bucle principal
    # =========================
    running = True
    while running:
        mouse = pygame.mouse.get_pos()
        click = False
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return None   # cerrar juego
            elif e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_LEFT):
                return None   # salir si presiona ESC o flecha izquierda
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                click = True  # click izquierdo

        # Fondo con scroll infinito
        scroll_x -= SCROLL_SPEED
        if scroll_x <= -W:
            scroll_x = 0
        screen.blit(background, (scroll_x, 0))
        screen.blit(background, (scroll_x + W, 0))

        # Título (imagen PNG transparente, ya sin fondo negro)
        screen.blit(title_img, title_rect)

        # Tarjetas de niveles
        draw_card(card1, r1, mouse)
        draw_card(card2, r2, mouse)
        draw_card(card3, r3, mouse)

        # Botón Back con hover zoom
        current_back_rect = None
        if back_img:
            if back_rect.collidepoint(mouse):
                r = back_img_hover.get_rect(center=back_rect.center)
                screen.blit(back_img_hover, r)
                current_back_rect = r
            else:
                screen.blit(back_img, back_rect)
                current_back_rect = back_rect

        # Detección de clicks
        if click:
            if r1.collidepoint(mouse): return {"nivel": 1}
            if r2.collidepoint(mouse): return {"nivel": 2}
            if r3.collidepoint(mouse): return {"nivel": 3}
            if current_back_rect and current_back_rect.collidepoint(mouse):
                return None  # volver al menú principal

        # Refrescar pantalla
        pygame.display.flip()
        clock.tick(60)
