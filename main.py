import pygame, os, math, traceback
import opciones
import play
import instrucciones
import tutorial
import config # IMPORTANTE: Importar el config para traducciones
from pathlib import Path
from audio_shared import start_menu_music, ensure_menu_music_running, play_click

pygame.init()

# ===== RUTAS / CONFIG =====
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
ASSETS = BASE_DIR / "assets"

# === STEMS ===
STEMS = {
    "bg": "Background_f",
    "title": "titulo_juego",
    "play": "btn_play",
    "opc": "btn_opc",
    "inst": "btn_instrucciones", 
    "tut": "Tutorial", 
}
SHOW_DEBUG_BORDERS = False

# ==========================================================
# ✅ FUNCIÓN PARA REPRODUCIR VIDEO (MANUAL / ROBUSTA)
# ==========================================================
def reproducir_intro(screen, assets_dir):
    """
    Reproduce 'intro.mp4' dibujando los frames manualmente en Pygame.
    Esto evita el error de [WinError 2] por falta de ffplay.
    """
    video_path = assets_dir / "intro.mp4"
    
    if not video_path.exists():
        print(f"[INFO] No se encontró {video_path}, saltando intro.")
        return

    try:
        # Intentamos importar MoviePy (compatible con v1 y v2)
        try:
            from moviepy import VideoFileClip
        except ImportError:
            from moviepy.editor import VideoFileClip
        
        print("[INFO] Cargando video de introducción...")
        
        # Cargar el video
        clip = VideoFileClip(str(video_path))
        
        # --- AJUSTE DE TAMAÑO Y POSICIÓN ---
        screen_w, screen_h = screen.get_size()
        video_w, video_h = clip.size
        
        # Calcular escala para que quepa en pantalla (85% del tamaño disponible)
        # manteniendo la relación de aspecto original para no perder calidad
        scale = min(screen_w / video_w, screen_h / video_h) * 0.85
        new_w = int(video_w * scale)
        new_h = int(video_h * scale)
        
        # Calcular posición para centrar
        pos_x = (screen_w - new_w) // 2
        pos_y = (screen_h - new_h) // 2
        
        if hasattr(clip, "resized"): # MoviePy v2
            clip = clip.resized(new_size=(new_w, new_h))
        else: # MoviePy v1
            clip = clip.resize(newsize=(new_w, new_h))
        
        # --- REPRODUCTOR MANUAL ---
        # Extraemos el audio a un archivo temporal para que Pygame lo toque
        # Esto evita depender de herramientas externas para el audio
        audio_temp = assets_dir / "temp_intro_audio.mp3"
        
        if clip.audio:
            # logger=None evita que llene la consola de barras de carga
            print("[INFO] Procesando audio del video...")
            try:
                clip.audio.write_audiofile(str(audio_temp), logger=None)
                pygame.mixer.music.load(str(audio_temp))
                pygame.mixer.music.play()
            except Exception as e:
                print(f"⚠️ No se pudo cargar el audio del video: {e}")

        clock = pygame.time.Clock()
        fps = clip.fps
        running = True
        
        print("[INFO] Reproduciendo video...")
        
        # Iteramos sobre cada cuadro del video
        start_ticks = pygame.time.get_ticks()
        
        for frame in clip.iter_frames(fps=fps, dtype="uint8"):
            if not running:
                break
            
            # Manejo de eventos (para poder saltar el video con click o tecla)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    running = False # Saltar intro
            
            # Convertir el frame de MoviePy (numpy array) a Pygame Surface
            # swapaxes es necesario porque MoviePy usa (y, x) y Pygame (x, y)
            video_surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
            
            # 1. Llenar fondo de negro
            screen.fill((0, 0, 0))
            # 2. Dibujar video centrado
            screen.blit(video_surf, (pos_x, pos_y))
            pygame.display.flip()
            
            # Controlar la velocidad (FPS)
            clock.tick(fps)
        
        # Limpieza
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        clip.close()
        
        # Borrar el archivo de audio temporal
        if audio_temp.exists():
            try:
                os.remove(audio_temp)
            except:
                pass
        
        # Restaurar título
        pygame.display.set_caption("Guardianes del Planeta")
        
    except ImportError:
        print("⚠️ [AVISO] Instala moviepy para ver el intro: pip install moviepy")
    except Exception as e:
        print(f"⚠️ [ERROR] Saltando intro por error interno: {e}")


