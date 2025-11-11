from __future__ import annotations
import pygame
import sys
import re
import math
from pathlib import Path
from typing import Optional, List, Tuple, Dict

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

# --- Constantes del Nivel ---
TIEMPO_PARA_REPARAR = 120  # 2 segundos
TOTAL_MS = 80_000          # 80 segundos
SUSPENSE_TIME_MS = 30_000  # 30 segundos


# ===============================================================
# === SECCIÓN DE AYUDA (Helpers) (Copiada de Nivel 2) ===
# ===============================================================

def find_by_stem(assets_dir: Path, stem: str) -> Optional[Path]:
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
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
    return None

# ===============================================================
# === CLASE PLAYER Y LOAD_CHAR_FRAMES ===
# ===============================================================

def load_char_frames(char_dir: Path, target_h: int) -> dict[str, list[pygame.Surface] | pygame.Surface]:
    # (Tu código de load_char_frames)
    if not char_dir.exists(): raise FileNotFoundError(f"No se encontró la carpeta '{char_dir}'")
    def _load_seq(prefix: str) -> list[pygame.Surface]:
        files: list[Path] = []; exts = (".png", ".jpg", ".jpeg")
        for ext in exts: files += list(char_dir.glob(f"{prefix}_[0-9]*{ext}"))
        def _num(p: Path) -> int: m = re.search(r"_(\d+)\.\w+$", p.name); return int(m.group(1)) if m else 0
        files.sort(key=_num); seq: list[pygame.Surface] = []
        for p in files: img = pygame.image.load(str(p)); seq.append(img.convert_alpha() if p.suffix.lower()==".png" else img.convert())
        return seq
    def _load_idle(name: str) -> Optional[pygame.Surface]:
        for ext in (".png", ".jpg", ".jpeg"):
            p = char_dir / f"{name}{ext}"
            if p.exists(): img = pygame.image.load(str(p)); return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
        return None
    right = _load_seq("ecoguardian_walk_right"); left  = _load_seq("ecoguardian_walk_left"); down  = _load_seq("ecoguardian_walk_down"); up    = _load_seq("ecoguardian_walk_up")
    idle_right = _load_idle("ecoguardian_right_idle"); idle_left  = _load_idle("ecoguardian_left_idle"); idle_down  = _load_idle("ecoguardian_down_idle"); idle_up    = _load_idle("ecoguardian_up_idle")
    if right and not left: left = [pygame.transform.flip(f, True, False) for f in right]
    if left and not right: right = [pygame.transform.flip(f, True, False) for f in left]
    if not down: down = right[:1] if right else []; 
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
            
            seq: list[pygame.Surface] = self.frames.get(self.dir, []); 
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
# === FUNCIÓN PRINCIPAL DEL NIVEL 3 ===
# ===============================================================

