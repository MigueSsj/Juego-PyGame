from __future__ import annotations
import pygame, math, random, re
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import config  # <--- IMPORTANTE: Importamos la configuración global

# ======================================================================
# === FUNCIONES BÁSICAS Y CLASES
# ======================================================================

try:
    from audio_shared import play_sfx, start_level_music, start_suspense_music, stop_level_music
except ImportError:
    def play_sfx(*args, **kwargs): pass
    def start_level_music(assets_dir: Path): pass
    def start_suspense_music(assets_dir: Path): pass
    def stop_level_music(): pass

TIEMPO_PARA_REPARAR_TUTORIAL = 1 

# === FUNCIONES DE AYUDA ===
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
    # Intentamos traducir los stems usando config.py
    translated_stems = [config.obtener_nombre(s) for s in stems]
    all_stems = translated_stems + stems
    
    for stem in all_stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
    return None

def load_surface(p: Path) -> pygame.Surface:
    img = pygame.image.load(str(p))
    return img.convert_alpha() if p.suffix.lower() == ".png" else img.convert()

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    if img.get_width() == 0: return pygame.Surface((new_w, new_w), pygame.SRCALPHA)
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height() * r)))

def make_glow(radius: int, color=(255, 255, 120)) -> pygame.Surface:
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for rr in range(radius, 0, -1):
        a = max(5, int(180 * (rr / radius) ** 2))
        pygame.draw.circle(s, (*color, a), (radius, radius), rr)
    return s

def _carry_anchor(player: pygame.sprite.Sprite, carrying_rect: pygame.Rect) -> tuple[int, int]:
    rect = player.rect
    cx, cy = rect.centerx, rect.centery
    cy = rect.centery + int(rect.height * 0.22)
    d = getattr(player, "dir", "down")
    if d == "left":
        cx -= int(rect.width * 0.12); cy += int(rect.height * 0.02)
    elif d == "right":
        cx += int(rect.width * 0.12); cy += int(rect.height * 0.02)
    elif d == "up":
        cy += int(rect.height * 0.06)
    else:
        cy += int(rect.height * 0.04)
    return cx, cy

