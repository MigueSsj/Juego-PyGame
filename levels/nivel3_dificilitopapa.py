from __future__ import annotations
import pygame, sys, math, random, re
from pathlib import Path
from typing import Optional, List, Tuple
import config

# === SISTEMA DE AUDIO ===
try:
    from audio_shared import start_level_music, start_suspense_music, stop_level_music, play_sfx
except ImportError:
    def start_level_music(a): pass
    def start_suspense_music(a): pass
    def stop_level_music(): pass
    def play_sfx(n, a): pass

# === CONFIGURACIÓN ===
BLANCO = (255, 255, 255)
NEGRO = (0, 0, 0)
VERDE = (0, 200, 0)
ROJO = (200, 0, 0)

TIEMPO_REPARACION = 120  # Ticks para reparar
TOTAL_MS = 70_000        # 70 Segundos (Difícil)
SUSPENSE_TIME_MS = 30_000 

# === FUNCIONES DE CARGA ===
def find_by_stem(assets_dir: Path, stem: str) -> Optional[Path]:
    exts = (".png", ".jpg", ".jpeg")
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists(): return p
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{stem}*{ext}"))
    return min(cands, key=lambda p: len(p.name)) if cands else None

def load_image(assets_dir: Path, stems: List[str]) -> Optional[pygame.Surface]:
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            try:
                img = pygame.image.load(str(p))
                return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
            except: pass
    return None

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    if img.get_width() == 0: return pygame.Surface((new_w, new_w), pygame.SRCALPHA)
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height() * r)))

