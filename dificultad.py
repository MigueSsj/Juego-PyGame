# dificultad.py
import pygame
from pathlib import Path

# ========== HELPERS ==========
def find_by_stem(assets_dir: Path, stem: str):
    """Devuelve Path a la primera imagen que coincida por nombre exacto o prefijo."""
    exts = (".png", ".jpg", ".jpeg")
    # exacto
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists():
            return p
    # por prefijo
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{stem}*{ext}"))
    return min(cands, key=lambda p: len(p.name)) if cands else None

def load_image(assets_dir: Path, stems: list[str]) -> pygame.Surface | None:
    """Carga la primera imagen que exista entre los prefijos dados."""
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            return img.convert_alpha() if p.suffix.lower() == ".png" else img.convert()
    return None

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height() * r)))

# ======== importar SeleccionPersonajeScreen (raíz o levels/) ========
def _import_seleccion_clase():
    try:
        from seleccion_personaje import SeleccionPersonajeScreen
        return SeleccionPersonajeScreen
    except ModuleNotFoundError:
        # si está dentro de levels/
        from levels.seleccion_personaje import SeleccionPersonajeScreen
        return SeleccionPersonajeScreen

def _abrir_seleccion_personaje(screen: pygame.Surface, assets_dir: Path):
    SeleccionPersonajeScreen = _import_seleccion_clase()
    print("[DEBUG] Abriendo SeleccionPersonajeScreen…")
    SeleccionPersonajeScreen(screen, assets_dir).run()
    print("[DEBUG] Selección de personaje cerrada.")

# ========== PANTALLA DIFICULTAD ==========
def run(screen: pygame.Surface, assets_dir: Path, nivel: int):
    """
    Selector de dificultad para el nivel dado.
    UI: 'Normal' -> lógica 'facil'
    Retorna:
      {"dificultad": "facil"}  o  {"dificultad": "dificil"}
    Si el usuario presiona Back, retorna None.
    """
    clock = pygame.time.Clock()
    W, H = screen.get_size()

    # ---- Fondo con scroll ----
    background = load_image(assets_dir, ["Background_f", "Background_fondo", "fondo"])
    if not background:
        raise FileNotFoundError("Fondo no encontrado (Background_f*).")
    background = pygame.transform.smoothscale(background, (W, H))
    bw = background.get_width()
    scroll_x = 0
    SCROLL_SPEED = 2

    # ---- Título (imagen si hay, si no texto) ----
    ASSETS_DIR = Path(__file__).parent / "assets"
    try:
        title_img = pygame.image.load(ASSETS_DIR / "elige_dificultad_nivel1.png").convert_alpha()
        title_img = scale_to_width(title_img, int(W * 0.3))
    except Exception:
        font_title = pygame.font.SysFont("arial", 48, bold=True)
        title_img = font_title.render(f"Elige dificultad - Nivel {nivel}", True, (255, 255, 255))
    title_rect = title_img.get_rect(center=(W // 2, int(H * 0.18)))

    # ---- Botones (UI muestra NORMAL y DIFÍCIL) ----
    # Normal == Fácil en la lógica
    btn_normal_img  = load_image(assets_dir, ["btn_normal", "normal", "btn_facil", "facil"])
    btn_dificil_img = load_image(assets_dir, ["btn_dificil", "dificil"])

    target_w = int(W * 0.26)
    gap = int(W * 0.06)
    HOVER_SCALE = 1.08

    def prepare_button(img: pygame.Surface | None, fallback_text: str):
        if img:
            base = scale_to_width(img, target_w)
            hover = scale_to_width(base, int(base.get_width() * HOVER_SCALE))
            return base, hover
        # Fallback con texto
        font = pygame.font.SysFont("arial", 40, bold=True)
        text = font.render(fallback_text, True, (20, 20, 20))
        pad = 24
        base = pygame.Surface((text.get_width() + pad * 2, text.get_height() + pad * 2), pygame.SRCALPHA)
        base.fill((230, 230, 230))
        base.blit(text, (pad, pad))
        hover = pygame.transform.smoothscale(
            base,
            (int(base.get_width() * HOVER_SCALE), int(base.get_height() * HOVER_SCALE))
        )
        return base, hover

    normal_base, normal_hover   = prepare_button(btn_normal_img,  "Normal")
    dificil_base, dificil_hover = prepare_button(btn_dificil_img, "Difícil")

    total_w = normal_base.get_width() + dificil_base.get_width() + gap
    start_x = (W - total_w) // 2
    center_y = int(H * 0.55)

    r_normal  = normal_base.get_rect(midleft=(start_x, center_y))
    r_dificil = dificil_base.get_rect(midleft=(r_normal.right + gap, center_y))

    # ---- Botón Back ----
    back_img = load_image(assets_dir, ["btn_back", "regresar", "btn_regresar", "back"])
    if not back_img:
        raise FileNotFoundError("No existe el botón Back (btn_back*).")
    desired_w = max(120, min(int(W * 0.12), 240))
    back_img = scale_to_width(back_img, desired_w)
    back_img_hover = scale_to_width(back_img, int(back_img.get_width() * HOVER_SCALE))
    back_rect = back_img.get_rect()
    back_rect.bottomleft = (10, H - 12)

    # ---- Bucle ----
    while True:
        mouse = pygame.mouse.get_pos()
        click = False

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return None
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                click = True

        # Fondo con scroll
        scroll_x -= SCROLL_SPEED
        if scroll_x <= -bw:
            scroll_x = 0
        screen.blit(background, (scroll_x, 0))
        screen.blit(background, (scroll_x + bw, 0))

        # Título
        screen.blit(title_img, title_rect)

        # Dibujo con hover
        def draw_pair(base_img, hover_img, rect):
            if rect.collidepoint(mouse):
                r = hover_img.get_rect(center=rect.center)
                screen.blit(hover_img, r)
                return r
            screen.blit(base_img, rect)
            return rect

        rN = draw_pair(normal_base,  normal_hover,  r_normal)
        rD = draw_pair(dificil_base, dificil_hover, r_dificil)

        # Back con hover
        if back_rect.collidepoint(mouse):
            r_back = back_img_hover.get_rect(center=back_rect.center)
            screen.blit(back_img_hover, r_back)
            current_back_rect = r_back
        else:
            screen.blit(back_img, back_rect)
            current_back_rect = back_rect

        # Clicks
        if click:
            if rN.collidepoint(mouse):
                _abrir_seleccion_personaje(screen, assets_dir)   # ← abre selección
                return {"dificultad": "facil"}                    # ← vuelve a play.py
            if rD.collidepoint(mouse):
                _abrir_seleccion_personaje(screen, assets_dir)
                return {"dificultad": "dificil"}
            if current_back_rect.collidepoint(mouse):
                return None

        pygame.display.flip()
        clock.tick(60)
