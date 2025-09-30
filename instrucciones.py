import pygame, math
from pathlib import Path

# ==============================
# -------- HELPERS -------------
# ==============================

# Buscar archivo por "stem" (nombre base sin extensión)
def find_by_stem(assets_dir: Path, stem: str) -> Path | None:
    exts = (".png", ".jpg", ".jpeg")
    # Primero intenta coincidencia exacta: stem.png/jpg/jpeg
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists():
            return p
    # Si no, busca cualquier archivo que empiece con stem
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{stem}*{ext}"))
    if not cands:
        return None
    # Si hay varios, se queda con el de nombre más corto
    return sorted(cands, key=lambda p: len(p.name))[0]

# Cargar imagen con varios posibles nombres
def load_image(assets_dir: Path, stems: list[str]) -> pygame.Surface | None:
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            # Si es PNG se respeta la transparencia
            return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
    return None

# Escalar una imagen a un ancho fijo manteniendo la proporción
def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    ratio = new_w / img.get_width()
    new_h = int(img.get_height() * ratio)
    return pygame.transform.smoothscale(img, (new_w, new_h))

# ==============================
# ---- PANTALLA INSTRUCCIONES --
# ==============================
def run(screen: pygame.Surface, assets_dir: Path) -> None:
    W, H = screen.get_size()
    clock = pygame.time.Clock()

    # ----------------------------
    # Fondo con scroll infinito
    # ----------------------------
    bg_img = load_image(assets_dir, ["Background_f"])   # carga el fondo
    if not bg_img:
        raise FileNotFoundError("No encontré fondo para instrucciones")
    background = bg_img.convert()
    bg_w, bg_h = background.get_size()
    scroll_x = 0                 # posición inicial del scroll
    SCROLL_SPEED = 2             # velocidad del scroll

    # ----------------------------
    # Imagen de INSTRUCCIONES
    # ----------------------------
    instr_img = load_image(assets_dir, ["instrucciones", "panel_instrucciones"])
    if not instr_img:
        raise FileNotFoundError("No encontré imagen de instrucciones en assets/")
    iw, ih = instr_img.get_size()
    # Escalado para que no ocupe más del 90% de pantalla
    ratio = min(W*0.9/iw, H*0.9/ih, 1.0)
    if ratio < 1.0:
        instr_img = pygame.transform.smoothscale(instr_img, (int(iw*ratio), int(ih*ratio)))
    instr_rect = instr_img.get_rect(center=(W//2, H//2))  # centrado en pantalla

    # ----------------------------
    # Botón BACK (regresar)
    # ----------------------------
    back_img = load_image(assets_dir, ["btn_back", "regresar", "btn_regresar", "back"])
    back_rect = None
    HOVER_SCALE = 1.08  # cuando el mouse pasa encima, crece 8%
    if back_img:
        # Escalar botón según tamaño de pantalla
        desired_w = max(120, min(int(W * 0.12), 240))
        back_img = scale_to_width(back_img, desired_w)
        # Versión hover (más grande)
        back_img_hover = scale_to_width(back_img, int(back_img.get_width() * HOVER_SCALE))
        # Colocar en esquina inferior izquierda con un margen
        back_rect = back_img.get_rect()
        margin_x, margin_y = 10, 12
        back_rect.bottomleft = (margin_x, H - margin_y)

    # ----------------------------
    # LOOP principal de instrucciones
    # ----------------------------
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        clicked = False

        # Eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:      # cerrar ventana
                return
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return                         # salir con ESC
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True                 # detectar click izquierdo

        # ---- DIBUJAR FONDO SCROLL ----
        scroll_x -= SCROLL_SPEED
        if scroll_x <= -bg_w:                  # reset cuando termina la imagen
            scroll_x = 0
        screen.blit(background, (scroll_x, 0))
        screen.blit(background, (scroll_x + bg_w, 0))

        # ---- DIBUJAR INSTRUCCIONES ----
        screen.blit(instr_img, instr_rect)

        # ---- DIBUJAR BOTÓN BACK ----
        if back_rect:
            if back_rect.collidepoint(mouse_pos):  # si el mouse está encima
                r = back_img_hover.get_rect(center=back_rect.center)
                screen.blit(back_img_hover, r)
                if clicked:                        # si da clic → salir
                    return
            else:
                screen.blit(back_img, back_rect)

        # Actualizar pantalla
        pygame.display.flip()
        clock.tick(60)
