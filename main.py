# main.py
import pygame, os, math
import opciones
import play
import instrucciones
from pathlib import Path

pygame.init()

# ===== RUTAS / CONFIG =====
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
ASSETS = BASE_DIR / "assets"

STEMS = {
    "bg":    "Background_f",
    "title": "titulo_juego",
    "play":  "btn_play",
    "opc":   "btn_opc",
    "inst":  "btn_instruccio",
}
SHOW_DEBUG_BORDERS = False

# ===== MÚSICA Y SONIDOS =====
def _audio_find(assets_dir: Path, stems: list[str], exts=(".ogg", ".wav", ".mp3")) -> Path | None:
    audio_dir = assets_dir / "msuiquita"
    if not audio_dir.exists(): return None
    # exacto
    for st in stems:
        for ext in exts:
            p = audio_dir / f"{st}{ext}"
            if p.exists(): return p
    # prefijo
    for st in stems:
        for ext in exts:
            cands = list(audio_dir.glob(f"{st}*{ext}"))
            if cands:
                return sorted(cands, key=lambda p: len(p.name))[0]
    return None

def start_menu_music(assets_dir: Path, volume: float = 0.75) -> None:
    try:
        p = _audio_find(assets_dir, ["musica inicio", "musica_inicio", "inicio"])
        if not p: return
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(str(p))
        pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
        pygame.mixer.music.play(-1)
        print(f"[MÚSICA] Menú: {p.name}")
    except Exception as e:
        print(f"[MÚSICA] No se pudo reproducir: {e}")

def ensure_menu_music_running(assets_dir: Path) -> None:
    try:
        if not pygame.mixer.get_init() or not pygame.mixer.music.get_busy():
            start_menu_music(assets_dir)
    except Exception:
        pass

_click_snd: pygame.mixer.Sound | None = None
def get_click_sound(assets_dir: Path) -> pygame.mixer.Sound | None:
    global _click_snd
    if _click_snd is not None: return _click_snd
    try:
        p = _audio_find(assets_dir, ["musica_botoncitos", "click", "boton"])
        if not p: return None
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        _click_snd = pygame.mixer.Sound(str(p))
        _click_snd.set_volume(0.2)  # volumen suave del “sonidito”
    except Exception as e:
        print(f"[SFX] No se pudo cargar el click: {e}")
        _click_snd = None
    return _click_snd

def play_click(assets_dir: Path):
    snd = get_click_sound(assets_dir)
    if snd:
        try: snd.play()
        except Exception: pass

# ===== HELPERS IMG =====
def find_by_stem(stem: str) -> Path | None:
    exts = (".png", ".jpg", ".jpeg")
    for ext in exts:
        p = ASSETS / f"{stem}{ext}"
        if p.exists(): return p
    cands = []
    for ext in exts:
        cands += list(ASSETS.glob(f"{stem}*{ext}"))
    return sorted(cands, key=lambda p: len(p.name))[0] if cands else None

def load_raw(stem: str):
    p = find_by_stem(stem)
    if not p:
        raise FileNotFoundError(f"No encontré '{stem}*.png/.jpg/.jpeg' en {ASSETS}")
    surf = pygame.image.load(str(p))
    print(f"[OK] Cargado: {p.name}")
    return surf, p

def sscale(surf: pygame.Surface, factor: float) -> pygame.Surface:
    return pygame.transform.smoothscale(
        surf, (int(surf.get_width()*factor), int(surf.get_height()*factor))
    )

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    ratio = new_w / img.get_width()
    new_h = int(img.get_height() * ratio)
    return pygame.transform.smoothscale(img, (new_w, new_h))

# ===== CARGA + VENTANA =====
bg_raw, _ = load_raw(STEMS["bg"])
W, H = bg_raw.get_size()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Guardianes del Planeta")
clock = pygame.time.Clock()
background = bg_raw.convert()

title_raw,  title_path = load_raw(STEMS["title"])
play_raw,   play_path  = load_raw(STEMS["play"])
opc_raw,    opc_path   = load_raw(STEMS["opc"])
inst_raw,   inst_path  = load_raw(STEMS["inst"])

title_img = title_raw.convert_alpha() if title_path.suffix.lower()==".png" else title_raw.convert()
btn_jugar = play_raw.convert_alpha()  if play_path.suffix.lower()==".png"  else play_raw.convert()
btn_opc   = opc_raw.convert_alpha()   if opc_path.suffix.lower()==".png"   else opc_raw.convert()
btn_inst  = inst_raw.convert_alpha()  if inst_path.suffix.lower()==".png"  else inst_raw.convert()

# ===== INICIA MÚSICA DE MENÚ =====
start_menu_music(ASSETS, volume=0.75)
get_click_sound(ASSETS)  # pre-carga sfx

