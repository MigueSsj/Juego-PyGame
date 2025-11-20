from __future__ import annotations
import pygame
import sys
import re
import math
from pathlib import Path
from typing import Optional, List, Tuple

# --- Importar música (con fallback) ---
try:
    from audio_shared import start_level_music, start_suspense_music, stop_level_music, play_sfx
except ImportError:
    print("WARN: No se pudo importar audio_shared. La música no funcionará.")
    def start_level_music(assets_dir: Path): pass
    def start_suspense_music(assets_dir: Path): pass
    def stop_level_music(): pass
    def play_sfx(*args, **kwargs): pass # Fallback

# --- Colores ---
BLANCO = (255, 255, 255); NEGRO = (0, 0, 0); VERDE = (0, 255, 0)
GRIS = (100, 100, 100); ROJO_OSCURO = (100, 0, 0)
# === CAMBIO: Añadido color para debug ===
DEBUG_COLOR_ROJO = (255, 0, 0)

# --- Constantes del Nivel ---
TIEMPO_PARA_REPARAR = 120  # 120 frames ~= 2s a 60fps
TOTAL_MS = 80_000          # 80 segundos
SUSPENSE_TIME_MS = 30_000  # 30 segundos

# ---------------------------
# Helpers rápidos y cache de imágenes
# ---------------------------
_image_cache: dict[str, pygame.Surface] = {}

def safe_load_image(path: Path) -> pygame.Surface:
    """Carga una imagen DESDE UN PATH EXACTO. Usado internamente por load_image."""
    key = str(path)
    if key in _image_cache:
        return _image_cache[key]
    
    if not path.exists():
        print(f"ERROR: No se pudo encontrar la imagen en: {path}")
        # Devuelve un placeholder rojo brillante si la imagen no se encuentra
        surf = pygame.Surface((100, 100))
        surf.fill((255, 0, 128))
        return surf
        
    img = pygame.image.load(str(path))
    # convert_alpha for pngs, convert otherwise
    surf = img.convert_alpha() if path.suffix.lower() == ".png" else img.convert()
    _image_cache[key] = surf
    return surf

def find_by_stem(assets_dir: Path, stem: str) -> Optional[Path]:
    """Busca .png, .jpg, o .jpeg que coincida con el stem."""
    exts = (".png", ".jpg", ".jpeg")
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists():
            return p
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{stem}*{ext}"))
    return min(cands, key=lambda p: len(p.name)) if cands else None

def load_image(assets_dir: Path, stems: List[str]) -> Optional[pygame.Surface]:
    """Carga la primera imagen que encuentre de una lista de stems."""
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            return safe_load_image(p) # Usa el helper interno
    return None

