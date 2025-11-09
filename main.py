# main.py
import pygame, os, math, traceback
import opciones
import play
import instrucciones
from pathlib import Path
from audio_shared import start_menu_music, ensure_menu_music_running, play_click

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

# ===== INICIA MÚSICA DE MENÚ (usa volumen maestro de audio_shared) =====
start_menu_music(ASSETS)

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

# Helper para lanzar niveles según número/dificultad
def _load_level_module(nivel: int, dificultad: str):
    # devuelve el módulo apropiado o lanza ImportError
    if nivel == 1:
        if dificultad == "facil":
            import levels.nivel1_facil as mod; return mod
        else:
            import levels.nivel1_dificil as mod; return mod
    elif nivel == 2:
        if dificultad == "facil":
            import levels.nivel2_facil as mod; return mod
        else:
            # === CAMBIO: Ahora cargamos el nuevo archivo difícil ===
            import levels.nivel2_dificil as mod; return mod
    elif nivel == 3:
        # adapta si tienes nivel3 modules
        import levels.nivel3_facil as mod; return mod

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
            ensure_menu_music_running(ASSETS)

            if isinstance(result, dict) and "nivel" in result and "dificultad" in result:
                nivel = int(result["nivel"])
                dif = result["dificultad"]
                # preferimos personaje_folder (carpeta ya normalizada) si existe
                personaje = result.get("personaje_folder") or result.get("personaje") or "PERSONAJE H"

                print("DEBUG: play.run result ->", result)
                # Cargar módulo correcto
                try:
                    nivel_mod = _load_level_module(nivel, dif)
                except Exception as e:
                    print("ERROR: no pude cargar módulo de nivel:", e)
                    traceback.print_exc()
                    ensure_menu_music_running(ASSETS)
                    pygame.display.flip(); clock.tick(60); t += 1; continue

                # Instanciamos/executamos el nivel según la API del módulo
                try:
                    # Asegurarnos de que la carpeta del personaje exista; si no, intentar alternativas
                    char_folder = personaje
                    pf = ASSETS / char_folder
                    if not pf.exists():
                        # probar invertir M/H si existe la otra
                        alt = None
                        if "M" in char_folder and (ASSETS / "PERSONAJE H").exists():
                            alt = "PERSONAJE H"
                        elif "H" in char_folder and (ASSETS / "PERSONAJE M").exists():
                            alt = "PERSONAJE M"
                        # intentar detectar carpeta con prefijo 'PERSONAJE' presente en assets
                        if alt is None:
                            for cand in ("PERSONAJE H", "PERSONAJE M", "personaje_h", "personaje_m"):
                                if (ASSETS / cand).exists():
                                    alt = cand
                                    break
                        if alt:
                            print(f"WARN: carpeta {pf} no existe. Usando alternativa {alt}.")
                            char_folder = alt
                        else:
                            print(f"WARN: carpeta {pf} no existe y no encontré alternativas. Uso 'PERSONAJE H' por defecto.")
                            char_folder = "PERSONAJE H"

                    # Buscar la clase del nivel en el módulo
                    class_name_candidates = [f"Nivel{nivel}Facil", f"Nivel{nivel}Dificil", f"Nivel{nivel}"]
                    NivelClass = None
                    for cname in class_name_candidates:
                        if hasattr(nivel_mod, cname):
                            NivelClass = getattr(nivel_mod, cname)
                            break

                    if NivelClass is not None:
                        
                        # ======================================================
                        # === CAMBIO 1: Detener la música ANTES de la clase ===
                        pygame.mixer.music.fadeout(1000) # 1 segundo
                        # ======================================================
                        
                        # preferimos constructor con char_folder
                        try:
                            level = NivelClass(screen, ASSETS, char_folder=char_folder)
                        except TypeError:
                            try:
                                level = NivelClass(screen, ASSETS, personaje=char_folder, dificultad=dif)
                            except TypeError:
                                level = NivelClass()

                        # loop del nivel
                        in_level = True
                        while in_level:
                            dt = clock.tick(60)
                            res = level.update(dt)
                            level.draw()
                            pygame.display.flip()
                            if res == "pause":
                                in_level = False
                            elif res == "home":
                                in_level = False
                            elif res == "quit":
                                in_level = False
                                running = False
                        ensure_menu_music_running(ASSETS)

                    elif hasattr(nivel_mod, "run"):
                        
                        # ======================================================
                        # === CAMBIO 2: Detener la música ANTES de .run() ===
                        pygame.mixer.music.fadeout(1000) # 1 segundo
                        # ======================================================
                        
                        # fallback a función run
                        try:
                            nivel_mod.run(screen, ASSETS, dificultad=dif, personaje=char_folder)
                        except TypeError:
                            nivel_mod.run(screen, ASSETS, personaje=char_folder, dificultad=dif)
                        ensure_menu_music_running(ASSETS)
                    else:
                        print("ERROR: módulo de nivel no tiene clase esperada ni función run().")
                        ensure_menu_music_running(ASSETS)

                except Exception as e:
                    print("ERROR dentro del nivel:", e)
                    traceback.print_exc()
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