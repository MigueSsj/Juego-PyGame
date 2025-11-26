from pathlib import Path
import pygame
import config # <--- 1. IMPORTAR CONFIGURACIÓN
from audio_shared import (
    load_master_volume,
    set_music_volume_now,
    save_master_volume,
    play_click,
    set_sfx_volume_now,
)
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
    
    # === MEJORA: TRADUCCIÓN Y FALLBACK ROBUSTO ===
    candidates = []
    if stems:
        key = stems[0]
        # 1. Agregar el nombre traducido (real_name) como primera opción
        real_name = config.obtener_nombre(key)
        candidates.append(real_name)
        
        # 2. Agregar los stems originales como opciones de fallback
        for stem in stems:
            if stem not in candidates:
                candidates.append(stem)
        
        
    # Usamos la lista de candidatos que ahora incluye la traducción y los fallbacks
    for stem in candidates:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
    
    # Fallback: crea una superficie rosa si no encuentra la imagen para que no crashee
    print(f"AVISO: No se encontró imagen para {stems}, usando cuadro rosa.")
    surf = pygame.Surface((64, 64))
    surf.fill((255, 0, 255))
    return surf

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height()*r)))

# =========================
# Persistencia simple de idioma
# =========================
def _lang_path_from_assets(assets_dir: Path) -> Path:
    return assets_dir.parent / "lang.txt"

def load_lang(assets_dir: Path) -> str:
    p = _lang_path_from_assets(assets_dir)
    try:
        if p.exists():
            s = p.read_text(encoding="utf-8").strip().lower()
            lang = "en" if s == "en" else "es"
            # === CAMBIO: Sincronizar config al cargar ===
            config.cambiar_idioma(lang) 
            return lang
    except Exception:
        pass
    return "es"