def run(screen: pygame.Surface, assets_dir: Path, personaje: str, dificultad: str):
    
    ANCHO, ALTO = screen.get_size()
    reloj = pygame.time.Clock()
    
    pygame.font.init()
    font_hud = pygame.font.SysFont("Arial", 22, bold=True)
    font_timer = pygame.font.SysFont("Arial", 36, bold=True)
    font_titulo = pygame.font.SysFont("Arial", 48, bold=True)

    # --- 1. Cargar Recursos del Nivel ---
    try:
        # (Tu sección de carga de 16 imágenes. Asumo que está completa y correcta)
        img_0_roto = pygame.image.load(assets_dir / 'original.jpg').convert()
        img_1_top_izq = pygame.image.load(assets_dir / 'img_1_top_izq.jpg').convert()
        img_1_top_medio = pygame.image.load(assets_dir / 'img_1_top_medio.png').convert()
        img_1_abajo_izq = pygame.image.load(assets_dir / 'img_1_abajo_izq.png').convert()
        img_1_abajo_der = pygame.image.load(assets_dir / 'img_1_abajo_der.png').convert()
        img_2_ti_tm = pygame.image.load(assets_dir / 'img_2_ti_tm.png').convert()
        img_2_ti_ai = pygame.image.load(assets_dir / 'img_2_ti_ai.png').convert()
        img_2_ti_ad = pygame.image.load(assets_dir / 'img_2_ti_ad.png').convert()
        img_2_tm_ai = pygame.image.load(assets_dir / 'img_2_tm_ai.png').convert()
        img_2_tm_ad = pygame.image.load(assets_dir / 'img_2_tm_ad.png').convert()
        img_2_ai_ad = pygame.image.load(assets_dir / 'img_2_ai_ad.png').convert()
        img_3_ti_tm_ai = pygame.image.load(assets_dir / 'img_3_ti_tm_ai.png').convert()
        img_3_ti_tm_ad = pygame.image.load(assets_dir / 'img_3_ti_tm_ad.png').convert()
        img_3_ti_ai_ad = pygame.image.load(assets_dir / 'img_3_ti_ai_ad.png').convert()
        img_3_tm_ai_ad = pygame.image.load(assets_dir / 'img_3_tm_ai_ad.png').convert()
        img_4_todo = pygame.image.load(assets_dir / 'img_4_todo.png').convert()
        
        imagenes = [
            img_0_roto, img_1_top_izq, img_1_top_medio, img_1_abajo_izq, img_1_abajo_der,
            img_2_ti_tm, img_2_ti_ai, img_2_ti_ad, img_2_tm_ai, img_2_tm_ad, img_2_ai_ad,
            img_3_ti_tm_ai, img_3_ti_tm_ad, img_3_ti_ai_ad, img_3_tm_ai_ad, img_4_todo
        ]
        imagenes_escaladas = [pygame.transform.scale(img, (ANCHO, ALTO)) for img in imagenes]
        
        win_img = None; lose_img = None
        for ext in (".jpg", ".png"):
            p_win = assets_dir / f"win_level3{ext}"
            if p_win.exists(): win_img = pygame.image.load(p_win).convert(); win_img = pygame.transform.scale(win_img, (ANCHO, ALTO)); break
        for ext in (".jpg", ".png"):
            p_lose = assets_dir / f"lose_level3{ext}"
            if p_lose.exists(): lose_img = pygame.image.load(p_lose).convert(); lose_img = pygame.transform.scale(lose_img, (ANCHO, ALTO)); break
        
        if not win_img: print("Advertencia: No se encontró 'win_level3.jpg' o '.png'")
        if not lose_img: print("Advertencia: No se encontró 'lose_level3.jpg' o '.png'")

        pausa_dir = assets_dir / "PAUSA"
        pausa_panel_img = load_image(pausa_dir, ["nivelA 2", "panel_pausa", "pausa_panel"])
        pause_button_assets = {
            "cont_base": None, "cont_hover": None,
            "restart_base": None, "restart_hover": None,
            "menu_base": None, "menu_hover": None,
        }
        
        timer_panel_img = load_image(assets_dir, ["temporizador", "timer_panel", "panel_tiempo", "TEMPORAZIDOR"])

    except Exception as e:
        print(f"Error cargando imágenes del Nivel 3: {e}")
        print("Asegúrate de tener TODAS las 16 imágenes de estado en la carpeta 'assets/'.")
        return "menu" 

    # --- 2. Definir Zonas de Reparación (¡¡¡CORREGIDAS Y PEQUEÑAS!!!) ---
    # Zonas pequeñas de 40x40 para ser precisos
    zona_reparar_top_izq = pygame.Rect(190, 200, 40, 40)
    zona_reparar_top_medio = pygame.Rect(440, 200, 40, 40)
    zona_reparar_abajo_izq = pygame.Rect(190, 500, 40, 40)
    zona_reparar_abajo_der = pygame.Rect(710, 500, 40, 40) # Movida más a la derecha, lejos de la fuente

    # --- 2.1. Definir Límites de los Edificios (¡¡¡VACÍA!!!) ---
    limites_edificios = []
    
    # --- 3. Instanciar Jugador ---
    try:
        ruta_personaje = assets_dir / personaje
        frames_jugador = load_char_frames(ruta_personaje, target_h=int(ALTO * 0.12))
    except FileNotFoundError:
         print(f"Error: No se encontraron los frames del personaje en {ruta_personaje}")
         return "menu" 
         
    limites_pantalla = screen.get_rect().inflate(-20, -20)
    
    # (El spawn vuelve al centro)
    spawn_pos = (ANCHO // 2, ALTO // 2) 
    jugador = Player(frames_jugador, spawn_pos, limites_pantalla, speed=300)

    # --- 4. Estado del Juego ---
    estado_reparacion = {
        "top_izq": False, "top_medio": False, 
        "abajo_izq": False, "abajo_der": False
    }
    progreso_reparacion = 0; reparando_actualmente = None
    paused = False; victoria = False; derrota = False
    tiempo_fin_juego = 0
    remaining_ms = TOTAL_MS; suspense_music_started = False
    
    # --- 5. Función de Reseteo ---
    def reset_level():
        nonlocal estado_reparacion, progreso_reparacion, reparando_actualmente
        nonlocal victoria, derrota, tiempo_fin_juego, remaining_ms, suspense_music_started, paused
        
        estado_reparacion = { "top_izq": False, "top_medio": False, "abajo_izq": False, "abajo_der": False }
        progreso_reparacion = 0
        reparando_actualmente = None
        victoria = False
        derrota = False
        tiempo_fin_juego = 0
        remaining_ms = TOTAL_MS
        suspense_music_started = False
        paused = False
        jugador.rect.center = spawn_pos
        start_level_music(assets_dir)

    # --- 6. Iniciar Música ---
    start_level_music(assets_dir)

    # --- Bucle Principal del Nivel ---
    ejecutando = True
    while ejecutando:
        
        dt = reloj.tick(60) / 1000.0
        dt_ms = int(dt * 1000)
        
        mouse_click = False
        mouse_pos = pygame.mouse.get_pos()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT: stop_level_music(); return "salir"
            
            if paused:
                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    mouse_click = True
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_SPACE:
                        paused = False
                        play_sfx("sfx_click", assets_dir)
                    if evento.key == pygame.K_ESCAPE:
                        stop_level_music(); return "menu"
            
            elif not (victoria or derrota):
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE: stop_level_music(); return "menu" 
                    if evento.key == pygame.K_SPACE:
                        paused = True
                        play_sfx("sfx_click", assets_dir)
                    
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
            
            # --- (Colisiones de edificios desactivadas) ---
            
            teclas = pygame.key.get_pressed(); zona_activa = None
            
            if not estado_reparacion["top_izq"] and jugador.rect.colliderect(zona_reparar_top_izq): zona_activa = "top_izq"
            elif not estado_reparacion["top_medio"] and jugador.rect.colliderect(zona_reparar_top_medio): zona_activa = "top_medio"
            elif not estado_reparacion["abajo_izq"] and jugador.rect.colliderect(zona_reparar_abajo_izq): zona_activa = "abajo_izq"
            elif not estado_reparacion["abajo_der"] and jugador.rect.colliderect(zona_reparar_abajo_der): zona_activa = "abajo_der"
            
            if zona_activa and teclas[pygame.K_r]:
                reparando_actualmente = zona_activa; progreso_reparacion += 1
                if progreso_reparacion >= TIEMPO_PARA_REPARAR:
                    estado_reparacion[zona_activa] = True
                    progreso_reparacion = 0; reparando_actualmente = None
            else:
                progreso_reparacion = 0; reparando_actualmente = None

        # --- Lógica de Dibujo (El Monstruo) ---
        ti = estado_reparacion["top_izq"]; tm = estado_reparacion["top_medio"]
        ai = estado_reparacion["abajo_izq"]; ad = estado_reparacion["abajo_der"]
        
        if not ti and not tm and not ai and not ad: screen.blit(imagenes_escaladas[0], (0, 0))
        elif ti and not tm and not ai and not ad: screen.blit(imagenes_escaladas[1], (0, 0))
        elif not ti and tm and not ai and not ad: screen.blit(imagenes_escaladas[2], (0, 0))
        elif not ti and not tm and ai and not ad: screen.blit(imagenes_escaladas[3], (0, 0))
        elif not ti and not tm and not ai and ad: screen.blit(imagenes_escaladas[4], (0, 0))
        elif ti and tm and not ai and not ad: screen.blit(imagenes_escaladas[5], (0, 0))
        elif ti and not tm and ai and not ad: screen.blit(imagenes_escaladas[6], (0, 0))
        elif ti and not tm and not ai and ad: screen.blit(imagenes_escaladas[7], (0, 0))
        elif not ti and tm and ai and not ad: screen.blit(imagenes_escaladas[8], (0, 0))
        elif not ti and tm and not ai and ad: screen.blit(imagenes_escaladas[9], (0, 0))
        elif not ti and not tm and ai and ad: screen.blit(imagenes_escaladas[10], (0, 0))
        elif ti and tm and ai and not ad: screen.blit(imagenes_escaladas[11], (0, 0))
        elif ti and tm and not ai and ad: screen.blit(imagenes_escaladas[12], (0, 0))
        elif ti and not tm and ai and ad: screen.blit(imagenes_escaladas[13], (0, 0))
        elif not ti and tm and ai and ad: screen.blit(imagenes_escaladas[14], (0, 0))
        elif ti and tm and ai and ad:
            screen.blit(imagenes_escaladas[15], (0, 0))
            if not victoria:
                victoria = True; stop_level_music(); tiempo_fin_juego = 0
        
        jugador.draw(screen)

        if reparando_actualmente:
            pos_barra_x = jugador.rect.centerx - 25
            pos_barra_y = jugador.rect.top - 30
            pygame.draw.rect(screen, GRIS, (pos_barra_x, pos_barra_y, 50, 10), border_radius=2)
            ancho_progreso = 50 * (progreso_reparacion / TIEMPO_PARA_REPARAR)
            pygame.draw.rect(screen, VERDE, (pos_barra_x, pos_barra_y, ancho_progreso, 10), border_radius=2)
            
        texto_hud = font_hud.render("Reparar: [R] | Pausa: [ESPACIO]", True, NEGRO)
        screen.blit(texto_hud, (15, ALTO - 35))
        texto_hud_sombra = font_hud.render("Reparar: [R] | Pausa: [ESPACIO]", True, BLANCO)
        screen.blit(texto_hud_sombra, (13, ALTO - 37))

        # Temporizador Gráfico
        mm = (remaining_ms // 1000) // 60; ss = (remaining_ms // 1000) % 60
        time_str = f"{mm}:{ss:02d}"
        color_timer = ROJO_OSCURO if remaining_ms <= 10000 else (20, 15, 10)
        
        panel_w, panel_h = int(ANCHO * 0.18), int(ALTO * 0.11)
        panel_rect = pygame.Rect(ANCHO - int(ANCHO * 0.04) - panel_w, int(ANCHO * 0.04), panel_w, panel_h)

        if timer_panel_img:
            scaled = pygame.transform.smoothscale(timer_panel_img, (panel_rect.w, panel_rect.h))
            screen.blit(scaled, panel_rect.topleft)
        else:
            pygame.draw.rect(screen, (30, 20, 15), panel_rect, border_radius=10)
            inner = panel_rect.inflate(-10, -10)
            pygame.draw.rect(screen, (210, 180, 140), inner, border_radius=8)

        txt = font_timer.render(time_str, True, color_timer)
        sh  = font_timer.render(time_str, True, (0, 0, 0))
        cx = panel_rect.centerx - int(panel_rect.w * 0.12)
        cy = panel_rect.centery
        screen.blit(sh,  sh.get_rect(center=(cx + 2, cy + 2)))
        screen.blit(txt, txt.get_rect(center=(cx, cy)))

        # Menú de Pausa Gráfico
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
                pygame.draw.rect(screen, (30, 20, 15), panel2, border_radius=16)

            btn_w, btn_h = int(panel_w2 * 0.80), int(panel_h2 * 0.18)
            cx = panel2.centerx
            y_cont    = panel2.top + int(panel_h2 * 0.40)
            y_restart = panel2.top + int(panel_h2 * 0.60)
            y_menu    = panel2.top + int(panel_h2 * 0.80)
            r_cont    = pygame.Rect(0, 0, btn_w, btn_h); r_cont.center    = (cx, y_cont)
            r_restart = pygame.Rect(0, 0, btn_w, btn_h); r_restart.center = (cx, y_restart)
            r_menu    = pygame.Rect(0, 0, btn_w, btn_h); r_menu.center    = (cx, y_menu)

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
                play_sfx("sfx_click", assets_dir)
                paused = False
            elif draw_btn(r_restart, pause_button_assets["restart_hover"]):
                play_sfx("sfx_click", assets_dir)
                reset_level()
            elif draw_btn(r_menu, pause_button_assets["menu_hover"]):
                play_sfx("sfx_click", assets_dir)
                stop_level_music()
                ejecutando = False

        if victoria:
            if win_img: screen.blit(win_img, (0, 0))
            else:
                screen.blit(imagenes_escaladas[15], (0, 0))
                overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA); overlay.fill((0, 150, 0, 170))
                screen.blit(overlay, (0, 0)); texto_vic = font_titulo.render("¡Plaza Reparada!", True, BLANCO)
                screen.blit(texto_vic, texto_vic.get_rect(center=(ANCHO // 2, ALTO // 2)))

        if derrota:
            if lose_img: screen.blit(lose_img, (0, 0))
            else:
                overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA); overlay.fill((150, 0, 0, 170))
                screen.blit(overlay, (0, 0)); texto_vic = font_titulo.render("¡Tiempo Agotado!", True, BLANCO)
                screen.blit(texto_vic, texto_vic.get_rect(center=(ANCHO // 2, ALTO // 2)))

        pygame.display.flip()

    stop_level_music()
    return "menu"