# === CARGA DE PERSONAJE (ROBUSTA) ===
def load_char_frames(assets_dir: Path, target_h: int, *, char_folder: str = "PERSONAJE H") -> dict[str, list[pygame.Surface] | pygame.Surface]:
    char_dir = assets_dir / char_folder
    if not char_dir.exists():
        # Fallback inteligente
        alt = "PERSONAJE M" if "H" in char_folder else "PERSONAJE H"
        if (assets_dir / alt).exists(): char_dir = assets_dir / alt
    
    prefix = "womanguardian" if "M" in char_folder.upper() or "WOMAN" in char_folder.upper() else "ecoguardian"

    def _load_seq(name: str) -> list[pygame.Surface]:
        files = []
        for ext in (".png", ".jpg", ".jpeg"):
            files += list(char_dir.glob(f"{prefix}_{name}_[0-9]*{ext}"))
        def _num(p: Path) -> int:
            m = re.search(r"_(\d+)\.\w+$", p.name)
            return int(m.group(1)) if m else 0
        files.sort(key=_num)
        seq: list[pygame.Surface] = []
        for p in files:
            img = pygame.image.load(str(p))
            seq.append(img.convert_alpha() if p.suffix.lower()==".png" else img.convert())
        return seq

    def _load_idle(name: str) -> Optional[pygame.Surface]:
        for ext in (".png", ".jpg", ".jpeg"):
            p = char_dir / f"{prefix}_{name}{ext}"
            if p.exists():
                img = pygame.image.load(str(p))
                return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
        return None

    right = _load_seq("walk_right"); left  = _load_seq("walk_left")
    down  = _load_seq("walk_down");  up    = _load_seq("walk_up")
    idle_right = _load_idle("right_idle"); idle_left  = _load_idle("left_idle")
    idle_down  = _load_idle("down_idle");  idle_up    = _load_idle("up_idle")

    if right and not left: left = [pygame.transform.flip(f, True, False) for f in right]
    if left and not right: right = [pygame.transform.flip(f, True, False) for f in left]
    if not down: down = right[:1] if right else []
    if not up:   up   = right[:1] if right else []

    if idle_right is None and right: idle_right = right[0]
    if idle_left  is None and idle_right is not None: idle_left = pygame.transform.flip(idle_right, True, False)
    if idle_down  is None and down:  idle_down = down[0]
    if idle_up    is None and up:    idle_up   = up[0]

    def _scale(f: pygame.Surface) -> pygame.Surface:
        if f.get_height() == 0: return pygame.Surface((int(target_h*0.7), target_h), pygame.SRCALPHA)
        h = target_h
        w = int(f.get_width() * (h / f.get_height()))
        return pygame.transform.smoothscale(f, (w, h))

    def _normalize_list(seq: list[pygame.Surface]) -> list[pygame.Surface]:
        if not seq: return seq
        max_w = max(f.get_width() for f in seq)
        H = seq[0].get_height()
        out = []
        for f in seq:
            c = pygame.Surface((max_w, H), pygame.SRCALPHA)
            rect = f.get_rect(midbottom=(max_w//2, H))
            c.blit(f, rect)
            out.append(c)
        return out

    def _normalize_single(s: pygame.Surface | None) -> pygame.Surface | None:
        if s is None:
             h = target_h
             w = int(h * 0.7)
             return pygame.Surface((w, h), pygame.SRCALPHA)
        S = _scale(s)
        c = pygame.Surface((S.get_width(), S.get_height()), pygame.SRCALPHA)
        c.blit(S, S.get_rect(midbottom=(c.get_width()//2, c.get_height())))
        return c

    return {
        "right": _normalize_list([_scale(f) for f in right]), 
        "left":  _normalize_list([_scale(f) for f in left]),
        "down":  _normalize_list([_scale(f) for f in down]),  
        "up":    _normalize_list([_scale(f) for f in up]),
        "idle_right": _normalize_single(idle_right), 
        "idle_left":  _normalize_single(idle_left),
        "idle_down":  _normalize_single(idle_down),  
        "idle_up":    _normalize_single(idle_up)
    }

# === CLASES DEL JUEGO ===

class ToolItem(pygame.sprite.Sprite):
    """La herramienta que aparece en el suelo."""
    def __init__(self, img: pygame.Surface, area_juego: pygame.Rect, center_pos: Tuple[int, int]):
        super().__init__()
        self.image = img
        self.rect = self.image.get_rect()
        self.area = area_juego
        self.glow_timer = 0.0
        # Espaunear SIEMPRE en el centro la primera vez
        self.rect.center = center_pos

    def respawn(self):
        # Aparecer en el CENTRO siempre para que sea fácil de ver
        self.rect.center = self.area.center

    def draw(self, screen):
        # Efecto de flotación y brillo para que se vea SIEMPRE
        self.glow_timer += 0.15
        offset = math.sin(self.glow_timer) * 8
        
        # Dibujar un círculo brillante detrás para que destaque sobre cualquier fondo
        glow_surf = pygame.Surface((80, 80), pygame.SRCALPHA)
        alpha = 150 + int(50*math.sin(self.glow_timer))
        pygame.draw.circle(glow_surf, (255, 255, 0, alpha), (40, 40), 35)
        
        draw_rect = self.rect.copy()
        draw_rect.y += int(offset)
        
        screen.blit(glow_surf, glow_surf.get_rect(center=draw_rect.center))
        screen.blit(self.image, draw_rect)

class Player(pygame.sprite.Sprite):
    def __init__(self, frames, pos, bounds, speed=340, anim_fps=8.0):
        super().__init__()
        self.frames = frames
        self.dir = "down"
        self.frame_idx = 0
        self.anim_timer = 0.0
        self.anim_dt = 1.0 / max(1.0, anim_fps)
        
        # Imagen inicial
        idle = self.frames.get("idle_down")
        if isinstance(idle, pygame.Surface): start_img = idle
        elif self.frames.get("down"): start_img = self.frames["down"][0]
        else: start_img = pygame.Surface((40,60), pygame.SRCALPHA)
            
        self.image = start_img 
        self.rect = self.image.get_rect(center=pos)
        self.speed = speed
        self.bounds = bounds
        self.has_tool = False 

    def update(self, dt):
        k = pygame.key.get_pressed()
        dx, dy = 0, 0
        
        # === CONTROLES INVERTIDOS (DIFICULTAD) ===
        if k[pygame.K_a] or k[pygame.K_LEFT]: dx = 1   # Izquierda -> Derecha
        if k[pygame.K_d] or k[pygame.K_RIGHT]: dx = -1 # Derecha -> Izquierda
        if k[pygame.K_w] or k[pygame.K_UP]: dy = 1     # Arriba -> Abajo
        if k[pygame.K_s] or k[pygame.K_DOWN]: dy = -1  # Abajo -> Arriba

        if dx != 0 or dy != 0:
            l = math.hypot(dx, dy); dx, dy = dx/l, dy/l
            
            self.rect.x += int(dx * self.speed * dt)
            self.rect.y += int(dy * self.speed * dt)
            self.rect.clamp_ip(self.bounds)

            # Animación (Visualmente correcta, aunque el movimiento sea invertido)
            if dx > 0: self.dir = "right"
            elif dx < 0: self.dir = "left"
            elif dy > 0: self.dir = "down"
            elif dy < 0: self.dir = "up"

            self.anim_timer += dt
            if self.anim_timer >= self.anim_dt:
                self.anim_timer -= self.anim_dt
                seq = self.frames.get(self.dir, [])
                if seq: 
                    self.frame_idx = (self.frame_idx + 1) % len(seq)
                    self.image = seq[self.frame_idx]
        else:
            # Idle
            ik = f"idle_{self.dir}"
            img = self.frames.get(ik)
            if isinstance(img, pygame.Surface): self.image = img
            elif self.frames.get(self.dir): self.image = self.frames[self.dir][0]
            self.frame_idx = 0

    def draw(self, screen):
        screen.blit(self.image, self.rect)
        if self.has_tool:
            # Indicador visual sobre la cabeza
            pygame.draw.circle(screen, (0, 0, 255), (self.rect.centerx, self.rect.top - 15), 8)
            pygame.draw.circle(screen, (255, 255, 255), (self.rect.centerx, self.rect.top - 15), 8, 2)

# ==========================================
# === FUNCIÓN PRINCIPAL ===
# ==========================================

def run(screen: pygame.Surface, assets_dir: Path, personaje: str = "EcoGuardian", dificultad: str = "Difícil"):
    W, H = screen.get_size()
    clock = pygame.time.Clock()
    pygame.font.init()
    
    # --- 1. CARGA OPTIMIZADA DE FONDOS ---
    path_roto = None; path_todo = None
    for f in assets_dir.glob("original.*"): path_roto = f; break
    for f in assets_dir.glob("img_4_todo.*"): path_todo = f; break

    bg_roto = load_image(assets_dir, [path_roto.stem] if path_roto else []) or pygame.Surface((W,H))
    bg_roto = pygame.transform.scale(bg_roto, (W, H))
    
    bg_todo = load_image(assets_dir, [path_todo.stem] if path_todo else []) or pygame.Surface((W,H))
    bg_todo = pygame.transform.scale(bg_todo, (W, H))
    
    if not path_todo: bg_todo.fill((100, 200, 100))

    # --- 2. CARGA DE HERRAMIENTA ---
    path_tool = assets_dir / "herramienta.png"
    if not path_tool.exists(): 
        for f in assets_dir.glob("tool*.*"): path_tool = f; break
    
    img_tool = load_image(assets_dir, ["herramienta", "tool", "martillo", "wrench"])
    if not img_tool: 
        img_tool = pygame.Surface((40,40)); img_tool.fill((0,0,255))
    img_tool = scale_to_width(img_tool, 60)

    # --- 3. UI & HUD ---
    font_hud = pygame.font.SysFont("arial", 26, bold=True)
    font_big = pygame.font.SysFont("arial", 48, bold=True)
    timer_font = pygame.font.SysFont("arial", 42, bold=True)
    
    # === CORRECCIÓN: AGREGADO "TEMPORAZIDOR" A LA LISTA DE BÚSQUEDA ===
    timer_panel = load_image(assets_dir, ["temporizador", "timer_panel", "TEMPORAZIDOR", "panel_tiempo"])
    icon_tool_hud = pygame.transform.smoothscale(img_tool, (40, 40))
    
    # Mensaje "Herramienta en mano"
    carry_label = font_hud.render("Herramienta en mano", True, BLANCO)
    carry_label_bg = pygame.Surface((carry_label.get_width() + 20, carry_label.get_height() + 10), pygame.SRCALPHA)
    pygame.draw.rect(carry_label_bg, (0,0,0,180), carry_label_bg.get_rect(), border_radius=8)
    carry_label_bg.blit(carry_label, (10, 5))

    # Win/Lose
    win_img = load_image(assets_dir, ["win_level3"]); 
    if win_img: win_img = pygame.transform.scale(win_img, (W,H))
    lose_img = load_image(assets_dir, ["lose_level3"]); 
    if lose_img: lose_img = pygame.transform.scale(lose_img, (W,H))
    
    pausa_panel_img = load_image(assets_dir / "PAUSA", ["nivelA 2", "panel_pausa"])

    # --- 4. CONFIGURACIÓN ---
    zones = {
        "TL": pygame.Rect(0, 0, W//4, H//2 - 50),           
        "TM": pygame.Rect(W//4, 0, W//4, H//2 - 50),        
        "BL": pygame.Rect(0, H//2 + 20, W//2, H//2 - 50),   
        "BR": pygame.Rect(W*2//3 + 80, H//2 + 40 - 30, W//3 - 80, H//2 - 50)
    }
    repaired_status = {k: False for k in zones}
    
    char_frames = load_char_frames(assets_dir, int(H*0.12), char_folder=personaje)
    player = Player(char_frames, (W//2, H//2), screen.get_rect())
    
    tool_item = ToolItem(img_tool, screen.get_rect().inflate(-100, -100), (W//2, H//2 + 100))
    
    remaining_ms = TOTAL_MS
    repair_progress = 0
    current_repairing = None
    victory = False; game_over = False; paused = False
    msg_text = ""; msg_timer = 0
    
    start_level_music(assets_dir)
    suspense_started = False

    def show_msg(txt):
        nonlocal msg_text, msg_timer
        msg_text = txt; msg_timer = 2.0 

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        ms = int(dt * 1000)
        
        for e in pygame.event.get():
            if e.type == pygame.QUIT: stop_level_music(); return "quit"
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: stop_level_music(); return "menu"
                if e.key == pygame.K_SPACE: paused = not paused
                
                if not paused and not game_over and not victory:
                    if e.key == pygame.K_e or e.key == pygame.K_RETURN:
                        # RECOGER HERRAMIENTA
                        if not player.has_tool:
                            if player.rect.colliderect(tool_item.rect.inflate(40, 40)):
                                player.has_tool = True
                                play_sfx("sfx_pick_seed", assets_dir)
                                show_msg(config.obtener_nombre("txt_herramienta_obt"))
                        else:
                            show_msg(config.obtener_nombre("txt_tutorial_msg7"))

        if not paused and not game_over and not victory:
            remaining_ms -= ms
            if remaining_ms <= 0: game_over = True; stop_level_music()
            
            if remaining_ms < SUSPENSE_TIME_MS and not suspense_started:
                start_suspense_music(assets_dir); suspense_started = True

            player.update(dt)
            
            keys = pygame.key.get_pressed()
            in_zone = None
            for k, rect in zones.items():
                if not repaired_status[k] and player.rect.colliderect(rect):
                    in_zone = k; break
            
            if in_zone and keys[pygame.K_r]:
                if player.has_tool:
                    current_repairing = in_zone
                    repair_progress += 1
                    if repair_progress >= TIEMPO_REPARACION:
                        repaired_status[in_zone] = True
                        repair_progress = 0; current_repairing = None
                        player.has_tool = False 
                        if not all(repaired_status.values()): tool_item.respawn() 
                        play_sfx("sfx_plant", assets_dir); show_msg(config.obtener_nombre("txt_zona_reparada"))
                        if all(repaired_status.values()): victory = True; stop_level_music()
                else:
                    if msg_timer <= 0: show_msg(config.obtener_nombre("txt_necesitas_herra"))
            else:
                repair_progress = 0; current_repairing = None
                
            if msg_timer > 0: msg_timer -= dt

        # --- DIBUJAR ---
        screen.blit(bg_roto, (0, 0))
        for k, is_fixed in repaired_status.items():
            if is_fixed: screen.blit(bg_todo, zones[k], area=zones[k])
        
        if not player.has_tool and not victory:
            tool_item.draw(screen)
            if player.rect.colliderect(tool_item.rect.inflate(60,60)):
                lbl = config.obtener_nombre("txt_recoger")
                t = font_hud.render(lbl, True, BLANCO)
                bg = pygame.Surface((t.get_width()+12, t.get_height()+8), pygame.SRCALPHA)
                bg.fill((0,0,0,160))
                rr = bg.get_rect(center=(tool_item.rect.centerx, tool_item.rect.top - 25))
                screen.blit(bg, rr.topleft)
                screen.blit(t, t.get_rect(center=rr.center))

        player.draw(screen)
        if player.has_tool: 
            screen.blit(carry_label_bg, (player.rect.centerx - carry_label_bg.get_width()//2, player.rect.top - 40))

        if current_repairing:
            bx = player.rect.centerx - 30; by = player.rect.top - 50
            pygame.draw.rect(screen, NEGRO, (bx, by, 60, 10))
            pct = repair_progress / TIEMPO_REPARACION
            pygame.draw.rect(screen, VERDE, (bx+1, by+1, 58*pct, 8))

        if player.has_tool and not current_repairing:
            glow_s = pygame.Surface((W, H), pygame.SRCALPHA)
            for k, rect in zones.items():
                if not repaired_status[k]:
                    # === CORRECCIÓN: QUITADO EL FONDO AMARILLO ===
                    # pygame.draw.rect(glow_s, (255, 255, 0, 40), rect) # <-- Comentado
                    if player.rect.colliderect(rect):
                        tr_txt = config.obtener_nombre("txt_reparar")
                        tr = font_hud.render(tr_txt, True, BLANCO)
                        bg_r = pygame.Surface((tr.get_width()+12, tr.get_height()+8), pygame.SRCALPHA)
                        bg_r.fill((0,0,0,150))
                        rrect = bg_r.get_rect(center=rect.center)
                        screen.blit(bg_r, rrect.topleft)
                        screen.blit(tr, tr.get_rect(center=rrect.center))
            screen.blit(glow_s, (0,0))

        # --- HUD (Timer y Contador) ---
        if not victory and not game_over:
            # Timer
            panel_rect = pygame.Rect(W - 200, 20, 180, 60)
            if timer_panel: screen.blit(pygame.transform.smoothscale(timer_panel, (180, 60)), panel_rect)
            else: pygame.draw.rect(screen, (50,50,50), panel_rect, border_radius=10)
            
            mm = (remaining_ms // 1000) // 60; ss = (remaining_ms // 1000) % 60
            
            # === CORRECCIÓN: Color del texto BLANCO para que siempre se vea ===
            timer_str = f"{mm}:{ss:02d}"
            
            # Si no hay panel o el fondo es oscuro, usamos blanco.
            # Si hay panel (madera), usamos negro o marrón oscuro.
            color_texto = (30, 20, 10) if timer_panel else BLANCO
            
            timer_txt = timer_font.render(timer_str, True, color_texto)
            
            # Renderizar en el centro del panel
            screen.blit(timer_txt, timer_txt.get_rect(center=panel_rect.center))

            # Contador (Icono + Texto Grande)
            screen.blit(icon_tool_hud, (30, 30))
            reparadas = sum(repaired_status.values())
            _lbl = config.obtener_nombre("txt_reparadas")
            txt_cnt = font_hud.render(f"{_lbl} {reparadas}/4", True, BLANCO)
            txt_sh = font_hud.render(f"{_lbl} {reparadas}/4", True, NEGRO)
            
            pos_x = 40 + icon_tool_hud.get_width()
            screen.blit(txt_sh, (pos_x+2, 37)); screen.blit(txt_cnt, (pos_x, 35))

            if msg_timer > 0:
                m_surf = font_big.render(msg_text, True, BLANCO); s_surf = font_big.render(msg_text, True, NEGRO)
                center = (W//2, H//4); m_rect = m_surf.get_rect(center=center)
                screen.blit(s_surf, (m_rect.x+2, m_rect.y+2)); screen.blit(m_surf, m_rect)

        if victory:
            if win_img: screen.blit(win_img, (0,0))
            else:
                overlay = pygame.Surface((W, H), pygame.SRCALPHA); overlay.fill((0, 0, 0, 180)); screen.blit(overlay, (0,0))
                v_surf = font_big.render(config.obtener_nombre("txt_zona_reparada"), True, VERDE)
                screen.blit(v_surf, v_surf.get_rect(center=(W//2, H//2)))
            pygame.display.flip(); pygame.time.wait(3000)
            try: import play; play.run(screen, assets_dir)
            except: return "menu"
            return "menu"

        if game_over:
            if lose_img: screen.blit(lose_img, (0,0))
            else:
                overlay = pygame.Surface((W, H), pygame.SRCALPHA); overlay.fill((50, 0, 0, 180)); screen.blit(overlay, (0,0))
                l_surf = font_big.render(config.obtener_nombre("txt_tiempo_agotado"), True, ROJO)
                screen.blit(l_surf, l_surf.get_rect(center=(W//2, H//2)))
            pygame.display.flip(); pygame.time.wait(3000)
            try: import play; play.run(screen, assets_dir)
            except: return "menu"
            return "menu"

        if paused:
             if pausa_panel_img:
                 s = pygame.transform.smoothscale(pausa_panel_img, (int(W*0.5), int(H*0.5)))
                 screen.blit(s, s.get_rect(center=(W//2, H//2)))
             else:
                 r = pygame.Rect(0,0,400,300); r.center=(W//2, H//2)
                 pygame.draw.rect(screen, (50,50,50), r, border_radius=10)
                 t = font_hud.render("PAUSA", True, BLANCO)
                 screen.blit(t, t.get_rect(center=r.center))

        pygame.display.flip()

    return "menu"