def draw_key_icon(surf: pygame.Surface, key_char: str, pos: Tuple[int, int], size: int, color: Tuple[int, int, int] = (255, 255, 255)):
    key_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(key_surf, (30, 30, 30), key_surf.get_rect(), border_radius=4)
    pygame.draw.rect(key_surf, (150, 150, 150), key_surf.get_rect(), 1, border_radius=4)
    
    key_font = pygame.font.SysFont("arial", int(size * 0.7), bold=True)
    text = key_font.render(key_char.upper(), True, color)
    text_rect = text.get_rect(center=(size // 2, size // 2))
    key_surf.blit(text, text_rect)
    
    surf.blit(key_surf, key_surf.get_rect(center=pos))

def draw_movement_hud(surf: pygame.Surface, center_x: int, center_y: int, key_size: int, font: pygame.font.Font, text_label: str):
    KEY_S = key_size
    GAP = KEY_S + 5
    
    title_text = font.render(text_label, True, (255, 255, 255))
    surf.blit(title_text, title_text.get_rect(midbottom=(center_x + GAP*1.75, center_y - KEY_S * 1.5)))

    draw_key_icon(surf, "W", (center_x, center_y - GAP), KEY_S)
    draw_key_icon(surf, "A", (center_x - GAP, center_y), KEY_S)
    draw_key_icon(surf, "S", (center_x, center_y), KEY_S)
    draw_key_icon(surf, "D", (center_x + GAP, center_y), KEY_S)
    
    ARROW_GAP_X = GAP * 3.5
    draw_key_icon(surf, "▲", (center_x + ARROW_GAP_X, center_y - GAP), KEY_S, (100, 200, 255))
    draw_key_icon(surf, "◀", (center_x + ARROW_GAP_X - GAP, center_y), KEY_S, (100, 200, 255))
    draw_key_icon(surf, "▼", (center_x + ARROW_GAP_X, center_y), KEY_S, (100, 200, 255))
    draw_key_icon(surf, "▶", (center_x + ARROW_GAP_X + GAP, center_y), KEY_S, (100, 200, 255))

# === CLASES DE OBJETOS ===

class Trash(pygame.sprite.Sprite):
    def __init__(self, img: pygame.Surface, pos, scale_w: int):
        super().__init__()
        self.image = scale_to_width(img, scale_w)
        self.rect = self.image.get_rect(center=pos)
        self.glow = make_glow(int(max(self.rect.width, self.rect.height) * 0.9))
        self.carried = False
        self.phase = random.uniform(0, math.tau)
        self.is_delivered = False 
    def draw(self, surface: pygame.Surface, t: float):
        if not self.carried:
            pul = (math.sin(t + self.phase) + 1) * 0.5
            a = int(70 + 100 * pul)
            g = self.glow.copy()
            g.fill((255, 255, 255, a), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(g, g.get_rect(center=self.rect.center))
        surface.blit(self.image, self.rect)

class Seed:
    def __init__(self, pos: Tuple[int,int], img: pygame.Surface):
        self.image = img
        self.rect = img.get_rect(center=pos)
        self.taken = False
        self.is_carried = False
    def draw(self, surf: pygame.Surface):
        if not self.taken: surf.blit(self.image, self.rect)

class Hole:
    def __init__(self, pos: Tuple[int,int], img: pygame.Surface, assets_dir: Path):
        self.base_img = img
        self.rect = img.get_rect(center=pos)
        self.has_tree = False
        self.grow_timer = 0
        self.grow_step = 0
        self.glow = make_glow(int(max(self.rect.width, self.rect.height) * 0.8), color=(100, 255, 100))
        self.assets_dir = assets_dir
    
    def start_grow(self): self.grow_step, self.grow_timer = 1, 1
    def update(self, dt: int):
        if self.grow_timer > 0 and not self.has_tree:
            self.grow_timer += dt
            if self.grow_timer >= 1200: 
                self.grow_timer = 0
                self.has_tree = True
                play_sfx("sfx_grow", self.assets_dir)
    
    def draw(self, surf: pygame.Surface, arbol_img: pygame.Surface, show_glow: bool, t: float):
        if show_glow and not self.has_tree and self.grow_timer == 0:
            pul = (math.sin(t * 6.0) + 1) * 0.5
            a = int(100 + 100 * pul)
            g = self.glow.copy()
            g.fill((100, 255, 100, a), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(g, g.get_rect(center=self.rect.center))

        if not self.has_tree and self.grow_timer == 0:
            surf.blit(self.base_img, self.rect)
        elif self.has_tree:
            cx, cy = self.rect.center
            offset_y = int(self.rect.height * 0.43) 
            tree_midbottom_y = cy + offset_y 
            surf.blit(arbol_img, arbol_img.get_rect(midbottom=(cx, tree_midbottom_y)))

# CLASE PLAYER
class Player(pygame.sprite.Sprite):
    def __init__(self, frames: dict[str, list[pygame.Surface] | pygame.Surface],
                 pos, bounds: pygame.Rect, speed: float = 320, anim_fps: float = 8.0):
        super().__init__()
        self.frames = frames
        self.dir = "down"
        self.frame_idx = 0
        self.anim_timer = 0.0
        self.anim_dt = 1.0 / max(1.0, anim_fps)
        
        idle = self.frames.get("idle_down")
        if idle:
            self.image = idle if isinstance(idle, pygame.Surface) else idle[0]
        elif self.frames.get("down"):
            self.image = self.frames["down"][0]
        else:
            self.image = pygame.Surface((40,60), pygame.SRCALPHA); pygame.draw.rect(self.image, (0,200,0), self.image.get_rect(), 2)
            
        self.rect = self.image.get_rect(center=pos)
        self.speed = speed
        self.bounds = bounds
        self.carrying_image: Optional[pygame.Surface] = None
    
    def handle_input(self, dt: float):
        k = pygame.key.get_pressed()
        dx = (k[pygame.K_d] or k[pygame.K_RIGHT]) - (k[pygame.K_a] or k[pygame.K_LEFT])
        dy = (k[pygame.K_s] or k[pygame.K_DOWN])  - (k[pygame.K_w] or k[pygame.K_UP])
        moving = (dx != 0 or dy != 0)

        if moving:
            l = math.hypot(dx, dy);  dx, dy = dx / l, dy / l
            
            if abs(dx) >= abs(dy): 
                self.dir = "left" if dx > 0 else "right" 
            else: 
                self.dir = "down" if dy > 0 else "up"
            
            self.rect.x += int(dx * self.speed * dt)
            self.rect.y += int(dy * self.speed * dt)
            self.rect.clamp_ip(self.bounds)
            
            self.anim_timer += dt
            if self.anim_timer >= self.anim_dt:
                self.anim_timer -= self.anim_dt
                seq: list[pygame.Surface] = self.frames.get(self.dir, []) 
                if seq: self.frame_idx = (self.frame_idx + 1) % len(seq)
            
            seq: list[pygame.Surface] = self.frames.get(self.dir, []) 
            if seq: self.image = seq[self.frame_idx % len(seq)]
        else:
            idle_key = f"idle_{self.dir}"
            idle_img = self.frames.get(idle_key)
            if isinstance(idle_img, pygame.Surface): self.image = idle_img
            else:
                seq: list[pygame.Surface] = self.frames.get(self.dir, []) 
                self.image = seq[0] if seq else self.image
            self.frame_idx = 0
        
        new_midbottom = self.rect.midbottom
        self.rect = self.image.get_rect(midbottom=new_midbottom)
        self.rect.clamp_ip(self.bounds)
    
    def _get_carry_anchor(self) -> tuple[int, int]:
        rect = self.rect
        cx, cy = rect.centerx, rect.centery
        cy = rect.centery + int(rect.height * 0.22)
        
        if self.dir == "left": cx -= int(rect.width * 0.12); cy += int(rect.height * 0.02)
        elif self.dir == "right": cx += int(rect.width * 0.12); cy += int(rect.height * 0.02)
        elif self.dir == "up": cy += int(rect.height * 0.06)
        else: cy += int(rect.height * 0.04)
        return cx, cy

    def draw(self, surf: pygame.Surface):
        surf.blit(self.image, self.rect)
        if self.carrying_image:
            cx, cy = self._get_carry_anchor()
            anchor_rect = self.carrying_image.get_rect(center=(cx, cy))
            surf.blit(self.carrying_image, anchor_rect)

# Función de carga de frames
def load_char_frames(assets_dir: Path, target_h: int, *, char_folder: str = "PERSONAJE H") -> dict[str, list[pygame.Surface] | pygame.Surface]:
    char_dir = assets_dir / char_folder
    
    if not char_dir.exists():
        fallback_surf = pygame.Surface((int(target_h * 0.7), target_h), pygame.SRCALPHA)
        pygame.draw.rect(fallback_surf, (0, 150, 0), fallback_surf.get_rect(), 2) 
        return {
            "right": [fallback_surf], "left": [pygame.transform.flip(fallback_surf, True, False)], 
            "down": [fallback_surf], "up": [fallback_surf],
            "idle_right": fallback_surf, "idle_left": pygame.transform.flip(fallback_surf, True, False),
            "idle_down": fallback_surf, "idle_up": fallback_surf
        }

    prefix = "womanguardian" if "M" in char_folder.upper() else "ecoguardian"

    def _load_seq(name: str) -> list[pygame.Surface]:
        files: list[Path] = []
        for ext in (".png", ".jpg", ".jpeg"):
            files += list(char_dir.glob(f"{prefix}_{name}_[0-9]*{ext}"))
        files.sort(key=lambda p: int(re.search(r"_(\d+)\.\w+$", p.name).group(1)) if re.search(r"_(\d+)\.\w+$", p.name) else 0)
        seq: list[pygame.Surface] = [load_surface(p) for p in files]
        return seq
    
    def _scale_and_pad(img: pygame.Surface) -> pygame.Surface:
        if img.get_height() == 0: return pygame.Surface((int(target_h * 0.7), target_h), pygame.SRCALPHA)
        current_w, current_h = img.get_size()
        scale_ratio = target_h / current_h
        scaled_w = int(current_w * scale_ratio)
        scaled_img = pygame.transform.smoothscale(img, (scaled_w, target_h))
        standard_w = int(target_h * 0.7)
        final_surf = pygame.Surface((standard_w, target_h), pygame.SRCALPHA)
        x_offset = (standard_w - scaled_w) // 2
        final_surf.blit(scaled_img, (x_offset, 0))
        return final_surf

    frames_dict: Dict[str, Any] = {}
    
    walk_down_seq = [_scale_and_pad(f) for f in _load_seq("walk_down")]
    walk_up_seq = [_scale_and_pad(f) for f in _load_seq("walk_up")]
    walk_left_seq = [_scale_and_pad(f) for f in _load_seq("walk_left")]
    walk_right_seq = [_scale_and_pad(f) for f in _load_seq("walk_right")]

    if not walk_down_seq: walk_down_seq = [pygame.Surface((int(target_h * 0.7), target_h), pygame.SRCALPHA)]
    if not walk_up_seq: walk_up_seq = [walk_down_seq[0]]
    if not walk_left_seq: walk_left_seq = [pygame.transform.flip(walk_right_seq[0], True, False) if walk_right_seq else walk_down_seq[0]]
    if not walk_right_seq: walk_right_seq = [pygame.transform.flip(walk_left_seq[0], True, False) if walk_left_seq else walk_down_seq[0]]

    frames_dict["down"] = walk_down_seq
    frames_dict["up"] = walk_up_seq
    frames_dict["left"] = walk_left_seq
    frames_dict["right"] = walk_right_seq

    frames_dict["idle_down"] = _scale_and_pad(load_image(char_dir, [f"{prefix}_idle_down"]) or walk_down_seq[0])
    frames_dict["idle_up"] = _scale_and_pad(load_image(char_dir, [f"{prefix}_idle_up"]) or walk_up_seq[0])
    frames_dict["idle_left"] = _scale_and_pad(load_image(char_dir, [f"{prefix}_idle_left"]) or walk_left_seq[0])
    frames_dict["idle_right"] = _scale_and_pad(load_image(char_dir, [f"{prefix}_idle_right"]) or walk_right_seq[0])
    
    return frames_dict

def load_bg_fit(assets_dir: Path, W: int, H: int, stems: List[str]) -> tuple[pygame.Surface, pygame.Rect]:
    p = find_by_stem(assets_dir, stems[0])
    if p:
        img = load_surface(p)
    else:
        found_img = False
        for stem in stems:
            temp_p = find_by_stem(assets_dir, stem)
            if temp_p:
                img = load_surface(temp_p)
                found_img = True
                break
        
        if not found_img:
            if stems[0] == "nivel1_parque": img = pygame.Surface((W, H)); img.fill((40, 120, 40)) 
            elif "nivel2_calle" in stems or "n2_fondo_calle" in stems: img = pygame.Surface((W, H)); img.fill((60, 60, 60)) 
            elif "nivel3_plaza" in stems or "plaza_central" in stems or "original" in stems: img = pygame.Surface((W, H)); img.fill((100, 100, 100))
            else: img = pygame.Surface((W, H)); img.fill((100, 100, 100))

    iw, ih = img.get_size()
    ratio = min(W / iw, H / ih) if iw and ih else 1.0
    new_w, new_h = int(iw * ratio), int(ih * ratio)
    scaled = pygame.transform.smoothscale(img, (new_w, new_h))
    rect = scaled.get_rect(center=(W // 2, H // 2))
    return scaled, rect

# ======================================================================
# === FUNCIÓN PRINCIPAL DEL TUTORIAL
# ======================================================================

BLANCO = (255, 255, 255); GRIS = (100, 100, 100); VERDE = (0, 200, 0)
ROJO_OSCURO = (180, 0, 0); ROJO_ALERTA = (255, 50, 50); AMARILLO = (255, 215, 0)

def run(screen: pygame.Surface, assets_dir: Path, personaje: str = "EcoGuardian", dificultad: str = "Fácil"):
    pygame.font.init()
    clock = pygame.time.Clock()
    W, H = screen.get_size()
    
    # --- Fuentes ---
    font = pygame.font.SysFont("arial", 26, bold=True)
    small_font = pygame.font.SysFont("arial", 20, bold=True)
    timer_font = pygame.font.SysFont("arial", 40, bold=True) 
    
    # --- Carga de Assets del Nivel 3 ---
    bg_roto = load_image(assets_dir, ["original", "img_3_roto", "nivel3_plaza_roto"])
    if bg_roto: bg_roto = pygame.transform.scale(bg_roto, (W, H))
    
    bg_todo = load_image(assets_dir, ["img_4_todo", "nivel3_plaza_todo"])
    if bg_todo: bg_todo = pygame.transform.scale(bg_todo, (W, H))

    # Bote de Basura
    BIN_SCALE = 0.24 
    bin_img = load_image(assets_dir, ["basurero", "bote_basura", "trash_bin"])
    if bin_img is None: bin_img = pygame.Surface((int(W * 0.15), int(W * 0.20)), pygame.SRCALPHA); bin_img.fill((90, 90, 90))
    bin_img = scale_to_width(bin_img, int(W * BIN_SCALE))
    bin_rect = bin_img.get_rect()
    bin_rect.bottomright = (W - int(W * 0.05), H - int(W * 0.05))
    BIN_RADIUS = max(36, int(W * 0.05))
    
    # Basura/Semilla/Hoyo/Árbol
    sprite_trash = load_image(assets_dir, ["trash_01", "trash_"])
    if sprite_trash is None: sprite_trash = pygame.Surface((40, 40)); sprite_trash.fill((160, 160, 160))
    
    img_hoyo_surf = load_image(assets_dir, ["n2_hoyo", "hoyo"])
    if img_hoyo_surf is None: img_hoyo_surf = pygame.Surface((66, 66)); img_hoyo_surf.fill((139, 69, 19))
    img_hoyo = scale_to_width(img_hoyo_surf, 66)
    
    img_semilla_surf = load_image(assets_dir, ["n2_semilla", "semilla"])
    if img_semilla_surf is None: img_semilla_surf = pygame.Surface((44, 44)); img_semilla_surf.fill((150, 255, 150))
    img_semilla = scale_to_width(img_semilla_surf, 44)

    img_arbol_surf = load_image(assets_dir, ["n2_arbol", "arbol"])
    if img_arbol_surf is None: img_arbol_surf = pygame.Surface((180, 180)); img_arbol_surf.fill((0, 128, 0))
    img_arbol = scale_to_width(img_arbol_surf, 180)

    # Flecha Indicadora
    arrow_img_orig = load_image(assets_dir, ["flecha_indicador", "arrow_indicator", "arrow"])
    if arrow_img_orig is None:
        arrow_img_orig = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.polygon(arrow_img_orig, (255,200,0), [(0,30),(15,0),(30,30)])
    arrow_img = scale_to_width(arrow_img_orig, 30)
    counter_icon_trash = load_image(assets_dir, ["contador_basura"])
    counter_icon_seed = load_image(assets_dir, ["semillita_entregada"])
    counter_icon_buildings = load_image(assets_dir, ["contador_edificios"])
    if counter_icon_trash: counter_icon_trash = scale_to_width(counter_icon_trash, int(W * 0.12))
    if counter_icon_seed: counter_icon_seed = scale_to_width(counter_icon_seed, int(W * 0.12))
    if counter_icon_buildings: counter_icon_buildings = scale_to_width(counter_icon_buildings, int(W * 0.12))
    timer_panel_img = load_image(assets_dir, ["temporizador", "timer_panel", "panel_tiempo", "TEMPORIZADOR", "TEMPORAZIDOR"])
    
    # Controles y Distancia de Interacción
    INTERACT_KEYS = (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE)
    INTERACT_DIST = int(W * 0.06)
    
    # --- Estado del Tutorial ---
    tutorial_phase = 0 
    
    # Fase 0: Inicialización
    background, bg_rect = load_bg_fit(assets_dir, W, H, ["nivel1_parque"]) 
    
    char_target_h = int(H * 0.14)
    frames = load_char_frames(assets_dir, target_h=char_target_h, char_folder=personaje)
    player = Player(frames, (W // 2, H // 2), screen.get_rect(), speed=320, anim_fps=8.0)
    
    # Objetos para Fase 0
    trash_obj = Trash(sprite_trash, (W // 2, H * 0.8), int(W * 0.035))
    carrying: Optional[Trash] = None 
    
    # Objetos para Fase 1
    seed_obj: Optional[Seed] = None
    hole_obj: Optional[Hole] = None
    carrying_seed = False          
    
    # Objetos para Fase 2 (Reparación)
    repair_zone_key = "BR" 
    zones_map = {
        "BR": pygame.Rect(int(W * 0.66), int(H * 0.55), int(W * 0.30), int(H * 0.40)) 
    }
    estado_reparacion = { "BR": False }
    reparando_actualmente = None
    progreso_reparacion = 0
    
    # --- TEMPORIZADOR DEL NIVEL 3 (50 Segundos) ---
    level_timer = 50.0  
    game_over = False
    hud_overlay_timer = 10.0
    transition_target_phase: int | None = None
    transition_delay = 0.0
    
    # Mensajes
    current_tutorial_msg = ""
    message_timer = 0.0
    message_duration = 3.5 
    
    def set_message(msg: str, duration: float = 3.5):
        nonlocal current_tutorial_msg, message_timer, message_duration
        current_tutorial_msg = msg
        message_duration = duration
        message_timer = message_duration
    
    # --- Bucle Principal ---
    t = 0.0
    running = True
    start_level_music(assets_dir)

    while running:
        dt_ms = clock.tick(60)
        dt_sec = dt_ms / 1000.0
        t += dt_sec
        interact = False
        reparar_key_pressed = False

        if message_timer > 0.0:
            message_timer = max(0.0, message_timer - dt_sec)
        if hud_overlay_timer > 0.0:
            hud_overlay_timer = max(0.0, hud_overlay_timer - dt_sec)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                stop_level_music(); return "menu"
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    stop_level_music(); return "menu"
                
                # Solo procesar input si no es Game Over
                if not game_over:
                    if e.key in INTERACT_KEYS:
                        interact = True
                    if e.key == pygame.K_r: # Tecla de Reparación del Nivel 3
                        reparar_key_pressed = True

        # ----------------------------------------------------------------------
        # LÓGICA DE JUEGO (Actualización)
        # ----------------------------------------------------------------------

        if not game_over:
            player.handle_input(dt_sec)
        
        if carrying:
            ax, ay = _carry_anchor(player, carrying.rect)
            carrying.rect.center = (ax, ay)
        if carrying_seed:
            player.carrying_image = img_semilla
        else:
            if not carrying:
                player.carrying_image = None
        
        if hole_obj:
            hole_obj.update(dt_ms)

        # --- Interacción ---
        if interact and not game_over:
            if tutorial_phase == 0:
                # FASE 0: BASURA
                if not carrying:
                    d = math.hypot(player.rect.centerx - trash_obj.rect.centerx,
                                   player.rect.centery - trash_obj.rect.centery)
                    if d <= INTERACT_DIST and not trash_obj.is_delivered:
                        carrying = trash_obj
                        carrying.carried = True
                        set_message(config.obtener_nombre("txt_tutorial_msg1"), 1.5)
                        play_sfx("sfx_pick_up", assets_dir)
                else:
                    d = math.hypot(player.rect.centerx - bin_rect.centerx,
                                   player.rect.centery - bin_rect.centery)
                    if d <= BIN_RADIUS * 1.5:
                        trash_obj.is_delivered = True
                        carrying = None
                        
                        set_message(config.obtener_nombre("txt_tutorial_msg2"), 4.0)
                        play_sfx("sfx_win", assets_dir)
                        transition_target_phase = 1
                        transition_delay = 0.6
                        
            elif tutorial_phase == 1:
                # FASE 1: PLANTACIÓN
                if not carrying_seed:
                    d = math.hypot(player.rect.centerx - seed_obj.rect.centerx,
                                   player.rect.centery - seed_obj.rect.centery)
                    if d <= INTERACT_DIST and not seed_obj.taken:
                        seed_obj.taken = True
                        carrying_seed = True
                        player.carrying_image = img_semilla
                        set_message(config.obtener_nombre("txt_tutorial_msg3"), 2.0)
                        play_sfx("sfx_pick_seed", assets_dir)
                else:
                    d = math.hypot(player.rect.centerx - hole_obj.rect.centerx,
                                   player.rect.centery - hole_obj.rect.centery)
                    if d <= INTERACT_DIST and not hole_obj.has_tree and hole_obj.grow_timer == 0:
                        carrying_seed = False
                        player.carrying_image = None
                        hole_obj.start_grow()
                        set_message(config.obtener_nombre("txt_tutorial_msg4"), 3.0)
                        play_sfx("sfx_plant", assets_dir)
            
            # --- Fase 3 (Conclusión) se activa en la lógica de reparación ---

        # --- Lógica de Transición de Fase 1 a Fase 2 ---
        if tutorial_phase == 1 and hole_obj and hole_obj.has_tree and transition_target_phase is None:
             set_message(config.obtener_nombre("txt_tutorial_msg5"), 4.0)
             transition_target_phase = 2
             transition_delay = 0.6

        # --- Ejecutar transición diferida ---
        if transition_target_phase is not None:
            transition_delay = max(0.0, transition_delay - dt_sec)
            if transition_delay == 0.0:
                if transition_target_phase == 1:
                    tutorial_phase = 1
                    hud_overlay_timer = 10.0
                    background, bg_rect = load_bg_fit(assets_dir, W, H, ["nivel2_calle", "n2_fondo_calle", "calle"]) 
                    player.rect.center = (W // 2, H // 2)
                    seed_obj = Seed((W // 4, H * 3 // 4), img_semilla)
                    hole_obj = Hole((W * 2 // 5, H * 2 // 5), img_hoyo, assets_dir)
                elif transition_target_phase == 2:
                    tutorial_phase = 2
                    level_timer = 50.0
                    hud_overlay_timer = 10.0
                    background = bg_roto
                    background.get_rect(topleft=(0,0))
                    player.rect.center = (W // 2, H * 0.7)
                transition_target_phase = None
             
        # --- LÓGICA ESPECÍFICA DE REPARACIÓN (FASE 2) ---
        if tutorial_phase == 2:
            
            # 1. Actualizar Timer
            if not game_over and not estado_reparacion[repair_zone_key]:
                level_timer -= dt_sec
                
                # CONDICIÓN DE DERROTA (TIEMPO AGOTADO)
                if level_timer <= 0:
                    level_timer = 0
                    game_over = True
                    play_sfx("sfx_lose", assets_dir) 
                    set_message(config.obtener_nombre("txt_tutorial_fail"), 5.0)
                    # Forzar salida a fase final de derrota tras el mensaje
                    tutorial_phase = 99 

            # 2. Lógica de Reparación
            if not game_over:
                zona_activa = None
                if not estado_reparacion[repair_zone_key]:
                    if player.rect.colliderect(zones_map[repair_zone_key]):
                         zona_activa = repair_zone_key
                
                if zona_activa and reparar_key_pressed:
                    reparando_actualmente = zona_activa
                    progreso_reparacion += 1
                    
                    # REPARACIÓN INSTANTÁNEA PARA EL TUTORIAL
                    if progreso_reparacion >= TIEMPO_PARA_REPARAR_TUTORIAL:
                        estado_reparacion[zona_activa] = True
                        progreso_reparacion = 0
                        reparando_actualmente = None
                        play_sfx("sfx_win", assets_dir) 
                        
                        # PASAR A FASE 3 (FIN)
                        set_message(config.obtener_nombre("txt_tutorial_msg6"), 5.0)
                        tutorial_phase = 3
                elif not reparar_key_pressed:
                    progreso_reparacion = 0; reparando_actualmente = None
            
        # --- Lógica de salida al terminar el tutorial (Fase 3 o 99) ---
        if (tutorial_phase == 3 or tutorial_phase == 99) and message_timer <= 0.0:
            running = False

        # ----------------------------------------------------------------------
        # LÓGICA DE DIBUJO
        # ----------------------------------------------------------------------
        
        screen.fill((34, 45, 38))
        screen.blit(background, bg_rect)
        
        if tutorial_phase == 0:
            # DIBUJO FASE 0
            screen.blit(bin_img, bin_rect) 
            trash_obj.draw(screen, t) 
            # Contador estilo nivel (solo imagen del contador del nivel)
            if counter_icon_trash:
                contador_rect = counter_icon_trash.get_rect(topleft=(int(W * 0.015), int(H * 0.10)))
                screen.blit(counter_icon_trash, contador_rect)
                num_font = pygame.font.SysFont("arial", max(18, int(H * 0.055)), bold=True)
                num = 1 if trash_obj.is_delivered else 0
                num_s = num_font.render(str(num), True, (255, 255, 255))
                num_sh = num_font.render(str(num), True, (0, 0, 0))
                nr = num_s.get_rect(midright=(contador_rect.right - 20, contador_rect.top + contador_rect.height // 2))
                screen.blit(num_sh, num_sh.get_rect(center=(nr.centerx + 2, nr.centery + 2)))
                screen.blit(num_s, nr)
            
            if hud_overlay_timer > 0.0:
                margin_x = int(W * 0.04)
                margin_y = int(H * 0.04)
                panel_w, panel_h = int(W * 0.18), int(H * 0.11)
                panel_rect = pygame.Rect(W - margin_x - panel_w, margin_y, panel_w, panel_h)
                if timer_panel_img:
                    scaled = pygame.transform.smoothscale(timer_panel_img, (panel_rect.w, panel_rect.h))
                    screen.blit(scaled, panel_rect.topleft)
                else:
                    pygame.draw.rect(screen, (30, 20, 15), panel_rect, border_radius=10)
                    inner = panel_rect.inflate(-10, -10)
                    pygame.draw.rect(screen, (210, 180, 140), inner, border_radius=8)
                remaining_overlay = int(hud_overlay_timer)
                mm = remaining_overlay // 60; ss = remaining_overlay % 60
                time_str = f"{mm}:{ss:02d}"
                txt = timer_font.render(time_str, True, (20, 15, 10))
                sh = timer_font.render(time_str, True, (0, 0, 0))
                screen.blit(sh, sh.get_rect(center=(panel_rect.centerx + 2, panel_rect.centery + 2)))
                screen.blit(txt, txt.get_rect(center=(panel_rect.centerx, panel_rect.centery)))
            # HUD y Flechas...
            if not carrying and not trash_obj.is_delivered: 
                # Se pasa el texto traducido al HUD desde config
                draw_movement_hud(screen, W // 2 - 100, H // 4, 30, font, config.obtener_nombre("txt_movimiento"))
            
            if carrying and not trash_obj.is_delivered:
                target_center = bin_rect.center; player_center = player.rect.center
                angle = math.atan2(target_center[1] - player_center[1], target_center[0] - player_center[0])
                arrow_rotated = pygame.transform.rotate(arrow_img, -math.degrees(angle) - 90)
                arrow_distance = player.rect.height * 0.7
                arrow_x = player_center[0] + arrow_distance * math.cos(angle); arrow_y = player_center[1] + arrow_distance * math.sin(angle)
                screen.blit(arrow_rotated, arrow_rotated.get_rect(center=(int(arrow_x), int(arrow_y))))

            if not carrying and not trash_obj.is_delivered:
                 d = math.hypot(player.rect.centerx - trash_obj.rect.centerx, player.rect.centery - trash_obj.rect.centery)
                 if d <= INTERACT_DIST:
                    txt = small_font.render(config.obtener_nombre("txt_recoger"), True, BLANCO); screen.blit(txt, txt.get_rect(midbottom=(trash_obj.rect.centerx, trash_obj.rect.top - 20)))
            if carrying and not trash_obj.is_delivered:
                d = math.hypot(player.rect.centerx - bin_rect.centerx, player.rect.centery - bin_rect.centery)
                if d <= BIN_RADIUS * 1.5:
                    txt = small_font.render(config.obtener_nombre("txt_depositar_e"), True, BLANCO); screen.blit(txt, txt.get_rect(midbottom=(bin_rect.centerx, bin_rect.top - 20)))


        elif tutorial_phase == 1:
            # DIBUJO FASE 1
            if seed_obj: seed_obj.draw(screen)
            if hole_obj: hole_obj.draw(screen, img_arbol, show_glow=carrying_seed, t=t)
            # Contador estilo nivel fase 1
            if counter_icon_seed:
                contador_rect = counter_icon_seed.get_rect(topleft=(int(W * 0.015), int(H * 0.10)))
                screen.blit(counter_icon_seed, contador_rect)
                num_font = pygame.font.SysFont("arial", max(18, int(H * 0.055)), bold=True)
                num = 1 if (hole_obj and hole_obj.has_tree) else 0
                num_s = num_font.render(str(num), True, (255, 255, 255))
                num_sh = num_font.render(str(num), True, (0, 0, 0))
                nr = num_s.get_rect(midright=(contador_rect.right - 20, contador_rect.top + contador_rect.height // 2))
                screen.blit(num_sh, num_sh.get_rect(center=(nr.centerx + 2, nr.centery + 2)))
                screen.blit(num_s, nr)
            
            if hud_overlay_timer > 0.0:
                margin_x = int(W * 0.04)
                margin_y = int(H * 0.04)
                panel_w, panel_h = int(W * 0.18), int(H * 0.11)
                panel_rect = pygame.Rect(W - margin_x - panel_w, margin_y, panel_w, panel_h)
                if timer_panel_img:
                    scaled = pygame.transform.smoothscale(timer_panel_img, (panel_rect.w, panel_rect.h))
                    screen.blit(scaled, panel_rect.topleft)
                else:
                    pygame.draw.rect(screen, (30, 20, 15), panel_rect, border_radius=10)
                    inner = panel_rect.inflate(-10, -10)
                    pygame.draw.rect(screen, (210, 180, 140), inner, border_radius=8)
                remaining_overlay = int(hud_overlay_timer)
                mm = remaining_overlay // 60; ss = remaining_overlay % 60
                time_str = f"{mm}:{ss:02d}"
                txt = timer_font.render(time_str, True, (20, 15, 10))
                sh = timer_font.render(time_str, True, (0, 0, 0))
                screen.blit(sh, sh.get_rect(center=(panel_rect.centerx + 2, panel_rect.centery + 2)))
                screen.blit(txt, txt.get_rect(center=(panel_rect.centerx, panel_rect.centery)))
            if not carrying_seed and seed_obj and not seed_obj.taken: 
                draw_movement_hud(screen, W // 2 - 100, H // 4, 30, font, config.obtener_nombre("txt_movimiento"))

            if carrying_seed and hole_obj and not hole_obj.has_tree and hole_obj.grow_timer == 0:
                target_center = hole_obj.rect.center; player_center = player.rect.center
                angle = math.atan2(target_center[1] - player_center[1], target_center[0] - player_center[0])
                arrow_rotated = pygame.transform.rotate(arrow_img, -math.degrees(angle) - 90)
                arrow_distance = player.rect.height * 0.7
                arrow_x = player_center[0] + arrow_distance * math.cos(angle); arrow_y = player_center[1] + arrow_distance * math.sin(angle)
                screen.blit(arrow_rotated, arrow_rotated.get_rect(center=(int(arrow_x), int(arrow_y))))

            if seed_obj and not carrying_seed and not seed_obj.taken:
                if player.rect.colliderect(seed_obj.rect.inflate(20, 20)):
                    txt = small_font.render(config.obtener_nombre("txt_recoger_semilla"), True, BLANCO); screen.blit(txt, txt.get_rect(midbottom=(seed_obj.rect.centerx, seed_obj.rect.top - 20)))

            if hole_obj and carrying_seed and not hole_obj.has_tree and hole_obj.grow_timer == 0:
                if player.rect.colliderect(hole_obj.rect.inflate(20, 20)):
                    txt = small_font.render(config.obtener_nombre("txt_plantar_semilla"), True, BLANCO); screen.blit(txt, txt.get_rect(midbottom=(hole_obj.rect.centerx, hole_obj.rect.top - 20)))
            
        elif tutorial_phase >= 2 and tutorial_phase != 99:
            # DIBUJO FASE 2 / 3
            
            rect_target = zones_map[repair_zone_key]

            # Dibujar la zona reparada sobre el fondo roto
            if estado_reparacion[repair_zone_key] and bg_todo:
                screen.blit(bg_todo, rect_target.topleft, area=rect_target)

            # Indicador de Reparación [R] y Flecha al objetivo
            if not estado_reparacion[repair_zone_key]:
                center_target = rect_target.center
                
                # Flecha indicadora al edificio
                player_center = player.rect.center
                angle = math.atan2(center_target[1] - player_center[1], center_target[0] - player_center[0])
                arrow_rotated = pygame.transform.rotate(arrow_img, -math.degrees(angle) - 90)
                arrow_distance = player.rect.height * 0.7
                arrow_x = player_center[0] + arrow_distance * math.cos(angle); arrow_y = player_center[1] + arrow_distance * math.sin(angle)
                screen.blit(arrow_rotated, arrow_rotated.get_rect(center=(int(arrow_x), int(arrow_y))))
                
                # Mensaje de Reparar
                if player.rect.colliderect(rect_target):
                     txt = small_font.render(config.obtener_nombre("txt_reparar"), True, BLANCO);
                     screen.blit(txt, txt.get_rect(center=(center_target[0], center_target[1] + 10)))
                     
            # Barra de progreso cuando reparando
            if reparando_actualmente:
                 pos_barra_x = player.rect.centerx - 25
                 pos_barra_y = player.rect.top - 30
                 pygame.draw.rect(screen, GRIS, (pos_barra_x, pos_barra_y, 50, 10), border_radius=2)
                 ancho_progreso = 50 * (progreso_reparacion / TIEMPO_PARA_REPARAR_TUTORIAL)
                 pygame.draw.rect(screen, VERDE, (pos_barra_x, pos_barra_y, ancho_progreso, 10), border_radius=2)

            # Contador estilo nivel fase 2
            if counter_icon_buildings:
                contador_rect = counter_icon_buildings.get_rect(topleft=(int(W * 0.015), int(H * 0.10)))
                screen.blit(counter_icon_buildings, contador_rect)
                num_font = pygame.font.SysFont("arial", max(18, int(H * 0.055)), bold=True)
                num = 1 if estado_reparacion[repair_zone_key] else 0
                num_s = num_font.render(str(num), True, (255, 255, 255))
                num_sh = num_font.render(str(num), True, (0, 0, 0))
                nr = num_s.get_rect(midright=(contador_rect.right - 20, contador_rect.top + contador_rect.height // 2))
                screen.blit(num_sh, num_sh.get_rect(center=(nr.centerx + 2, nr.centery + 2)))
                screen.blit(num_s, nr)

            panel_rect = pygame.Rect(W - margin_x - panel_w, margin_y, panel_w, panel_h)
            if timer_panel_img:
                scaled = pygame.transform.smoothscale(timer_panel_img, (panel_rect.w, panel_rect.h))
                screen.blit(scaled, panel_rect.topleft)
            else:
                pygame.draw.rect(screen, (30, 20, 15), panel_rect, border_radius=10)
                inner = panel_rect.inflate(-10, -10)
                pygame.draw.rect(screen, (210, 180, 140), inner, border_radius=8)
            remaining_int = int(max(0.0, level_timer))
            mm = remaining_int // 60; ss = remaining_int % 60
            color_timer = ROJO_ALERTA if remaining_int < 10 else (20, 15, 10)
            time_str = f"{mm}:{ss:02d}"
            txt = timer_font.render(time_str, True, color_timer)
            sh = timer_font.render(time_str, True, (0, 0, 0))
            screen.blit(sh, sh.get_rect(center=(panel_rect.centerx + 2, panel_rect.centery + 2)))
            screen.blit(txt, txt.get_rect(center=(panel_rect.centerx, panel_rect.centery)))


        player.draw(screen)
        
        # --- DIBUJO DE MENSAJE PRINCIPAL ---
        if message_timer > 0.0 and current_tutorial_msg:
            msg_font = pygame.font.SysFont("arial", 40, bold=True)
            a = int(255 * (message_timer / message_duration))
            
            # Ajuste de color si es mensaje de Game Over
            color_msg = ROJO_ALERTA if tutorial_phase == 99 else BLANCO
            
            msg_surf = msg_font.render(current_tutorial_msg, True, color_msg)
            shadow = msg_font.render(current_tutorial_msg, True, (0, 0, 0))

            msg_x = W // 2; msg_y = H // 2 + int(H * 0.08)

            shadow_s = shadow.copy(); shadow_s.set_alpha(a)
            msg_s = msg_surf.copy(); msg_s.set_alpha(a)

            screen.blit(shadow_s, shadow_s.get_rect(center=(msg_x + 4, msg_y + 4)))
            screen.blit(msg_s, msg_s.get_rect(center=(msg_x, msg_y)))
            
        pygame.display.flip()
        
    # --- FIN DEL JUEGO (Salida al menú de selección) ---
    stop_level_music()
    try:
        import play
        play.run(screen, assets_dir) 
    except ImportError:
        pass
    return "menu"