# ===============================================================
# CLASE PLAYER Y load_char_frames (igual funcionalidad que ya tenías)
# ===============================================================
def load_char_frames(char_dir: Path, target_h: int) -> dict[str, list[pygame.Surface] | pygame.Surface]:
    if not char_dir.exists(): 
        # Fallback si la carpeta seleccionada no existe
        alt_folder_name = "PERSONAJE H" if "M" in char_dir.name else "PERSONAJE M"
        alt_dir = char_dir.parent / alt_folder_name
        if alt_dir.exists():
            print(f"WARN: Carpeta '{char_dir.name}' no encontrada. Usando '{alt_folder_name}'.")
            char_dir = alt_dir
        else:
            raise FileNotFoundError(f"No se encontró la carpeta 'assets/{char_dir.name}' ni una alternativa.")
            
    def _load_seq(prefix: str) -> list[pygame.Surface]:
        files: list[Path] = []; exts = (".png", ".jpg", ".jpeg")
        for ext in exts: files += list(char_dir.glob(f"{prefix}_[0-9]*{ext}"))
        def _num(p: Path) -> int: m = re.search(r"_(\d+)\.\w+$", p.name); return int(m.group(1)) if m else 0
        files.sort(key=_num); seq: list[pygame.Surface] = []
        for p in files:
            img = safe_load_image(p)
            seq.append(img)
        return seq
    def _load_idle(name: str):
        for ext in (".png", ".jpg", ".jpeg"):
            p = char_dir / f"{name}{ext}"
            if p.exists():
                return safe_load_image(p)
        return None
    right = _load_seq("ecoguardian_walk_right"); left  = _load_seq("ecoguardian_walk_left"); down  = _load_seq("ecoguardian_walk_down"); up    = _load_seq("ecoguardian_walk_up")
    idle_right = _load_idle("ecoguardian_right_idle"); idle_left  = _load_idle("ecoguardian_left_idle"); idle_down  = _load_idle("ecoguardian_down_idle"); idle_up    = _load_idle("ecoguardian_up_idle")
    if right and not left: left = [pygame.transform.flip(f, True, False) for f in right]
    if left and not right: right = [pygame.transform.flip(f, True, False) for f in left]
    if not down: down = right[:1] if right else []
    if not up:   up   = right[:1] if right else []
    if idle_right is None and right: idle_right = right[0]
    if idle_left  is None and idle_right is not None: idle_left = pygame.transform.flip(idle_right, True, False)
    if idle_down  is None and down:  idle_down = down[0]
    if idle_up    is None and up:    idle_up   = up[0]
    def _scale(f: pygame.Surface) -> pygame.Surface:
        h = target_h; w = int(f.get_width() * (h / f.get_height())); return pygame.transform.smoothscale(f, (w, h))
    def _scale_list(seq: list[pygame.Surface]) -> list[pygame.Surface]: return [_scale(f) for f in seq]
    def _normalize(seq: list[pygame.Surface]) -> list[pygame.Surface]:
        if not seq: return seq
        max_w = max(f.get_width() for f in seq); H = seq[0].get_height(); out = []
        for f in seq: canvas = pygame.Surface((max_w, H), pygame.SRCALPHA); rect = f.get_rect(midbottom=(max_w//2, H)); canvas.blit(f, rect); out.append(canvas)
        return out
    def _normalize_single(s: pygame.Surface) -> pygame.Surface:
        S = _scale(s); canvas = pygame.Surface((S.get_width(), S.get_height()), pygame.SRCALPHA); rect = S.get_rect(midbottom=(canvas.get_width()//2, canvas.get_height())); canvas.blit(S, rect); return canvas
    right = _normalize(_scale_list(right)); left  = _normalize(_scale_list(left)); down  = _normalize(_scale_list(down)); up    = _normalize(_scale_list(up))
    if idle_right: idle_right = _normalize_single(idle_right)
    if idle_left:  idle_left  = _normalize_single(idle_left)
    if idle_down:  idle_down  = _normalize_single(idle_down)
    if idle_up:    idle_up    = _normalize_single(idle_up)
    return {"right": right, "left": left, "down": down, "up": up, "idle_right": idle_right, "idle_left": idle_left, "idle_down": idle_down, "idle_up": idle_up}

class Player(pygame.sprite.Sprite):
    def __init__(self, frames: dict[str, list[pygame.Surface] | pygame.Surface], pos, bounds: pygame.Rect,
                 speed: float = 300, anim_fps: float = 9.0):
        super().__init__()
        self.frames = frames; self.dir = "down"; self.frame_idx = 0; self.anim_timer = 0.0; self.anim_dt = 1.0 / max(1.0, anim_fps)
        idle = self.frames.get("idle_down"); start_img = idle if isinstance(idle, pygame.Surface) else (self.frames["down"][0] if self.frames["down"] else pygame.Surface((40,60), pygame.SRCALPHA))
        self.image = start_img; self.rect = self.image.get_rect(center=pos); self.speed = speed; self.bounds = bounds
        self.prev_rect = self.rect.copy()

    def handle_input(self, dt: float):
        self.prev_rect = self.rect.copy()
        k = pygame.key.get_pressed(); dx = (k[pygame.K_d] or k[pygame.K_RIGHT]) - (k[pygame.K_a] or k[pygame.K_LEFT]); dy = (k[pygame.K_s] or k[pygame.K_DOWN])  - (k[pygame.K_w] or k[pygame.K_UP])
        moving = (dx != 0 or dy != 0)
        if moving:
            l = math.hypot(dx, dy); dx, dy = dx / l, dy / l
            if abs(dx) > abs(dy):
                self.dir = "left" if dx > 0 else "right"
            else:
                self.dir = "down" if dy > 0 else "up"
            self.rect.x += int(dx * self.speed * dt); self.rect.y += int(dy * self.speed * dt); self.rect.clamp_ip(self.bounds)
            self.anim_timer += dt
            if self.anim_timer >= self.anim_dt:
                self.anim_timer -= self.anim_dt; seq: list[pygame.Surface] = self.frames.get(self.dir, [])
                if seq: self.frame_idx = (self.frame_idx + 1) % len(seq)
            seq: list[pygame.Surface] = self.frames.get(self.dir, [])
            if seq: self.image = seq[self.frame_idx % len(seq)]
        else:
            idle_key = f"idle_{self.dir}"; idle_img = self.frames.get(idle_key)
            if isinstance(idle_img, pygame.Surface): self.image = idle_img
            else: seq: list[pygame.Surface] = self.frames.get(self.dir, []); self.image = seq[0] if seq else self.image
            self.frame_idx = 0
        new_midbottom = self.rect.midbottom; self.rect = self.image.get_rect(midbottom=new_midbottom); self.rect.clamp_ip(self.bounds)

    def revert_position(self):
        self.rect = self.prev_rect.copy()

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, self.rect)

# ===============================================================
# FUNCION PRINCIPAL NIVEL 3 - FACIL
# ===============================================================
def run(screen: pygame.Surface, assets_dir: Path, personaje: str, dificultad: str):
    ANCHO, ALTO = screen.get_size()
    reloj = pygame.time.Clock()

    pygame.font.init()
    font_hud = pygame.font.SysFont("Arial", 22, bold=True)
    font_timer = pygame.font.SysFont("Arial", 36, bold=True)
    font_titulo = pygame.font.SysFont("Arial", 48, bold=True)

    # --- 1. Cargar recursos (UNA SOLA VEZ) ---
    try:
        # Placeholder para mapas (se usa si una imagen falta)
        placeholder_map_img = pygame.Surface((ANCHO, ALTO))
        placeholder_map_img.fill((255, 0, 128)) # Rosa brillante
        
        def get_map_img(stem: str, fallback_stem: Optional[str] = None):
            """Carga una imagen del mapa, o su fallback, o un placeholder."""
            img = load_image(assets_dir, [stem])
            if img:
                return img
            # Si falla, intenta cargar el fallback (ej. "ced2" si "2y4" falta)
            if fallback_stem:
                img_fallback = load_image(assets_dir, [fallback_stem])
                if img_fallback:
                    print(f"WARN: No se encontró '{stem}'. Usando fallback '{fallback_stem}'.")
                    return img_fallback
            # Si todo falla, usa el placeholder
            print(f"ERROR: No se encontró '{stem}' ni fallback. Usando placeholder.")
            return placeholder_map_img

        # === CAMBIO: Cargar el mapa de fondo único ===
        fondo_mapa_escalado = pygame.transform.smoothscale(get_map_img("1366x768 ever"), (ANCHO, ALTO))
        
        # === CAMBIO: Cargar las 14 imágenes en un diccionario ===
        # (ti=top_izq(1), tm=top_medio(2), ai=abajo_izq(3), ad=abajo_der(4))
        
        MAPA_ESTADOS = {
            # 0 reparados
            (False, False, False, False): get_map_img("1366x768 ever"),
            # 1 reparado
            (True,  False, False, False): get_map_img("ced1"), # 1
            (False, True,  False, False): get_map_img("ced2"), # 2
            (False, False, True,  False): get_map_img("ced3f"), # 3
            (False, False, False, True):  get_map_img("1366x768 ever", "1366x768 ever"), # 4 (FALTA! Usando inicial)
            # 2 reparados
            (True,  True,  False, False): get_map_img("1y2"), # 1+2
            (True,  False, True,  False): get_map_img("1y3"), # 1+3
            (True,  False, False, True):  get_map_img("1y4"), # 1+4
            (False, True,  True,  False): get_map_img("2y3"), # 2+3
            (False, True,  False, True):  get_map_img("ced2", "ced2"), # 2+4 (FALTA! Usando "Solo 2")
            (False, False, True,  True):  get_map_img("3y4"), # 3+4
            # 3 reparados
            (True,  True,  True,  False): get_map_img("12y3"), # 1+2+3
            (True,  True,  False, True):  get_map_img("12y4"), # 1+2+4
            (True,  False, True,  True):  get_map_img("13y4"), # 1+3+4
            (False, True,  True,  True):  get_map_img("34y2"), # 2+3+4
            # 4 reparados
            (True,  True,  True,  True):  get_map_img("123y4"), # 1+2+3+4
        }
        
        # Escalar todas las imágenes del mapa de una vez
        imagenes_escaladas = {}
        for estado, img in MAPA_ESTADOS.items():
            imagenes_escaladas[estado] = pygame.transform.smoothscale(img, (ANCHO, ALTO))

        # win/lose (opcional)
        win_img = None; lose_img = None
        win_img = load_image(assets_dir, ["win_level3"])
        lose_img = load_image(assets_dir, ["lose_level3"])
        if win_img: win_img = pygame.transform.smoothscale(win_img, (ANCHO, ALTO))
        if lose_img: lose_img = pygame.transform.smoothscale(lose_img, (ANCHO, ALTO))


        pausa_dir = assets_dir / "PAUSA"
        pausa_panel_img = load_image(pausa_dir, ["nivelA 2", "panel_pausa", "pausa_panel"])
        timer_panel_img = load_image(assets_dir, ["temporizador", "timer_panel", "panel_tiempo", "TEMPORAZIDOR"])

        # Pre-escalar panel del temporizador al tamaño fijo usado en pantalla:
        panel_w, panel_h = int(ANCHO * 0.18), int(ALTO * 0.11)
        scaled_timer_panel = None
        if timer_panel_img:
            scaled_timer_panel = pygame.transform.smoothscale(timer_panel_img, (panel_w, panel_h))

    except Exception as e:
        print(f"Error cargando imágenes del Nivel 3: {e}")
        stop_level_music() # Detener música si la carga falla
        return "menu"

    # --- 2. Zonas y jugador ---
    # === CAMBIO: Zonas de reparación. AJUSTA ESTAS COORDENADAS ===
    # (x, y, ancho, alto)
    zona_reparar_top_izq = pygame.Rect(100, 100, 150, 150)  # Ejemplo
    zona_reparar_top_medio = pygame.Rect(400, 100, 150, 150) # Ejemplo
    zona_reparar_abajo_izq = pygame.Rect(100, 400, 150, 150) # Ejemplo
    zona_reparar_abajo_der = pygame.Rect(700, 400, 150, 150) # Ejemplo

    try:
        ruta_personaje = assets_dir / personaje
        frames_jugador = load_char_frames(ruta_personaje, target_h=int(ALTO * 0.12))
    except FileNotFoundError:
        print(f"Error: No se encontraron los frames del personaje en {ruta_personaje}")
        stop_level_music() # Detener música si la carga falla
        return "menu"

    limites_pantalla = screen.get_rect().inflate(-20, -20)
    spawn_pos = (ANCHO // 2, ALTO // 2)
    jugador = Player(frames_jugador, spawn_pos, limites_pantalla, speed=300)

    # ===============================================================
    # === ¡AQUÍ VAN LOS STOPS! ===
    # === CAMBIO: Añadidas tus 7 coordenadas ===
    COLLISION_RECTS = [
        pygame.Rect(876, 12, 253, 292),    # 1
        pygame.Rect(901, 301, 275, 243),   # 2
        pygame.Rect(923, 558, 250, 253),   # 3
        pygame.Rect(218, 628, 260, 208),   # 4
        pygame.Rect(-2, 443, 244, 331),    # 5
        pygame.Rect(331, 34, 235, 300),    # 6
        pygame.Rect(9, 39, 263, 266)       # 8 (el 7 que faltaba)
    ]
    # ===============================================================

    # --- 4. Estado del juego ---
    estado_reparacion = { "top_izq": False, "top_medio": False, "abajo_izq": False, "abajo_der": False }
    progreso_reparacion = 0; reparando_actualmente = None
    paused = False; victoria = False; derrota = False
    tiempo_fin_juego = 0
    remaining_ms = TOTAL_MS; suspense_music_started = False

    pause_button_assets = {"cont_base": None, "cont_hover": None, "restart_base": None, "restart_hover": None, "menu_base": None, "menu_hover": None}

    # start music (no heavy op inside loop)
    start_level_music(assets_dir)
    
    # =====================================================================
    # === ¡NUEVO! PANTALLA DE INSTRUCCIONES ===
    # =====================================================================
    # (Asegúrate de guardar tu imagen como 'instruccion_nivel_3.png' en assets/)
    instruccion_img = load_image(assets_dir, ["instruccion_nivel_3"])
    if instruccion_img:
        # Escalar la imagen de instrucciones para que quepa
        img_w, img_h = instruccion_img.get_size()
        scale_ratio = min((ANCHO * 0.8) / img_w, (ALTO * 0.8) / img_h)
        instruccion_img = pygame.transform.smoothscale(
            instruccion_img, (int(img_w * scale_ratio), int(img_h * scale_ratio))
        )
        instruccion_rect = instruccion_img.get_rect(center=(ANCHO // 2, ALTO // 2))

        # Crear un overlay oscuro
        overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180)) # Negro semitransparente

        waiting_for_start = True
        while waiting_for_start:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    stop_level_music()
                    return "salir" # Usar "salir" para cerrar el juego
                if e.type == pygame.KEYDOWN:
                    if e.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN):
                        waiting_for_start = False
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    waiting_for_start = False

            # Dibujar
            screen.blit(fondo_mapa_escalado, (0,0)) # Fondo del nivel
            screen.blit(overlay, (0, 0)) # Overlay oscuro
            screen.blit(instruccion_img, instruccion_rect) # Instrucción

            pygame.display.flip()
            reloj.tick(60)
        
        play_sfx("select", assets_dir) # Sonido de clic al empezar

    # =====================================================================
    # === FIN DE PANTALLA DE INSTRUCCIONES ===
    # =====================================================================


    # --- Bucle principal ---
    ejecutando = True
    while ejecutando:
        dt = reloj.tick(60) / 1000.0
        dt_ms = int(dt * 1000)
        mouse_click = False
        mouse_pos = pygame.mouse.get_pos()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT: stop_level_music(); return "salir"
            if paused:
                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1: mouse_click = True
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_SPACE:
                        paused = False; play_sfx("sfx_click", assets_dir)
                    if evento.key == pygame.K_ESCAPE:
                        stop_level_music(); return "menu"
            elif not (victoria or derrota):
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE: stop_level_music(); return "menu"
                    if evento.key == pygame.K_SPACE:
                        paused = True; play_sfx("sfx_click", assets_dir)

        if victoria or derrota:
            tiempo_fin_juego += dt
            if tiempo_fin_juego > 3.0: return "menu"
        elif not paused:
            remaining_ms -= dt_ms; remaining_ms = max(0, remaining_ms)
            if remaining_ms <= SUSPENSE_TIME_MS and not suspense_music_started:
                start_suspense_music(assets_dir); suspense_music_started = True
            if remaining_ms <= 0:
                derrota = True; stop_level_music(); tiempo_fin_juego = 0; continue
            
            jugador.handle_input(dt)

            # === ¡NUEVO! Comprobar colisiones con los "Stops" ===
            for wall in COLLISION_RECTS:
                if jugador.rect.colliderect(wall):
                    jugador.revert_position() # Choca y regresa
                    break # No necesita comprobar más muros
            
            teclas = pygame.key.get_pressed(); zona_activa = None
            if not estado_reparacion["top_izq"] and jugador.rect.colliderect(zona_reparar_top_izq): zona_activa = "top_izq"
            elif not estado_reparacion["top_medio"] and jugador.rect.colliderect(zona_reparar_top_medio): zona_activa = "top_medio"
            elif not estado_reparacion["abajo_izq"] and jugador.rect.colliderect(zona_reparar_abajo_izq): zona_activa = "abajo_izq"
            elif not estado_reparacion["abajo_der"] and jugador.rect.colliderect(zona_reparar_abajo_der): zona_activa = "abajo_der"
            
            if zona_activa and teclas[pygame.K_r]:
                reparando_actualmente = zona_activa; progreso_reparacion += 1
                if progreso_reparacion >= TIEMPO_PARA_REPARAR:
                    estado_reparacion[zona_activa] = True; progreso_reparacion = 0; reparando_actualmente = None
                    play_sfx("sfx_plant", assets_dir) # Reusamos el sonido de plantar
                    if all(estado_reparacion.values()):
                        victoria = True; stop_level_music(); tiempo_fin_juego = 0
            else:
                progreso_reparacion = 0; reparando_actualmente = None

        # --- Dibujo ---
        
        # === CAMBIO: Dibujar el mapa correcto según el estado ===
        ti = estado_reparacion["top_izq"]
        tm = estado_reparacion["top_medio"]
        ai = estado_reparacion["abajo_izq"]
        ad = estado_reparacion["abajo_der"]
        
        # Crear la "llave" (key) para el diccionario de imágenes
        estado_actual = (ti, tm, ai, ad)
        
        # Dibujar la imagen escalada que corresponde a ese estado
        # Fallback por si la combinación (rara) no estuviera en el dict
        screen.blit(imagenes_escaladas.get(estado_actual, fondo_mapa_escalado), (0,0))
        
        # ================================================
        # === CAMBIO: Dibujar colisiones para debug ===
        for rect in COLLISION_RECTS:
            pygame.draw.rect(screen, DEBUG_COLOR_ROJO, rect, 2) # '2' = borde de 2px
        # ================================================

        # === CAMBIO: Mostrar las zonas dañadas (opcional, para debug) ===
        # (Si quieres ver las zonas, descomenta estas líneas)
        # if not estado_reparacion["top_izq"]: pygame.draw.rect(screen, (255,0,0,50), zona_reparar_top_izq)
        # if not estado_reparacion["top_medio"]: pygame.draw.rect(screen, (255,0,0,50), zona_reparar_top_medio)
        # if not estado_reparacion["abajo_izq"]: pygame.draw.rect(screen, (255,0,0,50), zona_reparar_abajo_izq)
        # if not estado_reparacion["abajo_der"]: pygame.draw.rect(screen, (255,0,0,50), zona_reparar_abajo_der)

        jugador.draw(screen)

        if reparando_actualmente:
            pos_barra_x = jugador.rect.centerx - 25
            pos_barra_y = jugador.rect.top - 30
            pygame.draw.rect(screen, GRIS, (pos_barra_x, pos_barra_y, 50, 10), border_radius=2)
            ancho_progreso = 50 * (progreso_reparacion / TIEMPO_PARA_REPARAR)
            pygame.draw.rect(screen, VERDE, (pos_barra_x, pos_barra_y, ancho_progreso, 10), border_radius=2)

        texto_hud_str = "Reparar: [R] | Pausa: [ESPACIO]"
        texto_hud = font_hud.render(texto_hud_str, True, NEGRO)
        screen.blit(texto_hud, (15, ALTO - 35))
        texto_hud_sombra = font_hud.render(texto_hud_str, True, BLANCO)
        screen.blit(texto_hud_sombra, (13, ALTO - 37))

        # Temporizador (usa scaled_timer_panel precalculado)
        mm = (remaining_ms // 1000) // 60; ss = (remaining_ms // 1000) % 60
        time_str = f"{mm}:{ss:02d}"
        color_timer = ROJO_OSCURO if remaining_ms <= 10000 else (20, 15, 10)
        panel_rect = pygame.Rect(ANCHO - int(ANCHO * 0.04) - int(ANCHO * 0.18), int(ANCHO * 0.04), int(ANCHO * 0.18), int(ALTO * 0.11))

        if scaled_timer_panel:
            screen.blit(scaled_timer_panel, panel_rect.topleft)
        else:
            pygame.draw.rect(screen, (30,20,15), panel_rect, border_radius=10)
            inner = panel_rect.inflate(-10, -10)
            pygame.draw.rect(screen, (210,180,140), inner, border_radius=8)

        txt = font_timer.render(time_str, True, color_timer)
        sh  = font_timer.render(time_str, True, (0,0,0))
        cx = panel_rect.centerx - int(panel_rect.w * 0.12)
        cy = panel_rect.centery
        screen.blit(sh,  sh.get_rect(center=(cx + 2, cy + 2)))
        screen.blit(txt, txt.get_rect(center=(cx, cy)))

        # Pausa (interacción ligera — generación de subsurfaces solo en la primera pausa cuando panel_scaled existe)
        if paused and not (victoria or derrota):
            overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA); overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))
            panel_w2, panel_h2 = int(ANCHO * 0.52), int(ALTO * 0.52)
            panel2 = pygame.Rect(ANCHO//2 - panel_w2//2, ALTO//2 - panel_h2//2, panel_w2, panel_h2)
            panel_scaled = None
            if pausa_panel_img:
                panel_scaled = pygame.transform.smoothscale(pausa_panel_img, (panel_w2, panel_h2))
                screen.blit(panel_scaled, panel2)
            else:
                pygame.draw.rect(screen, (30,20,15), panel2, border_radius=16)

            btn_w, btn_h = int(panel_w2 * 0.80), int(panel_h2 * 0.18)
            cx = panel2.centerx
            y_cont    = panel2.top + int(panel_h2 * 0.40)
            y_restart = panel2.top + int(panel_h2 * 0.60)
            y_menu    = panel2.top + int(panel_h2 * 0.80)
            r_cont    = pygame.Rect(0, 0, btn_w, btn_h); r_cont.center    = (cx, y_cont)
            r_restart = pygame.Rect(0, 0, btn_w, btn_h); r_restart.center = (cx, y_restart)
            r_menu    = pygame.Rect(0, 0, btn_w, btn_h); r_menu.center    = (cx, y_menu)

            # build hover assets once (cheap)
            if pause_button_assets["cont_base"] is None and panel_scaled:
                try:
                    r_cont_local    = r_cont.move(-panel2.x, -panel2.y)
                    r_restart_local = r_restart.move(-panel2.x, -panel2.y)
                    r_menu_local    = r_menu.move(-panel2.x, -panel2.y)
                    base_cont    = panel_scaled.subsurface(r_cont_local)
                    base_restart = panel_scaled.subsurface(r_restart_local)
                    base_menu    = panel_scaled.subsurface(r_menu_local)
                    pause_button_assets["cont_base"] = base_cont
                    pause_button_assets["restart_base"] = base_restart
                    pause_button_assets["menu_base"] = base_menu
                    hover_w, hover_h = int(r_cont.w * 1.05), int(r_cont.h * 1.05)
                    pause_button_assets["cont_hover"] = pygame.transform.smoothscale(base_cont, (hover_w, hover_h))
                    pause_button_assets["restart_hover"] = pygame.transform.smoothscale(base_restart, (hover_w, hover_h))
                    pause_button_assets["menu_hover"] = pygame.transform.smoothscale(base_menu, (hover_w, hover_h))
                except ValueError:
                    pause_button_assets["cont_base"] = None

            def draw_btn(base_rect: pygame.Rect, hover_img: pygame.Surface) -> bool:
                hov = base_rect.collidepoint(mouse_pos)
                if hov and hover_img:
                    hover_rect = hover_img.get_rect(center=base_rect.center)
                    screen.blit(hover_img, hover_rect)
                return hov and mouse_click

            if draw_btn(r_cont, pause_button_assets["cont_hover"]):
                play_sfx("sfx_click", assets_dir); paused = False
            elif draw_btn(r_restart, pause_button_assets["restart_hover"]):
                play_sfx("sfx_click", assets_dir)
                # reset simple: reinitialize state
                estado_reparacion = { "top_izq": False, "top_medio": False, "abajo_izq": False, "abajo_der": False }
                progreso_reparacion = 0; reparando_actualmente = None
                paused = False; victoria = False; derrota = False
                tiempo_fin_juego = 0; remaining_ms = TOTAL_MS; suspense_music_started = False
                jugador.rect.center = spawn_pos
                start_level_music(assets_dir)
            elif draw_btn(r_menu, pause_button_assets["menu_hover"]):
                play_sfx("sfx_click", assets_dir); stop_level_music(); ejecutando = False

        if victoria:
            if win_img: screen.blit(win_img, (0,0))
            else:
                # === CAMBIO: Mostrar el fondo final ===
                screen.blit(imagenes_escaladas.get((True, True, True, True), fondo_mapa_escalado), (0,0))
                overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA); overlay.fill((0,150,0,170))
                screen.blit(overlay, (0,0))
                texto_vic = font_titulo.render("¡Plaza Reparada!", True, BLANCO)
                screen.blit(texto_vic, texto_vic.get_rect(center=(ANCHO//2, ALTO//2)))

        if derrota:
            if lose_img: screen.blit(lose_img, (0,0))
            else:
                overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA); overlay.fill((150,0,0,170))
                screen.blit(overlay, (0,0))
                texto_vic = font_titulo.render("¡Tiempo Agotado!", True, BLANCO)
                screen.blit(texto_vic, texto_vic.get_rect(center=(ANCHO//2, ALTO//2)))

        pygame.display.flip()

    stop_level_music()
    return "menu"