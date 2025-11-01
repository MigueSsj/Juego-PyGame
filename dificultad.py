# dificultad.py
from __future__ import annotations
import pygame
from pathlib import Path
from typing import Optional
import importlib, importlib.util
from audio_shared import play_sfx  # <<< usar SFX compartidos (easy/hard/back)

# ===== Helpers =====
def find_by_stem(assets_dir: Path, stem: str) -> Optional[Path]:
    exts = (".png", ".jpg", ".jpeg")
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists():
            return p
    cands: list[Path] = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{stem}*{ext}"))
    return min(cands, key=lambda p: len(p.name)) if cands else None

def load_image(assets_dir: Path, stems: list[str]) -> pygame.Surface | None:
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            return img.convert_alpha() if p.suffix.lower() == ".png" else img.convert()
    return None

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height() * r)))

# ===== Import Selección =====
def _import_seleccion_clase():
    try:
        from seleccion_personaje import SeleccionPersonajeScreen as Cls
        return Cls
    except Exception:
        pass
    try:
        mod = importlib.import_module("levels.seleccion_personaje")
        if hasattr(mod, "SeleccionPersonajeScreen"):
            return getattr(mod, "SeleccionPersonajeScreen")
    except Exception:
        pass
    base = Path(__file__).resolve().parent
    for p in [base / "levels" / "seleccion_personaje.py", base / "seleccion_personaje.py"]:
        if p.exists():
            spec = importlib.util.spec_from_file_location("levels.seleccion_personaje", str(p))
            mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            assert spec and spec.loader
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            if hasattr(mod, "SeleccionPersonajeScreen"):
                return getattr(mod, "SeleccionPersonajeScreen")
    raise ModuleNotFoundError("No se encontró seleccion_personaje.py en raíz ni en /levels/.")

def _abrir_seleccion_personaje(screen: pygame.Surface, assets_dir: Path) -> Optional[str]:
    SeleccionPersonajeScreen = _import_seleccion_clase()
    return SeleccionPersonajeScreen(screen, assets_dir).run()  # ← retorna nombre o None

# ===== Pantalla Dificultad =====
def run(screen: pygame.Surface, assets_dir: Path, nivel: int = 1, *args, **kwargs):
    """Devuelve {'dificultad': 'facil'|'dificil', 'personaje': <str>} o None si Back."""
    clock = pygame.time.Clock()
    W, H = screen.get_size()

    background = load_image(assets_dir, ["Background_f", "Background_fondo", "fondo"])
    if not background:
        raise FileNotFoundError("Fondo no encontrado (Background_f*).")
    background = pygame.transform.smoothscale(background, (W, H))
    bw = background.get_width()
    scroll_x = 0; SCROLL_SPEED = 2

    title_img = load_image(assets_dir, [f"elige_dificultad_nivel{nivel}", "elige_dificultad", "title_dificultad"])
    if title_img:
        title_img = scale_to_width(title_img, int(W * 0.38))
    else:
        font_title = pygame.font.SysFont("arial", 48, bold=True)
        title_img = font_title.render(f"Elige dificultad - Nivel {nivel}", True, (255, 255, 255))
    title_rect = title_img.get_rect(center=(W // 2, int(H * 0.18)))

    btn_normal_img  = load_image(assets_dir, ["btn_normal", "normal", "btn_facil", "facil"])
    btn_dificil_img = load_image(assets_dir, ["btn_dificil", "dificil"])
    target_w = int(W * 0.26); gap = int(W * 0.06); HOVER_SCALE = 1.08

    def prepare_button(img: pygame.Surface | None, txt: str):
        if img:
            base = scale_to_width(img, target_w)
            hover = scale_to_width(base, int(base.get_width()*HOVER_SCALE))
            return base, hover
        font = pygame.font.SysFont("arial", 40, bold=True)
        txtsurf = font.render(txt, True, (20,20,20))
        pad = 24
        base = pygame.Surface((txtsurf.get_width()+pad*2, txtsurf.get_height()+pad*2), pygame.SRCALPHA)
        base.fill((230,230,230)); base.blit(txtsurf, (pad, pad))
        hover = pygame.transform.smoothscale(base, (int(base.get_width()*HOVER_SCALE), int(base.get_height()*HOVER_SCALE)))
        return base, hover

    normal_base, normal_hover   = prepare_button(btn_normal_img,  "Normal")
    dificil_base, dificil_hover = prepare_button(btn_dificil_img, "Difícil")

    total_w = normal_base.get_width() + dificil_base.get_width() + gap
    start_x = (W - total_w) // 2
    center_y = int(H * 0.55)
    r_normal  = normal_base.get_rect(midleft=(start_x, center_y))
    r_dificil = dificil_base.get_rect(midleft=(r_normal.right + gap, center_y))

    back_img = load_image(assets_dir, ["btn_back", "regresar", "btn_regresar", "back"])
    if not back_img: raise FileNotFoundError("No existe el botón Back (btn_back*).")
    desired_w = max(120, min(int(W * 0.12), 240))
    back_img = scale_to_width(back_img, desired_w)
    back_img_hover = scale_to_width(back_img, int(back_img.get_width()*HOVER_SCALE))
    back_rect = back_img.get_rect(); back_rect.bottomleft = (10, H - 12)

    while True:
        mouse = pygame.mouse.get_pos(); click = False
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1: click = True

        scroll_x -= SCROLL_SPEED
        if scroll_x <= -bw: scroll_x = 0
        screen.blit(background, (scroll_x, 0)); screen.blit(background, (scroll_x+bw, 0))
        screen.blit(title_img, title_rect)

        def draw_pair(base, hover, rect):
            if rect.collidepoint(mouse):
                r = hover.get_rect(center=rect.center); screen.blit(hover, r); return r
            screen.blit(base, rect); return rect
        rN = draw_pair(normal_base, normal_hover, r_normal)
        rD = draw_pair(dificil_base, dificil_hover, r_dificil)

        if back_rect.collidepoint(mouse):
            r_back = back_img_hover.get_rect(center=back_rect.center)
            screen.blit(back_img_hover, r_back); current_back_rect = r_back
        else:
            screen.blit(back_img, back_rect); current_back_rect = back_rect

        if click:
            if rN.collidepoint(mouse):
                play_sfx("easy", assets_dir)   # <<< sonido Fácil
                nombre = _abrir_seleccion_personaje(screen, assets_dir)
                if nombre is None:  # cancelado
                    return None
                return {"dificultad": "facil", "personaje": nombre}

            if rD.collidepoint(mouse):
                play_sfx("hard", assets_dir)   # <<< sonido Difícil
                nombre = _abrir_seleccion_personaje(screen, assets_dir)
                if nombre is None:
                    return None
                return {"dificultad": "dificil", "personaje": nombre}

            if current_back_rect.collidepoint(mouse):
                play_sfx("back", assets_dir)   # <<< sonido Back
                return None

        pygame.display.flip()
        clock.tick(60)
