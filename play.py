import pygame
from pathlib import Path

# ---------- helpers ----------

def find_by_stem(assets_dir: Path, stem: str) -> Path | None:
    # Extensiones válidas
    exts = (".png", ".jpg", ".jpeg")
    # 1) Buscar coincidencia exacta: stem.png/jpg/jpeg
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists():
            return p
    # 2) Si no, buscar archivos que empiecen con "stem"
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{stem}*{ext}"))
    if not cands:
        return None
    # 3) Si hay varios, elegir el de nombre más corto
    return sorted(cands, key=lambda p: len(p.name))[0]

def load_image(assets_dir: Path, stems: list[str]) -> pygame.Surface | None:
    # Intenta cargar usando varios nombres posibles (stems)
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            # Si es PNG mantiene transparencia, si no usa convert normal
            return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
    return None

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    # Escala la imagen al ancho indicado (new_w) manteniendo proporción
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height()*r)))

# ---------- pantalla PLAY ----------
def run(screen: pygame.Surface, assets_dir: Path):
    clock = pygame.time.Clock()
    W, H = screen.get_size()   # Ancho y alto de la pantalla

    # Fondo (scroll)
    background = load_image(assets_dir, ["Background_f"])
    if background is None:
        raise FileNotFoundError("No encontré el fondo 'Background_f*.png/jpg/jpeg'.")
    background = pygame.transform.smoothscale(background, (W, H))  # escalar al tamaño pantalla
    scroll_x = 0
    SCROLL_SPEED = 2  # velocidad del scroll del fondo

    # Tarjetas de niveles
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

    # Calcular posiciones de las tarjetas para que queden centradas
    total_w = card1.get_width() + card2.get_width() + card3.get_width() + 2*gap
    start_x = (W - total_w) // 2
    center_y = int(H * 0.55)

    r1 = card1.get_rect(midleft=(start_x, center_y))
    r2 = card2.get_rect(midleft=(r1.right + gap, center_y))
    r3 = card3.get_rect(midleft=(r2.right + gap, center_y))

    # Título arriba
    title_font = pygame.font.Font(None, 96)
    title = title_font.render("Seleccione un nivel", True, (30, 20, 15))
    title_rect = title.get_rect(center=(W//2, int(H * 0.18)))

    # -------- Botón BACK (esquina inferior izquierda, con hover zoom) --------
    back_img = load_image(assets_dir, ["btn_back", "regresar", "btn_regresar", "back"])
    back_rect = None
    HOVER_SCALE = 1.08  # 8% más grande en hover
    if back_img:
        desired_w = max(120, min(int(W * 0.12), 240))  # tamaño adaptativo del botón
        back_img = scale_to_width(back_img, desired_w)
        back_img_hover = scale_to_width(back_img, int(back_img.get_width() * HOVER_SCALE))

        back_rect = back_img.get_rect()
        margin_x, margin_y = 10, 12
        # Lo coloca en la parte inferior izquierda con margen
        back_rect.bottomleft = (margin_x, H - margin_y)

    # Función para dibujar cada tarjeta con borde al pasar el mouse
    def draw_card(img, rect, mouse):
        if rect.collidepoint(mouse):
            pygame.draw.rect(screen, (255, 255, 255), rect.inflate(10, 10), 3, border_radius=10)
        screen.blit(img, rect)

    # Bucle principal de la pantalla PLAY
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
                click = True  # se detecta click izquierdo

 # --- fondo con scroll infinito ---
        scroll_x -= SCROLL_SPEED
        if scroll_x <= -W:
            scroll_x = 0
        screen.blit(background, (scroll_x, 0))
        screen.blit(background, (scroll_x + W, 0))

        # Título
        screen.blit(title, title_rect)

        # Tarjetas de niveles
        draw_card(card1, r1, mouse)
        draw_card(card2, r2, mouse)
        draw_card(card3, r3, mouse)

        # Botón Back con hover (zoom al pasar el mouse)
        current_back_rect = None
        if back_img:
            if back_rect.collidepoint(mouse):
                r = back_img_hover.get_rect(center=back_rect.center)  # mantener centrado al hacer zoom
                screen.blit(back_img_hover, r)
                current_back_rect = r
            else:
                screen.blit(back_img, back_rect)
                current_back_rect = back_rect

        # Clicks en objetos
        if click:
            if r1.collidepoint(mouse): return {"nivel": 1}   # si clic en tarjeta 1 → nivel 1
            if r2.collidepoint(mouse): return {"nivel": 2}   # si clic en tarjeta 2 → nivel 2
            if r3.collidepoint(mouse): return {"nivel": 3}   # si clic en tarjeta 3 → nivel 3
            if current_back_rect and current_back_rect.collidepoint(mouse):
                return None  # clic en BACK → regresar al menú principal

        # Actualizar pantalla
        pygame.display.flip()
        clock.tick(60)  # limitar a 60 FPS