# ===== HELPERS IMG =====
def find_by_stem(stem: str) -> Path | None:
    exts = (".png", ".jpg", ".jpeg")
    for ext in exts:
        p = ASSETS / f"{stem}{ext}"
        if p.exists():
            return p
    cands = []
    for ext in exts:
        cands += list(ASSETS.glob(f"{stem}*{ext}"))
    return sorted(cands, key=lambda p: len(p.name))[0] if cands else None

def load_raw(stem: str):
    # === CAMBIO: TRADUCCIÓN ===
    # Buscamos el nombre real según el idioma actual en config
    real_name = config.obtener_nombre(stem)
    
    p = find_by_stem(real_name)
    # Si no encuentra la versión traducida, intenta la original (fallback)
    if not p and real_name != stem:
        p = find_by_stem(stem)
        
    if not p:
        # Fallback específico para Tutorial si no existe
        if stem == "Tutorial":
            print(f"[WARN] No encontré '{stem}', usando superficie vacía temporal.")
            s = pygame.Surface((200, 50))
            s.fill((100, 100, 200))
            return s, Path("dummy.png")
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
# 1. Cargar idioma desde opciones
opciones.load_lang(ASSETS)
# 2. Sincronizar config.py con lo que cargó opciones
if hasattr(opciones, "IDIOMA_ACTUAL"):
    config.cambiar_idioma(opciones.IDIOMA_ACTUAL)

bg_raw, _ = load_raw(STEMS["bg"])
W, H = bg_raw.get_size()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Guardianes del Planeta")
clock = pygame.time.Clock()

# ==========================================================
# 🎬 REPRODUCIR INTRO ANTES DE CARGAR EL MENÚ
# ==========================================================
reproducir_intro(screen, ASSETS)

# Continuar carga normal...
background = bg_raw.convert()

# Variables globales para UI
title_img = None
btn_jugar = None
btn_opc = None
btn_inst = None
btn_tut = None
btn_jugar_h = None
btn_opc_h = None
btn_inst_h = None
btn_tut_h = None
rect_jugar = None
rect_opc = None
rect_inst = None
rect_tut = None
title_w = 0
title_h = 0

# === Definición de TITLE_TOP ===
TITLE_TOP = int(H * 0.12)