def save_lang(assets_dir: Path, code: str) -> None:
    try:
        _lang_path_from_assets(assets_dir).write_text(code, encoding="utf-8")
    except Exception:
        pass

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
        self.frame = frame
        self.hover_scale = hover_scale

    def draw(self, surf: pygame.Surface):
        temp = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        outline = (30, 20, 15)
        bg = (205, 170, 125) if not self.hover else (225, 190, 145)

        if self.frame:
            pygame.draw.rect(temp, outline, temp.get_rect())
            pygame.draw.rect(temp, bg, temp.get_rect().inflate(-6, -6))

        if self.img:
            img = self.img
            # Si NO hay texto, permitimos que la imagen sea más grande y centrada
            if not self.text:
                max_w = int(self.rect.w * 0.85)
                max_h = int(self.rect.h * 0.85)
            else:
                max_w = int(self.rect.w * (0.7 if self.frame else 0.9))
                max_h = int(self.rect.h * (0.55 if self.frame else 0.6))

            scale = min(max_w / img.get_width(), max_h / img.get_height(), 1.0)
            
            # Aplicar escala
            if scale < 1.0 or (not self.text and scale != 1.0): 
                img = pygame.transform.smoothscale(img, (int(img.get_width()*scale), int(img.get_height()*scale)))
            
            if self.text:
                y_offset = -self.rect.h*0.12 if self.frame else -self.rect.h*0.05
                img_rect = img.get_rect(center=(self.rect.w//2, int(self.rect.h//2 + y_offset)))
            else:
                img_rect = img.get_rect(center=(self.rect.w//2, self.rect.h//2))
            
            temp.blit(img, img_rect)

        # Solo dibujar texto si existe
        if self.text:
            label = self.font.render(self.text, True, (25, 20, 15))
            if self.img:
                label_rect = label.get_rect(center=(self.rect.w//2, int(self.rect.h*0.72)))
            else:
                label_rect = label.get_rect(center=(self.rect.w//2, self.rect.h//2))
            temp.blit(label, label_rect)

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

def _load_font(assets_dir: Path, size: int) -> pygame.font.Font:
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
    clock = pygame.time.Clock()
    W, H = screen.get_size()

    # Idioma desde archivo de texto
    lang = load_lang(assets_dir)

    # Fondo con scroll
    background = load_image(assets_dir, ["Background_f", "Background_fondo"])
    background = pygame.transform.smoothscale(background, (W, H))
    bw, bh = background.get_size()
    scroll_x = 0
    SCROLL_SPEED = 2

    # --- CARGA DE IMÁGENES DE TÍTULOS (Modificado para recargar) ---
    # Usamos una función interna para poder refrescar las imágenes cuando cambie el idioma
    
    title_main_img = None
    title_vol_img = None
    title_lang_img = None
    back_img = None
    back_img_hover = None
    
    desired_w = max(120, min(int(W * 0.12), 240)) # Cálculo de tu código original

    def recargar_imagenes():
        nonlocal title_main_img, title_vol_img, title_lang_img, back_img, back_img_hover
        
        # Cargamos usando las claves de config.py
        # Si estás en inglés, load_image buscará "titulo_opcionesus.png" automáticamente
        tm = load_image(assets_dir, ["titulo_opciones", "opciones_titulo"])
        tv = load_image(assets_dir, ["titulo_volume", "volumen_titulo"]) # Usamos 'titulo_volume' como stem principal
        tl = load_image(assets_dir, ["titulo_idioma", "idioma_titulo"])
        bk = load_image(assets_dir, ["btn_back", "regresar", "btn_regresar", "back"])

        # Escalamos (lógica original)
        title_main_img = scale_to_width(tm, int(W * 0.45))
        title_vol_img = scale_to_width(tv, int(W * 0.25))
        title_lang_img = scale_to_width(tl, int(W * 0.25))

        back_img = scale_to_width(bk, desired_w)
        back_img_hover = scale_to_width(back_img, int(back_img.get_width() * 1.08))

    recargar_imagenes() # Carga inicial

    margin_x, margin_y = 10, 12
    # Rect del botón back (lógica original)
    # Nota: back_img ya está cargado por recargar_imagenes
    # Necesitamos calcular su rect aquí para el bucle
    # Como back_img cambia, mejor calculamos el rect en el bucle o usamos una posición fija
    # Usaremos posición fija basada en tu código: bottomleft
    
    # Fuentes
    btn_font = _load_font(assets_dir, 40)

    # Slider de volumen
    slider_w, slider_h = int(W*0.45), 28
    vol_inicial = load_master_volume(assets_dir)
    # Ajustamos un poco la Y del slider
    slider = Slider((W-slider_w)//2, int(H*0.40), slider_w, slider_h, vol_inicial)

    # Banderas
    flag_es = None
    flag_us = None
    try:
        flag_es = load_image(assets_dir, ["flag_es", "es_flag", "bandera_es"])
    except Exception: pass
    try:
        flag_us = load_image(assets_dir, ["flag_us", "us_flag", "bandera_us", "bandera_usa"])
    except Exception: pass

    # Botones de idioma GRANDES, sin marco y con hover_scale
    bw_lang, bh_lang = int(W*0.40), int(H*0.32)
    gap = int(W*0.07)
    left_x = (W - (bw_lang*2 + gap))//2
    y_lang = int(H*0.55) # Bajamos un poco la posición

    # === FUNCIÓN DE CAMBIO DE IDIOMA ===
    def cambiar_idioma_click(nuevo_idioma):
        nonlocal lang
        lang = nuevo_idioma
        config.cambiar_idioma(nuevo_idioma) # Actualizar global
        save_lang(assets_dir, nuevo_idioma) # Guardar en disco
        play_click(assets_dir)
        recargar_imagenes() # Actualizar títulos y botones visualmente

    # Botones conectados a la función de cambio
    btn_es = Button(
        pygame.Rect(left_x, y_lang, bw_lang, bh_lang),
        "", # Texto vacío
        btn_font,
        on_click=lambda: cambiar_idioma_click("es"),
        img=flag_es, frame=False, hover_scale=1.2
    )
    btn_en = Button(
        pygame.Rect(left_x + bw_lang + gap, y_lang, bw_lang, bh_lang),
        "", # Texto vacío
        btn_font,
        on_click=lambda: cambiar_idioma_click("en"),
        img=flag_us, frame=False, hover_scale=1.2
    )

    run._running = True
    while run._running:
        mouse = pygame.mouse.get_pos()
        clicked = False
        
        # Recalcular rect de back_img por si cambió de tamaño al recargar
        back_draw_rect = back_img.get_rect(bottomleft=(margin_x, H - margin_y))

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                clicked = True
                if back_draw_rect.collidepoint(mouse):
                    play_click(assets_dir)
                    run._running = False

            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    play_click(assets_dir)
                    run._running = False
                if e.key == pygame.K_LEFT:
                    slider.value = max(0.0, slider.value - 0.05)
                elif e.key == pygame.K_RIGHT:
                    slider.value = min(1.0, slider.value + 0.05)

            # widgets
            slider.handle(e)
            btn_es.handle(e)
            btn_en.handle(e)

        # Volumen maestro en caliente
        set_music_volume_now(assets_dir, slider.value)
        set_sfx_volume_now(assets_dir, slider.value)

        # Fondo scroll
        scroll_x -= SCROLL_SPEED
        if scroll_x <= -bw:
            scroll_x = 0
        screen.blit(background, (scroll_x, 0))
        screen.blit(background, (scroll_x + bw, 0))

        # --- DIBUJAR IMÁGENES DE TÍTULOS ---
        screen.blit(title_main_img, title_main_img.get_rect(midtop=(W//2, int(H*0.09))))
        screen.blit(title_vol_img, title_vol_img.get_rect(midtop=(W//2, int(H*0.26))))
        screen.blit(title_lang_img, title_lang_img.get_rect(midtop=(W//2, int(H*0.50))))

        # UI
        slider.draw(screen)
        btn_es.draw(screen)
        btn_en.draw(screen)

        # Back con hover zoom
        if back_draw_rect.collidepoint(mouse):
            r = back_img_hover.get_rect(center=back_draw_rect.center)
            screen.blit(back_img_hover, r)
        else:
            screen.blit(back_img, back_draw_rect)

        pygame.display.flip()
        clock.tick(60)

    # Guardar idioma + volumen maestro al salir
    save_lang(assets_dir, lang)
    save_master_volume(assets_dir, slider.value)
    
    return {"volume": round(slider.value, 3), "lang": lang}