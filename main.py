import pygame, os, math
from pathlib import Path

pygame.init()

# =========================
# RUTAS / CONFIG
# =========================
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
ASSETS = BASE_DIR / "assets"

# Usa estos prefijos tal como están en tu carpeta
STEMS = {
    "bg":    "Background_f",    # ej. Background_fondo.jpeg
    "title": "titulo_juego",    # ej. titulo_juego.png
    "play":  "btn_play",        # ej. btn_play.png
    "opc":   "btn_opc",         # ej. btn_opc.png
    "inst":  "btn_instruccio",  # ej. btn_instrucciones.png / btn_instruccio.png
}

SHOW_DEBUG_BORDERS = False  # True para ver rectángulos de debug

# =========================
# HELPERS: CARGAR SIN CONVERT
# =========================
def find_by_stem(stem: str) -> Path | None:
    """Devuelve el primer archivo que empieza con stem y tiene .png/.jpg/.jpeg."""
    exts = (".png", ".jpg", ".jpeg")
    # coincidencia exacta: stem.ext
    for ext in exts:
        p = ASSETS / f"{stem}{ext}"
        if p.exists():
            return p
    # prefijo: stem*ext (elige el nombre más corto)
    candidates = []
    for ext in exts:
        candidates += list(ASSETS.glob(f"{stem}*{ext}"))
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: len(p.name))[0]

def load_raw(stem: str):
    """Carga la imagen SIN convert/convert_alpha (eso se hace después de set_mode)."""
    p = find_by_stem(stem)
    if not p:
        raise FileNotFoundError(f"No encontré '{stem}*.png/.jpg/.jpeg' en {ASSETS}")
    surf = pygame.image.load(str(p))  # <- sin convert aquí
    print(f"[OK] Cargado: {p.name}")
    return surf, p

# Escalado suave por factor
def sscale(surf: pygame.Surface, factor: float) -> pygame.Surface:
    return pygame.transform.smoothscale(
        surf, (int(surf.get_width()*factor), int(surf.get_height()*factor))
    )

# Escalar a ancho fijo
def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    ratio = new_w / img.get_width()
    new_h = int(img.get_height() * ratio)
    return pygame.transform.smoothscale(img, (new_w, new_h))

# =========================
# CARGA EN CRUDO + CREAR VENTANA
# =========================
bg_raw, bg_path = load_raw(STEMS["bg"])
W, H = bg_raw.get_size()

screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Guardianes del Planeta - Menú")
clock = pygame.time.Clock()

# Ahora SÍ convertir (ya hay video mode)
background = bg_raw.convert()

title_raw,  title_path = load_raw(STEMS["title"])
play_raw,   play_path  = load_raw(STEMS["play"])
opc_raw,    opc_path   = load_raw(STEMS["opc"])
inst_raw,   inst_path  = load_raw(STEMS["inst"])

title_img = title_raw.convert_alpha() if title_path.suffix.lower()==".png" else title_raw.convert()
btn_jugar = play_raw.convert_alpha()  if play_path.suffix.lower()==".png"  else play_raw.convert()
btn_opc   = opc_raw.convert_alpha()   if opc_path.suffix.lower()==".png"   else opc_raw.convert()
btn_inst  = inst_raw.convert_alpha()  if inst_path.suffix.lower()==".png"  else inst_raw.convert()

# =========================
# ESCALADOS (normalizar por ancho)
# =========================
TITLE_SCALE = 1.35
title_img = sscale(title_img, TITLE_SCALE)
title_w, title_h = title_img.get_size()

# Ancho objetivo para TODOS los botones (ajústalo a tu gusto)
TARGET_BTN_W = int(W * 0.28)   # ~28% del ancho de pantalla
HOVER_SCALE  = 1.08            # hover 8% más grande

btn_jugar = scale_to_width(btn_jugar, TARGET_BTN_W)
btn_opc   = scale_to_width(btn_opc,   TARGET_BTN_W)
btn_inst  = scale_to_width(btn_inst,  TARGET_BTN_W)

# versiones hover (un poco más anchas, re-centradas al dibujar)
btn_jugar_h = scale_to_width(btn_jugar, int(TARGET_BTN_W * HOVER_SCALE))
btn_opc_h   = scale_to_width(btn_opc,   int(TARGET_BTN_W * HOVER_SCALE))
btn_inst_h  = scale_to_width(btn_inst,  int(TARGET_BTN_W * HOVER_SCALE))

# =========================
# LAYOUT (centrado y espaciado uniforme)
# =========================
j_w, j_h = btn_jugar.get_size()
o_w, o_h = btn_opc.get_size()
i_w, i_h = btn_inst.get_size()

TITLE_TOP  = int(H * 0.12)            # padding superior del título
start_y    = int(H * 0.44)            # inicio de la columna (debajo del título)
GAP        = max(16, int(j_h * 0.25)) # separación entre botones (25% de la altura del botón JUGAR)

rect_jugar = btn_jugar.get_rect(center=(W // 2, start_y))
rect_opc   = btn_opc.get_rect(center=(W // 2, rect_jugar.bottom + GAP + o_h // 2))
rect_inst  = btn_inst.get_rect(center=(W // 2, rect_opc.bottom + GAP + i_h // 2))


# =========================
# ANIMACIONES
# =========================
scroll_x = 0
SCROLL_SPEED = 2

t = 0
FLOAT_AMP   = 8
FLOAT_SPEED = 0.08

# =========================
# LOOP PRINCIPAL
# =========================
running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    clicked = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = True

    # Fondo con scroll infinito
    scroll_x -= SCROLL_SPEED
    if scroll_x <= -W:
        scroll_x = 0
    screen.blit(background, (scroll_x, 0))
    screen.blit(background, (scroll_x + W, 0))

    # Título flotando
    y_float = int(FLOAT_AMP * math.sin(t * FLOAT_SPEED))
    screen.blit(title_img, ((W - title_w)//2, TITLE_TOP + y_float))

    # Botones (hover + “saltito”)
    def draw_btn(img, img_hover, base_rect):
        if base_rect.collidepoint(mouse_pos):
            r = img_hover.get_rect(center=base_rect.center)
            r.y -= 2  # pequeño saltito al pasar
            screen.blit(img_hover, r)
            return r
        else:
            screen.blit(img, base_rect)
            return base_rect

    rj = draw_btn(btn_jugar, btn_jugar_h, rect_jugar)
    ro = draw_btn(btn_opc,   btn_opc_h,   rect_opc)
    ri = draw_btn(btn_inst,  btn_inst_h,  rect_inst)

    if SHOW_DEBUG_BORDERS:
        pygame.draw.rect(screen, (255, 0, 0), rj, 2)
        pygame.draw.rect(screen, (0, 255, 0), ro, 2)
        pygame.draw.rect(screen, (0, 0, 255), ri, 2)

    # Clicks
    if clicked:
        if rj.collidepoint(mouse_pos): print("🎮 JUGAR")
        elif ro.collidepoint(mouse_pos): print("⚙️ OPCIONES")
        elif ri.collidepoint(mouse_pos): print("📖 INSTRUCCIONES")

    pygame.display.flip()
    clock.tick(60)
    t += 1

pygame.quit()