# === FUNCIÓN DE RECARGA (Para actualizar idioma) ===
def reload_ui():
    global title_img, btn_jugar, btn_opc, btn_inst, btn_tut
    global btn_jugar_h, btn_opc_h, btn_inst_h, btn_tut_h
    global rect_jugar, rect_opc, rect_inst, rect_tut, title_w, title_h

    # Cargar imágenes (load_raw usa config)
    title_raw, title_path = load_raw(STEMS["title"])
    play_raw, play_path = load_raw(STEMS["play"])
    opc_raw, opc_path = load_raw(STEMS["opc"])
    inst_raw, inst_path = load_raw(STEMS["inst"])
    tut_raw, tut_path = load_raw(STEMS["tut"])

    # Convertir
    t_img = title_raw.convert_alpha() if title_path.suffix.lower()==".png" else title_raw.convert()
    b_play = play_raw.convert_alpha() if play_path.suffix.lower()==".png" else play_raw.convert()
    b_opc = opc_raw.convert_alpha() if opc_path.suffix.lower()==".png" else opc_raw.convert()
    b_inst = inst_raw.convert_alpha() if inst_path.suffix.lower()==".png" else inst_raw.convert()
    b_tut = tut_raw.convert_alpha() if tut_path.suffix.lower()==".png" else tut_raw.convert()

    # ===== ESCALADOS =====
    TITLE_SCALE = 1.00
    title_img = sscale(t_img, TITLE_SCALE)
    title_w, title_h = title_img.get_size()

    TARGET_BTN_W = int(W * 0.28)
    HOVER_SCALE = 1.08

    btn_jugar = scale_to_width(b_play, TARGET_BTN_W)
    btn_opc = scale_to_width(b_opc, TARGET_BTN_W)
    btn_inst = scale_to_width(b_inst, TARGET_BTN_W)
    btn_tut = scale_to_width(b_tut, int(TARGET_BTN_W * 0.8)) 

    btn_jugar_h = scale_to_width(btn_jugar, int(TARGET_BTN_W * HOVER_SCALE))
    btn_opc_h = scale_to_width(btn_opc, int(TARGET_BTN_W * HOVER_SCALE))
    btn_inst_h = scale_to_width(btn_inst, int(TARGET_BTN_W * HOVER_SCALE))
    btn_tut_h = scale_to_width(btn_tut, int((TARGET_BTN_W * 0.8) * HOVER_SCALE))

    # ===== LAYOUT =====
    GAP_TITLE_BTN = 20
    GAP_BOTONES = 15 

    start_y = TITLE_TOP + title_h + GAP_TITLE_BTN

    rect_jugar = btn_jugar.get_rect(center=(W // 2, 0))
    rect_jugar.top = start_y
    
    rect_opc = btn_opc.get_rect(center=(W // 2, 0))
    rect_opc.top = rect_jugar.bottom + GAP_BOTONES
    
    rect_inst = btn_inst.get_rect(center=(W // 2, 0))
    rect_inst.top = rect_opc.bottom + GAP_BOTONES
    
    rect_tut = btn_tut.get_rect(bottomright=(W - 30, H - 80)) 

    MARGIN_BOTTOM = 8
    overflow = rect_inst.bottom - (H - MARGIN_BOTTOM)
    if overflow > 0:
        rect_jugar.move_ip(0, -overflow)
        rect_opc.move_ip(0, -overflow)
        rect_inst.move_ip(0, -overflow)

# Cargar UI inicial
reload_ui()

# ===== INICIA MÚSICA DE MENÚ =====
# Se inicia DESPUÉS del video para que no se mezclen los audios
start_menu_music(ASSETS)

# ===== ANIM =====
scroll_x = 0
SCROLL_SPEED = 2
t = 0
FLOAT_AMP = 8
FLOAT_SPEED = 0.08

# Helper para lanzar niveles según número/dificultad
def _load_level_module(nivel: int, dificultad: str):
    if nivel == 1:
        if dificultad == "facil":
            import levels.nivel1_facilitopapa as mod
            return mod
        else:
            import levels.nivel1_dificil as mod
            return mod
    elif nivel == 2:
        if dificultad == "facil":
            import levels.nivel2_facil as mod
            return mod
        else:
            import levels.nivel2_dificil as mod
            return mod
    elif nivel == 3:
        if dificultad == "facil":
            import levels.nivel3_facil as mod
            return mod
        else:
            import levels.nivel3_dificil as mod
            return mod 

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
    if scroll_x <= -W:
        scroll_x = 0
    screen.blit(background, (scroll_x, 0))
    screen.blit(background, (scroll_x + W, 0))

    y_float = int(FLOAT_AMP * math.sin(t * FLOAT_SPEED))
    screen.blit(title_img, ((W - title_w)//2, TITLE_TOP + y_float))

    # Botones (hover)
    def draw_btn(img, img_hover, base_rect):
        if base_rect.collidepoint(mouse_pos):
            r = img_hover.get_rect(center=base_rect.center)
            r.y -= 2
            screen.blit(img_hover, r)
            return r
        screen.blit(img, base_rect)
        return base_rect

    rj = draw_btn(btn_jugar, btn_jugar_h, rect_jugar)
    ro = draw_btn(btn_opc, btn_opc_h, rect_opc)
    ri = draw_btn(btn_inst, btn_inst_h, rect_inst)
    rt = draw_btn(btn_tut, btn_tut_h, rect_tut) 

    if SHOW_DEBUG_BORDERS:
        pygame.draw.rect(screen, (255, 0, 0), rj, 2)
        pygame.draw.rect(screen, (0, 255, 0), ro, 2)
        pygame.draw.rect(screen, (0, 0, 255), ri, 2)
        pygame.draw.rect(screen, (255, 255, 0), rt, 2)

    # Clicks
    if clicked:
        # --- BOTÓN JUGAR ---
        if rj.collidepoint(mouse_pos):
            play_click(ASSETS)
            result = play.run(screen, ASSETS)
            ensure_menu_music_running(ASSETS)

            if isinstance(result, dict) and "nivel" in result and "dificultad" in result:
                nivel = int(result["nivel"])
                dif = result["dificultad"]
                personaje = result.get("personaje_folder") or result.get("personaje") or "PERSONAJE H"

                print("DEBUG: play.run result ->", result)
                try:
                    nivel_mod = _load_level_module(nivel, dif)
                except Exception as e:
                    print("ERROR: no pude cargar módulo de nivel:", e)
                    traceback.print_exc()
                    ensure_menu_music_running(ASSETS)
                    pygame.display.flip()
                    clock.tick(60)
                    t += 1
                    continue

                try:
                    char_folder = personaje
                    pf = ASSETS / char_folder
                    if not pf.exists():
                        alt = None
                        if "M" in char_folder and (ASSETS / "PERSONAJE H").exists():
                            alt = "PERSONAJE H"
                        elif "H" in char_folder and (ASSETS / "PERSONAJE M").exists():
                            alt = "PERSONAJE M"
                        if alt is None:
                            for cand in ("PERSONAJE H", "PERSONAJE M", "personaje_h", "personaje_m"):
                                if (ASSETS / cand).exists():
                                    alt = cand
                                    break
                        if alt:
                            char_folder = alt
                        else:
                            char_folder = "PERSONAJE H"

                    class_name_candidates = [f"Nivel{nivel}Facil", f"Nivel{nivel}Dificil", f"Nivel{nivel}"]
                    NivelClass = None
                    for cname in class_name_candidates:
                        if hasattr(nivel_mod, cname):
                            NivelClass = getattr(nivel_mod, cname)
                            break

                    if NivelClass is not None:
                        pygame.mixer.music.fadeout(1000) 
                        try:
                            level = NivelClass(screen, ASSETS, char_folder=char_folder)
                        except TypeError:
                            try:
                                level = NivelClass(screen, ASSETS, personaje=char_folder, dificultad=dif)
                            except TypeError:
                                level = NivelClass()
        
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
                        pygame.mixer.music.fadeout(1000) 
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

            pygame.display.flip()
            clock.tick(60)
            t += 1
            continue

        # --- BOTÓN OPCIONES ---
        elif ro.collidepoint(mouse_pos):
            play_click(ASSETS)
            _ = opciones.run(screen, ASSETS)
            
            # Sincronizar idioma
            if hasattr(opciones, "IDIOMA_ACTUAL"):
                config.cambiar_idioma(opciones.IDIOMA_ACTUAL)
            
            reload_ui() 
            ensure_menu_music_running(ASSETS)
            pygame.display.flip()
            clock.tick(60)
            t += 1
            continue

        # --- BOTÓN INSTRUCCIONES ---
        elif ri.collidepoint(mouse_pos):
            play_click(ASSETS)
            _ = instrucciones.run(screen, ASSETS)
            ensure_menu_music_running(ASSETS)
            pygame.display.flip()
            clock.tick(60)
            t += 1
            continue
        
        # --- BOTÓN TUTORIAL ---
        elif rt.collidepoint(mouse_pos):
            play_click(ASSETS)
            # Tutorial lo busca solo en config
            tutorial.run(screen, ASSETS, personaje="PERSONAJE H") 
            
            ensure_menu_music_running(ASSETS)
            pygame.display.flip()
            clock.tick(60)
            t += 1
            continue

    pygame.display.flip()
    clock.tick(60)
    t += 1

pygame.quit()