# ===== ESCALADOS =====
TITLE_SCALE = 1.00
title_img = sscale(title_img, TITLE_SCALE)
title_w, title_h = title_img.get_size()

TARGET_BTN_W = int(W * 0.28)
HOVER_SCALE  = 1.08

btn_jugar = scale_to_width(btn_jugar, TARGET_BTN_W)
btn_opc   = scale_to_width(btn_opc,   TARGET_BTN_W)
btn_inst  = scale_to_width(btn_inst,  TARGET_BTN_W)

btn_jugar_h = scale_to_width(btn_jugar, int(TARGET_BTN_W * HOVER_SCALE))
btn_opc_h   = scale_to_width(btn_opc,   int(TARGET_BTN_W * HOVER_SCALE))
btn_inst_h  = scale_to_width(btn_inst,  int(TARGET_BTN_W * HOVER_SCALE))

# ===== LAYOUT =====
TITLE_TOP      = int(H * 0.12)
GAP_TITLE_BTN  = 20
GAP_BOTONES    = 20

start_y = TITLE_TOP + title_h + GAP_TITLE_BTN

rect_jugar = btn_jugar.get_rect(center=(W // 2, 0)); rect_jugar.top = start_y
rect_opc   = btn_opc.get_rect(center=(W // 2, 0));   rect_opc.top   = rect_jugar.bottom + GAP_BOTONES
rect_inst  = btn_inst.get_rect(center=(W // 2, 0));  rect_inst.top  = rect_opc.bottom   + GAP_BOTONES

MARGIN_BOTTOM = 8
overflow = rect_inst.bottom - (H - MARGIN_BOTTOM)
if overflow > 0:
    rect_jugar.move_ip(0, -overflow)
    rect_opc.move_ip(0, -overflow)
    rect_inst.move_ip(0, -overflow)

# ===== ANIM =====
scroll_x = 0
SCROLL_SPEED = 2
t = 0
FLOAT_AMP   = 8
FLOAT_SPEED = 0.08

# ===== LOOP =====
running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    clicked = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = True

    # Fondo + título
    scroll_x -= SCROLL_SPEED
    if scroll_x <= -W: scroll_x = 0
    screen.blit(background, (scroll_x, 0))
    screen.blit(background, (scroll_x + W, 0))

    y_float = int(FLOAT_AMP * math.sin(t * FLOAT_SPEED))
    screen.blit(title_img, ((W - title_w)//2, TITLE_TOP + y_float))

    # Botones (hover)
    def draw_btn(img, img_hover, base_rect):
        if base_rect.collidepoint(mouse_pos):
            r = img_hover.get_rect(center=base_rect.center); r.y -= 2
            screen.blit(img_hover, r); return r
        screen.blit(img, base_rect); return base_rect

    rj = draw_btn(btn_jugar, btn_jugar_h, rect_jugar)
    ro = draw_btn(btn_opc,   btn_opc_h,   rect_opc)
    ri = draw_btn(btn_inst,  btn_inst_h,  rect_inst)

    if SHOW_DEBUG_BORDERS:
        pygame.draw.rect(screen, (255, 0, 0), rj, 2)
        pygame.draw.rect(screen, (0, 255, 0), ro, 2)
        pygame.draw.rect(screen, (0, 0, 255), ri, 2)

    # Clicks
    if clicked:
        if rj.collidepoint(mouse_pos):
            play_click(ASSETS)
            result = play.run(screen, ASSETS)  # selector niveles + dificultad + personaje
            # Al volver del selector/nivel, si no suena la música, reanúdala:
            ensure_menu_music_running(ASSETS)

            if isinstance(result, dict) and "nivel" in result and "dificultad" in result:
                nivel = result["nivel"]
                dif = result["dificultad"]
                personaje = result.get("personaje", "EcoGuardian")
                if nivel == 1 and dif == "facil":
                    from levels import nivel1_facil as lv
                    lv.run(screen, ASSETS, personaje=personaje, dificultad="Fácil")
                elif nivel == 1 and dif == "dificil":
                    from levels import nivel1_facil as lv  # temporal
                    lv.run(screen, ASSETS, personaje=personaje, dificultad="Difícil")
                ensure_menu_music_running(ASSETS)

            pygame.display.flip(); clock.tick(60); t += 1; continue

        elif ro.collidepoint(mouse_pos):
            play_click(ASSETS)
            _ = opciones.run(screen, ASSETS)
            ensure_menu_music_running(ASSETS)
            pygame.display.flip(); clock.tick(60); t += 1; continue

        elif ri.collidepoint(mouse_pos):
            play_click(ASSETS)
            _ = instrucciones.run(screen, ASSETS)
            ensure_menu_music_running(ASSETS)
            pygame.display.flip(); clock.tick(60); t += 1; continue

    pygame.display.flip()
    clock.tick(60)
    t += 1

pygame.quit()
