# opciones.py
import json
from pathlib import Path
import pygame

# =========================
# Helpers mínimos locales (tuyos)
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
# Persistencia de ajustes
# =========================
DEFAULT_SETTINGS = {"volume": 0.6, "lang": "es"}

def _settings_path_from_assets(assets_dir: Path) -> Path:
    # Se guarda al lado de la carpeta assets (raíz del proyecto)
    return assets_dir.parent / "settings.json"

def load_settings(assets_dir: Path) -> dict:
    f = _settings_path_from_assets(assets_dir)
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            return {**DEFAULT_SETTINGS, **data}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(assets_dir: Path, data: dict) -> None:
    f = _settings_path_from_assets(assets_dir)
    try:
        f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass  # no romper el juego si no se puede guardar

# =========================
# Widgets simples (pixel style)
# =========================
class Button:
    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font,
                 on_click, img: pygame.Surface | None = None,
                 frame: bool = True, hover_scale: float = 1.08):
        self.rect = rect
        self.text = text
        self.font = font
        self.on_click = on_click
        self.img = img
        self.hover = False
        self.frame = frame           # si False, no dibuja caja
        self.hover_scale = hover_scale

    def draw(self, surf: pygame.Surface):
        # Vamos a dibujar el botón en una surface temporal del tamaño base
        temp = pygame.Surface(self.rect.size, pygame.SRCALPHA)

        outline = (30, 20, 15)
        bg = (205, 170, 125) if not self.hover else (225, 190, 145)

        # Dibuja caja solo si frame=True
        if self.frame:
            pygame.draw.rect(temp, outline, temp.get_rect())
            pygame.draw.rect(temp, bg, temp.get_rect().inflate(-6, -6))

        # imagen centrada (opcional)
        if self.img:
            img = self.img
            max_w = int(self.rect.w * (0.7 if self.frame else 0.9))
            max_h = int(self.rect.h * (0.55 if self.frame else 0.6))
            scale = min(max_w / img.get_width(), max_h / img.get_height(), 1.0)
            if scale < 1.0:
                img = pygame.transform.smoothscale(img, (int(img.get_width()*scale), int(img.get_height()*scale)))
            y_offset = -self.rect.h*0.12 if self.frame else -self.rect.h*0.05
            img_rect = img.get_rect(center=(self.rect.w//2, int(self.rect.h//2 + y_offset)))
            temp.blit(img, img_rect)

        # texto
        label = self.font.render(self.text, True, (25, 20, 15))
        if self.img:
            label_rect = label.get_rect(center=(self.rect.w//2, int(self.rect.h*0.72)))
        else:
            label_rect = label.get_rect(center=(self.rect.w//2, self.rect.h//2))
        temp.blit(label, label_rect)

        # Hover zoom (igual idea que tu back)
        if self.hover and self.hover_scale != 1.0:
            w = max(1, int(self.rect.w * self.hover_scale))
            h = max(1, int(self.rect.h * self.hover_scale))
            scaled = pygame.transform.smoothscale(temp, (w, h))
            dest = scaled.get_rect(center=self.rect.center)
            surf.blit(scaled, dest)
        else:
            surf.blit(temp, self.rect)

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()

class Slider:
    def __init__(self, x, y, w, h, value=0.5):
        self.rect = pygame.Rect(x, y, w, h)
        self.value = max(0.0, min(1.0, float(value)))
        self.dragging = False

    @property
    def knob_x(self):
        return int(self.rect.x + self.value * self.rect.w)

    def draw(self, surf: pygame.Surface):
        outline = (30, 20, 15)
        bar_bg = (120, 90, 60)
        bar_fill = (190, 150, 100)

        pygame.draw.rect(surf, outline, self.rect.inflate(8, 8))
        pygame.draw.rect(surf, bar_bg, self.rect)
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, int(self.rect.w * self.value), self.rect.h)
        pygame.draw.rect(surf, bar_fill, fill_rect)

        knob_rect = pygame.Rect(0, 0, 14, self.rect.h + 10)
        knob_rect.center = (self.knob_x, self.rect.centery)
        pygame.draw.rect(surf, outline, knob_rect)
        pygame.draw.rect(surf, (220, 190, 150), knob_rect.inflate(-6, -6))

    def set_from_mouse(self, mx):
        self.value = max(0.0, min(1.0, (mx - self.rect.x) / self.rect.w))

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.inflate(16, 16).collidepoint(event.pos):
                self.dragging = True
                self.set_from_mouse(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.set_from_mouse(event.pos[0])

# =========================
# Textos (ES/EN)
# =========================
TXT = {
    "es": {
        "title": "OPCIONES",
        "volume": "Volumen",
        "language": "Idioma",
        "spanish": "Español",
        "english": "English",
    },
    "en": {
        "title": "OPTIONS",
        "volume": "Volume",
        "language": "Language",
        "spanish": "Spanish",
        "english": "English",
    },
}

def _load_font(assets_dir: Path, size: int) -> pygame.font.Font:
    # Si tienes una fuente pixel en assets (p.ej. PressStart2P.ttf), úsala.
    candidates = ["pixel_font", "PressStart2P", "VT323"]
    for st in candidates:
        p = find_by_stem(assets_dir, st)
        if p and p.suffix.lower() in (".ttf", ".otf"):
            return pygame.font.Font(str(p), size)
    return pygame.font.SysFont("arial", size, bold=True)

# =========================
# Pantalla de OPCIONES
# =========================
def run(screen: pygame.Surface, assets_dir: Path):
    """
    Pantalla de OPCIONES:
    - Fondo con scroll infinito.
    - Slider de volumen (mouse y ← →).
    - Botones de idioma grandes SIN marco + hover zoom.
    - Ajustes persistentes en settings.json.
    Devuelve un dict con settings actualizados.
    """
    clock = pygame.time.Clock()
    W, H = screen.get_size()

    # Cargar settings actuales
    settings = load_settings(assets_dir)
    lang = settings["lang"]

    # Fondo con scroll
    background = load_image(assets_dir, ["Background_f", "Background_fondo"])
    background = pygame.transform.smoothscale(background, (W, H))
    bw, bh = background.get_size()
    scroll_x = 0
    SCROLL_SPEED = 2

    # Botón Back (imagen tuya con hover-zoom)
    back_img = load_image(assets_dir, ["btn_back", "regresar", "btn_regresar", "back"])
    desired_w = max(120, min(int(W * 0.12), 240))
    back_img = scale_to_width(back_img, desired_w)
    back_img_hover = scale_to_width(back_img, int(back_img.get_width() * 1.08))
    margin_x, margin_y = 10, 12

    # Fuentes
    title_font = _load_font(assets_dir, 96 if W < 1500 else 120)
    label_font = _load_font(assets_dir, 54)
    btn_font = _load_font(assets_dir, 40)

    # Slider de volumen (centrado)
    slider_w, slider_h = int(W*0.45), 28
    slider = Slider((W-slider_w)//2, int(H*0.36), slider_w, slider_h, settings["volume"])

    # Banderas (opcionales)
    flag_es = None
    flag_us = None
    try:
        flag_es = load_image(assets_dir, ["flag_es", "es_flag", "bandera_es"])
    except Exception:
        pass
    try:
        flag_us = load_image(assets_dir, ["flag_us", "us_flag", "bandera_us", "bandera_usa"])
    except Exception:
        pass

    # Botones de idioma GRANDES, sin marco y con hover_scale
    bw_lang, bh_lang = int(W*0.40), int(H*0.32)  # ← más grandes
    gap = int(W*0.07)
    left_x = (W - (bw_lang*2 + gap))//2
    y_lang = int(H*0.58)

    btn_es = Button(
        pygame.Rect(left_x, y_lang, bw_lang, bh_lang),
        TXT[lang]["spanish"], btn_font,
        on_click=lambda: set_lang("es"),
        img=flag_es, frame=False, hover_scale=1.35
    )
    btn_en = Button(
        pygame.Rect(left_x + bw_lang + gap, y_lang, bw_lang, bh_lang),
        TXT[lang]["english"], btn_font,
        on_click=lambda: set_lang("en"),
        img=flag_us, frame=False, hover_scale=1.35
    )

    def set_lang(code: str):
        nonlocal lang
        lang = code
        btn_es.text = TXT[lang]["spanish"]
        btn_en.text = TXT[lang]["english"]

    # Aplicar volumen al mixer desde el inicio (si hay mixer)
    try:
        pygame.mixer.music.set_volume(slider.value)
    except Exception:
        pass

    run._running = True
    while run._running:
        mouse = pygame.mouse.get_pos()
        clicked = False

        # --- Eventos ---
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                clicked = True
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    run._running = False
                if e.key == pygame.K_LEFT:
                    slider.value = max(0.0, slider.value - 0.05)
                elif e.key == pygame.K_RIGHT:
                    slider.value = min(1.0, slider.value + 0.05)

            # widgets
            slider.handle(e)
            btn_es.handle(e)
            btn_en.handle(e)

        # aplicar volumen si cambió
        try:
            pygame.mixer.music.set_volume(slider.value)
        except Exception:
            pass

        # --- Fondo con scroll infinito ---
        scroll_x -= SCROLL_SPEED
        if scroll_x <= -bw:
            scroll_x = 0
        screen.blit(background, (scroll_x, 0))
        screen.blit(background, (scroll_x + bw, 0))

        # --- Títulos/labels ---
        title_s = title_font.render(TXT[lang]["title"], True, (20, 15, 10))
        screen.blit(title_s, title_s.get_rect(midtop=(W//2, int(H*0.05))))
        vol_s = label_font.render(TXT[lang]["volume"], True, (20, 15, 10))
        screen.blit(vol_s, vol_s.get_rect(midtop=(W//2, int(H*0.26))))
        lang_s = label_font.render(TXT[lang]["language"], True, (20, 15, 10))
        screen.blit(lang_s, lang_s.get_rect(midtop=(W//2, int(H*0.48))))

        # --- UI ---
        slider.draw(screen)
        btn_es.draw(screen)
        btn_en.draw(screen)

        # Botón Back (imagen con hover zoom, el tuyo)
        back_draw_rect = back_img.get_rect(bottomleft=(margin_x, H - margin_y))
        if back_draw_rect.collidepoint(mouse):
            r = back_img_hover.get_rect(center=back_draw_rect.center)
            screen.blit(back_img_hover, r)
            current_back_rect = r
        else:
            screen.blit(back_img, back_draw_rect)
            current_back_rect = back_draw_rect

        # Click explícito sobre imagen Back (tu comportamiento original)
        if clicked and current_back_rect.collidepoint(mouse):
            run._running = False

        pygame.display.flip()
        clock.tick(60)

    # Guardar y devolver ajustes
    settings["volume"] = round(slider.value, 3)
    settings["lang"] = lang
    save_settings(assets_dir, settings)
    return settings
