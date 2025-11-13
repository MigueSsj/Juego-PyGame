from __future__ import annotations
import pygame, random, re, math
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

try:
    # === CAMBIO: Importar funciones de música ===
    from audio_shared import play_sfx, start_level_music, start_suspense_music, stop_level_music
except Exception:
    # Esta función 'falsa' aceptará cualquier argumento y no hará nada
    def play_sfx(*args, **kwargs): pass
    def start_level_music(assets_dir: Path): pass
    def start_suspense_music(assets_dir: Path): pass
    def stop_level_music(): pass

# === FUNCIONES DE AYUDA PARA CARGAR IMÁGENES (Se quedan fuera) ===
def find_by_stem(assets_dir: Path, stem: str) -> Optional[Path]:
    """Busca una imagen por el 'stem' (nombre sin extensión)."""
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
    """Carga la primera imagen que encuentre de una lista de nombres."""
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
    return None

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    """Escala una imagen a un nuevo ancho, manteniendo la proporción."""
    if img.get_width() == 0: return pygame.Surface((new_w, new_w), pygame.SRCALPHA)
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height() * r)))

# === CONSTANTES DEL NIVEL (Se quedan fuera) ===
ASSET_STEMS = {
    "fondo":       ["n2_fondo_calle"],
    "hoyo":        ["n2_hoyo"],
    "semilla":     ["n2_semilla"],
    "arbol":       ["n2_arbol"],
    "victoria":    ["n2_victoria_calle_verde"],
    "timer_panel": ["temporizador", "timer_panel", "panel_tiempo", "TEMPORAZIDOR"],
}
SAFE_SPAWN_AREAS = [
    pygame.Rect(80, 380, 150, 80),  # Izquierda del árbol superior izquierdo
    pygame.Rect(330, 380, 830, 80), # Entre los dos árboles superiores
    pygame.Rect(80, 540, 1000, 140), 
]
SEEDS_TO_SPAWN = 5
HOLES_TO_SPAWN = 5
TOTAL_HOLES = HOLES_TO_SPAWN
GROW_STEPS = 3
GROW_TIME_PER_STEP = 220  # ms

# === CLASES (Se quedan fuera) ===

# === INICIO: CÓDIGO COPIADO DE NIVEL 1 (MANEJO DE PERSONAJE) ===
def load_char_frames(assets_dir: Path, target_h: int, *, char_folder: str = "PERSONAJE H") -> dict[str, list[pygame.Surface] | pygame.Surface]:
    char_dir = assets_dir / char_folder
    if not char_dir.exists():
        # Fallback a H si M no existe, o viceversa
        alt_folder = "PERSONAJE H" if "M" in char_folder else "PERSONAJE M"
        if (assets_dir / alt_folder).exists():
            print(f"WARN: Carpeta '{char_folder}' no encontrada. Usando '{alt_folder}'.")
            char_dir = assets_dir / alt_folder
        else:
            raise FileNotFoundError(f"No se encontró la carpeta 'assets/{char_folder}' ni una alternativa.")

    # === ¡LÓGICA DE PREFIJO (womanguardian)! ===
    if "M" in char_folder.upper():
        prefix = "womanguardian"
    else:
        prefix = "ecoguardian"
    # ==================================

    def _load_seq(name: str) -> list[pygame.Surface]:
        # Usa el prefijo dinámico
        files: list[Path] = []
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
        # Usa el prefijo dinámico
        for ext in (".png", ".jpg", ".jpeg"):
            p = char_dir / f"{prefix}_{name}{ext}"
            if p.exists():
                img = pygame.image.load(str(p))
                return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
        return None

    # Carga usando nombres genéricos
    right = _load_seq("walk_right")
    left  = _load_seq("walk_left")
    down  = _load_seq("walk_down")
    up    = _load_seq("walk_up")

    idle_right = _load_idle("right_idle")
    idle_left  = _load_idle("left_idle")
    idle_down  = _load_idle("down_idle")
    idle_up    = _load_idle("up_idle")

    if right and not left: left = [pygame.transform.flip(f, True, False) for f in right]
    if left and not right: right = [pygame.transform.flip(f, True, False) for f in left]
    if not down: down = right[:1] if right else []
    
    # === CORRECCIÓN DE BUG (UP) ===
    if not up:
        up = down[:1] if down else (right[:1] if right else [])

    if idle_right is None and right: idle_right = right[0]
    if idle_left  is None and idle_right is not None: idle_left = pygame.transform.flip(idle_right, True, False)
    if idle_down  is None and down:  idle_down = down[0]
    if idle_up    is None and up:    idle_up   = up[0]

    def _scale(f: pygame.Surface) -> pygame.Surface:
        if f.get_height() == 0: return pygame.Surface((int(target_h*0.7), target_h), pygame.SRCALPHA)
        h = target_h
        w = int(f.get_width() * (h / f.get_height()))
        return pygame.transform.smoothscale(f, (w, h))

    def _scale_list(seq: list[pygame.Surface]) -> list[pygame.Surface]:
        return [_scale(f) for f in seq]

    def _normalize(seq: list[pygame.Surface]) -> list[pygame.Surface]:
        if not seq: return seq
        max_w = max(f.get_width() for f in seq)
        H = seq[0].get_height()
        out = []
        for f in seq:
            canvas = pygame.Surface((max_w, H), pygame.SRCALPHA)
            rect = f.get_rect(midbottom=(max_w//2, H))
            canvas.blit(f, rect)
            out.append(canvas)
        return out

    def _normalize_single(s: pygame.Surface | None) -> pygame.Surface | None:
        if s is None:
             h = target_h
             w = int(h * 0.7)
             return pygame.Surface((w, h), pygame.SRCALPHA)
        S = _scale(s)
        canvas = pygame.Surface((S.get_width(), S.get_height()), pygame.SRCALPHA)
        rect = S.get_rect(midbottom=(canvas.get_width()//2, canvas.get_height()))
        canvas.blit(S, rect)
        return canvas

    right = _normalize(_scale_list(right))
    left  = _normalize(_scale_list(left))
    down  = _normalize(_scale_list(down))
    up    = _normalize(_scale_list(up))

    idle_right = _normalize_single(idle_right)
    idle_left  = _normalize_single(idle_left)
    idle_down  = _normalize_single(idle_down)
    idle_up    = _normalize_single(idle_up)

    return {
        "right": right, "left": left, "down": down, "up": up,
        "idle_right": idle_right, "idle_left": idle_left,
        "idle_down": idle_down, "idle_up": idle_up
    }

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
        start_img = idle if isinstance(idle, pygame.Surface) else (self.frames["down"][0] if self.frames.get("down") else pygame.Surface((40,60), pygame.SRCALPHA))
        self.image = start_img # type: ignore[assignment]
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
            
            # === LÓGICA DE MOVIMIENTO INVERTIDA (DE TU NIVEL 1) ===
            if abs(dx) >= abs(dy): 
                self.dir = "left" if dx > 0 else "right"
            else: 
                self.dir = "down" if dy > 0 else "up"
            # ======================================================
            
            self.rect.x += int(dx * self.speed * dt)
            self.rect.y += int(dy * self.speed * dt)
            self.rect.clamp_ip(self.bounds)
            self.anim_timer += dt
            if self.anim_timer >= self.anim_dt:
                self.anim_timer -= self.anim_dt
                seq: list[pygame.Surface] = self.frames.get(self.dir, []) # type: ignore[assignment]
                if seq: self.frame_idx = (self.frame_idx + 1) % len(seq)
            seq: list[pygame.Surface] = self.frames.get(self.dir, []) # type: ignore[assignment]
            if seq: self.image = seq[self.frame_idx % len(seq)]
        else:
            idle_key = f"idle_{self.dir}"
            idle_img = self.frames.get(idle_key)
            if isinstance(idle_img, pygame.Surface): self.image = idle_img
            else:
                seq: list[pygame.Surface] = self.frames.get(self.dir, []) # type: ignore[assignment]
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
# === FIN: CÓDIGO COPIADO DE NIVEL 1 ===


class Seed:
    def __init__(self, pos: Tuple[int,int], img: pygame.Surface):
        self.image = img
        self.rect = img.get_rect(center=pos)
        self.taken = False
    def draw(self, surf: pygame.Surface):
        if not self.taken: surf.blit(self.image, self.rect)

class Hole:
    def __init__(self, pos: Tuple[int,int], img: pygame.Surface):
        self.base_img = img
        self.rect = img.get_rect(center=pos)
        self.has_tree = False
        self.grow_timer = 0
        self.grow_step = 0
    def start_grow(self): self.grow_step, self.grow_timer = 1, 1
    def update(self, dt: int, assets_dir: Path):
        if self.grow_timer > 0 and not self.has_tree:
            self.grow_timer += dt
            if self.grow_timer >= GROW_TIME_PER_STEP:
                self.grow_timer = 1
                self.grow_step += 1
                if self.grow_step >= GROW_STEPS:
                    self.grow_step = GROW_STEPS 
                    self.has_tree = True
                    play_sfx("sfx_grow", assets_dir) # Asume que tienes un sfx_grow
    
    # === ¡CORRECCIÓN DE INDENTACIÓN! ===
    # 'def draw' debe estar al mismo nivel que 'def update', no dentro de él.
    def draw(self, surf: pygame.Surface, arbol_img: pygame.Surface, semilla_img: pygame.Surface):
        # === ¡CAMBIO AQUÍ! ===
        # Solo dibuja el hoyo (self.base_img) si el árbol NO está completo
        if not self.has_tree:
            surf.blit(self.base_img, self.rect)
        # ======================
        
        cx, cy = self.rect.center
        offset_y = int(self.rect.height * 0.43) 
        tree_midbottom_y = cy + offset_y 

        if not self.has_tree and self.grow_timer > 0:
            if self.grow_step == 1:
                surf.blit(semilla_img, semilla_img.get_rect(center=(cx, tree_midbottom_y - 6))) 
            elif self.grow_step == 2:
                small = pygame.transform.smoothscale(arbol_img, (int(arbol_img.get_width()*0.45), int(arbol_img.get_height()*0.45)))
                surf.blit(small, small.get_rect(midbottom=(cx, tree_midbottom_y)))
            else:
                medium = pygame.transform.smoothscale(arbol_img, (int(arbol_img.get_width()*0.8), int(arbol_img.get_height()*0.8)))
                surf.blit(medium, medium.get_rect(midbottom=(cx, tree_midbottom_y)))
        elif self.has_tree:
            surf.blit(arbol_img, arbol_img.get_rect(midbottom=(cx, tree_midbottom_y)))

def random_point_in_rect(r: pygame.Rect) -> Tuple[int,int]:
    return (random.randint(r.left+8, r.right-8), random.randint(r.top+8, r.bottom-8))

def non_overlapping_spawn(rects_to_avoid: List[pygame.Rect], areas: List[pygame.Rect], count: int) -> List[Tuple[int,int]]:
    pts: List[Tuple[int,int]] = []
    tries = 0
    while len(pts) < count and tries < count*100:
        tries += 1
        area = random.choice(areas)
        p = random_point_in_rect(area)
        pr = pygame.Rect(0,0,36,36); pr.center = p
        if any(pr.colliderect(r.inflate(24,24)) for r in rects_to_avoid): continue
        if any(pr.colliderect(pygame.Rect(x-18,y-18,36,36)) for (x,y) in pts): continue
        pts.append(p)
    return pts

# ==================================================================
# === ¡AQUÍ COMIENZA LA NUEVA FUNCIÓN 'RUN' QUE LO CONTIENE TODO! ===
# ==================================================================

def run(screen: pygame.Surface, assets_dir: Path, personaje: str = "EcoGuardian", dificultad: str = "Fácil"):
    
    # --- 1. Inicialización (lógica del __init__) ---
    pygame.font.init()
    clock = pygame.time.Clock()
    W, H = screen.get_size()

    # Cargar fuentes
    font = pygame.font.SysFont("arial", 26, bold=True)
    big_font = pygame.font.SysFont("arial", 54, bold=True)
    timer_font = pygame.font.SysFont("arial", 42, bold=True)

    # --- NUEVAS FUENTES/ASSETS PARA ICONO Y MENSAJES ---
    popup_font = pygame.font.SysFont("arial", 28, bold=True)
    small_font = pygame.font.SysFont("arial", 20, bold=True)

    # Cargar imágenes
    try:
        # === LÓGICA DE CARGA MÁS SEGURA (copiada de Nivel 1) ===
        img_fondo_surf = load_image(assets_dir, ASSET_STEMS["fondo"])
        if img_fondo_surf is None: raise FileNotFoundError(f"No se encontró fondo: {ASSET_STEMS['fondo']}")
        img_hoyo_surf = load_image(assets_dir, ASSET_STEMS["hoyo"])
        if img_hoyo_surf is None: raise FileNotFoundError(f"No se encontró hoyo: {ASSET_STEMS['hoyo']}")
        img_semilla_surf = load_image(assets_dir, ASSET_STEMS["semilla"])
        if img_semilla_surf is None: raise FileNotFoundError(f"No se encontró semilla: {ASSET_STEMS['semilla']}")
        img_arbol_surf = load_image(assets_dir, ASSET_STEMS["arbol"])
        if img_arbol_surf is None: raise FileNotFoundError(f"No se encontró arbol: {ASSET_STEMS['arbol']}")
        img_victoria_surf = load_image(assets_dir, ASSET_STEMS["victoria"])
        if img_victoria_surf is None: raise FileNotFoundError(f"No se encontró victoria: {ASSET_STEMS['victoria']}")
        timer_panel_img = load_image(assets_dir, ASSET_STEMS["timer_panel"]) # Este es opcional
    except Exception as e:
        print(f"Error fatal cargando imágenes del Nivel 2: {e}")
        stop_level_music()
        return # Salir si faltan assets
        
    # Escalar imágenes
    img_fondo = pygame.transform.scale(img_fondo_surf, screen.get_size())
    img_victoria = pygame.transform.scale(img_victoria_surf, screen.get_size())
    img_hoyo = scale_to_width(img_hoyo_surf, 66)
    img_semilla = scale_to_width(img_semilla_surf, 44)
    img_arbol = scale_to_width(img_arbol_surf, 180)

    # Crear Jugador
    target_h = max(40, int(H * 0.14)) # Usamos el tamaño 0.14
    # === ¡AQUÍ ESTÁ LA CORRECCIÓN! ===
    # Pasa la variable 'personaje' (que puede ser "PERSONAJE M") a la función.
    frames = load_char_frames(assets_dir, target_h=target_h, char_folder=personaje)
    player = Player(frames, (120, 490), screen.get_rect(), speed=320, anim_fps=8.0) # Stats Fácil

    # === Generar Hoyos y Semillas Aleatoriamente ===
    hole_pts = non_overlapping_spawn([], SAFE_SPAWN_AREAS, HOLES_TO_SPAWN)
    holes: List[Hole] = [Hole(p, img_hoyo) for p in hole_pts]
    avoid_rects = [h.rect for h in holes]
    seed_pts = non_overlapping_spawn(avoid_rects, SAFE_SPAWN_AREAS, SEEDS_TO_SPAWN)
    seeds: List[Seed] = [Seed(p, img_semilla) for p in seed_pts]


    # Variables de estado del juego
    carrying_seed = False
    victory = False
    victory_timer = 0
    total_semillas_plantadas = 0
    total_hoyos = len(holes)

    # Variables de Timer y Pausa
    TOTAL_MS = 80_000
    remaining_ms = TOTAL_MS
    game_over = False
    game_over_timer_ms = 1200
    paused = False
    
    start_level_music(assets_dir)
    suspense_music_started = False
    
    # Assets del Menú de Pausa
    pause_assets_dir = assets_dir / "PAUSA"
    pausa_panel_img = load_image(pause_assets_dir, ["nivelA 2", "panel_pausa", "pausa_panel"])
    pause_button_assets = {
        "cont_base": None, "cont_hover": None,
        "restart_base": None, "restart_hover": None,
        "menu_base": None, "menu_hover": None,
    }
    
    # --- CARGAR ICONO "E" (fallback a dibujo si no existe) ---
    icon_e_img = load_image(assets_dir, ["tecla_e", "icon_e", "key_e", "teclaE"])
    icon_e_bg = None
    if icon_e_img:
        # escalar a tamaño razonable relativo a pantalla
        icon_w = max(28, int(W * 0.035))
        icon_e_img = pygame.transform.smoothscale(icon_e_img, (icon_w, icon_w))
        # crear un bg para centrar si queremos (no obligatorio)
        icon_e_bg = icon_e_img
    else:
        # Crear icono programático (fondo + letra)
        letter = popup_font.render("E", True, (255,255,255))
        icon_e_bg = pygame.Surface((letter.get_width()+16, letter.get_height()+12), pygame.SRCALPHA)
        pygame.draw.rect(icon_e_bg, (0,0,0,180), icon_e_bg.get_rect(), border_radius=8)
        icon_e_bg.blit(letter, letter.get_rect(center=icon_e_bg.get_rect().center))

    # Variables para mensajes temporales (Semilla recogida / Árbol plantado)
    show_message = ""
    message_timer = 0.0
    message_duration = 1.6  # segundos

    # --- 2. Funciones Anidadas (Helpers) ---

    def reset_level():
        """Reinicia el nivel a su estado inicial."""
        nonlocal seeds, holes, player, carrying_seed, victory, victory_timer
        nonlocal total_semillas_plantadas, remaining_ms, game_over, paused
        nonlocal suspense_music_started
        
        player.rect.center = (120, 490)
        player.carrying_image = None
        
        carrying_seed = False
        victory = False
        victory_timer = 0
        total_semillas_plantadas = 0
        remaining_ms = TOTAL_MS
        game_over = False
        paused = False
        suspense_music_started = False
        start_level_music(assets_dir)
        
        hole_pts = non_overlapping_spawn([], SAFE_SPAWN_AREAS, HOLES_TO_SPAWN)
        holes = [Hole(p, img_hoyo) for p in hole_pts]
        avoid_rects = [h.rect for h in holes]
        seed_pts = non_overlapping_spawn(avoid_rects, SAFE_SPAWN_AREAS, SEEDS_TO_SPAWN)
        seeds = [Seed(p, img_semilla) for p in seed_pts]


    def _try_interact():
        """Lógica para recoger o plantar semillas."""
        nonlocal carrying_seed, total_semillas_plantadas, show_message, message_timer
        if victory or game_over: return
        
        try:
            player_center = player.rect.center
            # 1. Intentar recoger una semilla
            if not carrying_seed:
                closest_seed: Optional[Seed] = None
                min_dist_sq = float('inf')
                for s in seeds:
                    if not s.taken and player.rect.colliderect(s.rect):
                        dist_sq = (player_center[0] - s.rect.centerx)**2 + (player_center[1] - s.rect.centery)**2
                        if dist_sq < min_dist_sq:
                            min_dist_sq = dist_sq; closest_seed = s
                if closest_seed:
                    closest_seed.taken = True
                    carrying_seed = True
                    player.carrying_image = img_semilla
                    play_sfx("sfx_pick_seed", assets_dir)
                    # mensaje
                    show_message = "Semilla recogida"
                    message_timer = message_duration
                    return
            
            # 2. Intentar plantar una semilla
            if carrying_seed:
                closest_hole: Optional[Hole] = None
                min_dist_sq = float('inf')
                for h in holes:
                    if not h.has_tree and h.grow_timer == 0 and player.rect.colliderect(h.rect.inflate(20,20)):
                        dist_sq = (player_center[0] - h.rect.centerx)**2 + (player_center[1] - h.rect.centery)**2
                        if dist_sq < min_dist_sq:
                            min_dist_sq = dist_sq; closest_hole = h
                if closest_hole:
                    carrying_seed = False
                    player.carrying_image = None
                    closest_hole.start_grow()
                    total_semillas_plantadas += 1
                    play_sfx("sfx_plant", assets_dir)
                    # mensaje
                    show_message = "Árbol plantado"
                    message_timer = message_duration
                    return
        except Exception as e:
            print(f"ADVERTENCIA: Interacción: {e}")

    # --- 3. Bucle Principal del Juego ---
    running = True
    while running:
        dt_ms = clock.tick(60)
        dt_sec = dt_ms / 1000.0
        
        mouse_click = False
        mouse_pos = pygame.mouse.get_pos()
        
        # actualizar temporizador de mensajes
        if message_timer > 0.0:
            message_timer = max(0.0, message_timer - dt_sec)
            if message_timer == 0.0:
                show_message = ""

        # --- Manejo de Eventos ---
        events = pygame.event.get() # Obtener eventos UNA VEZ
        for ev in events:
            if ev.type == pygame.QUIT:
                stop_level_music()
                running = False
            
            if paused:
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1: 
                    mouse_click = True
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_SPACE:
                        paused = False
                        play_sfx("sfx_click", assets_dir)
                    if ev.key == pygame.K_ESCAPE:
                        stop_level_music()
                        running = False
            
            else: # Eventos si NO está en pausa
                if not game_over and not victory:
                    if ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_ESCAPE:
                            stop_level_music()
                            running = False
                        if ev.key == pygame.K_SPACE:
                            paused = True
                            play_sfx("sfx_click", assets_dir)
                        if ev.key == pygame.K_e or ev.key == pygame.K_RETURN:
                            _try_interact()

        # --- Lógica de Update ---
        if not paused and not game_over:
            if remaining_ms > 0:
                remaining_ms -= dt_ms
                remaining_ms = max(0, remaining_ms)

                if remaining_ms <= 30000 and not suspense_music_started:
                    start_suspense_music(assets_dir)
                    suspense_music_started = True
                
                if not victory:
                    player.handle_input(dt_sec)
                for h in holes: h.update(dt_ms, assets_dir)
                
                all_grown = total_semillas_plantadas >= total_hoyos
                if all_grown and not victory:
                    victory, victory_timer = True, 1800
                    play_sfx("sfx_grow", assets_dir)
                    
            else: # El tiempo se acabó
                if not victory:
                    game_over = True
                    game_over_timer_ms = 1200 # Iniciar contador de salida
        
        if victory and not paused:
            victory_timer -= dt_ms
            if victory_timer <= 0:
                stop_level_music()
                running = False
        
        if game_over and not paused: # Contar solo si no está en pausa
            game_over_timer_ms -= dt_ms
            if game_over_timer_ms <= 0:
                stop_level_music()
                running = False

        # --- Lógica de Dibujado ---
        if victory:
            screen.blit(img_victoria, (0, 0))
        else:
            screen.blit(img_fondo, (0,0))

            # Dibujar semillas y mostrar icono E + texto si el jugador está cerca
            for s in seeds:
                s.draw(screen)
                if not s.taken:
                    # detectar proximidad (pequeña ampliación para comodidad)
                    if player.rect.colliderect(s.rect.inflate(18, 18)):
                        # dibujar icono E encima de la semilla
                        icon_pos = (s.rect.centerx, s.rect.top - int(H * 0.035))
                        ib = icon_e_bg.copy()
                        # pulso sutil en alpha para llamar la atención
                        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180.0)
                        try:
                            ib.set_alpha(int(220 * (0.6 + 0.4 * pulse)))
                        except Exception:
                            pass
                        recti = ib.get_rect(center=icon_pos)
                        screen.blit(ib, recti)
                        # texto "Recoger semilla (E)" justo abajo del icono
                        recog = small_font.render("Recoger semilla (E)", True, (255, 255, 255))
                        recog_bg = pygame.Surface((recog.get_width() + 10, recog.get_height() + 6), pygame.SRCALPHA)
                        pygame.draw.rect(recog_bg, (0,0,0,160), recog_bg.get_rect(), border_radius=6)
                        recog_bg.blit(recog, recog.get_rect(center=recog_bg.get_rect().center))
                        rrect = recog_bg.get_rect(midtop=(recti.centerx, recti.bottom + 4))
                        screen.blit(recog_bg, rrect)

            # Dibujar hoyos y mostrar icono E + texto si el jugador tiene semilla
            for h in holes:
                h.draw(screen, img_arbol, img_semilla)
                if not h.has_tree and carrying_seed and player.rect.colliderect(h.rect.inflate(20,20)):
                    icon_pos = (h.rect.centerx, h.rect.top - int(H * 0.035))
                    ib = icon_e_bg.copy()
                    pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180.0)
                    try:
                        ib.set_alpha(int(220 * (0.6 + 0.4 * pulse)))
                    except Exception:
                        pass
                    recti = ib.get_rect(center=icon_pos)
                    screen.blit(ib, recti)
                    recog = small_font.render("Plantar semilla (E)", True, (255, 255, 255))
                    recog_bg = pygame.Surface((recog.get_width() + 10, recog.get_height() + 6), pygame.SRCALPHA)
                    pygame.draw.rect(recog_bg, (0,0,0,160), recog_bg.get_rect(), border_radius=6)
                    recog_bg.blit(recog, recog.get_rect(center=recog_bg.get_rect().center))
                    rrect = recog_bg.get_rect(midtop=(recti.centerx, recti.bottom + 4))
                    screen.blit(recog_bg, rrect)

            # Dibujar jugador (incluye si lleva semilla)
            player.draw(screen)
            
            # HUD
            hud = [
                "Nivel 2 – La Calle (Fácil, con tiempo)",
                "Mover: WASD/Flechas | Recoger/Plantar: E / Enter | Pausa: Espacio",
                f"Plantadas: {total_semillas_plantadas} / {total_hoyos}",
            ]
            for i, line in enumerate(hud):
                shadow = font.render(line, True, (15, 15, 15))
                screen.blit(shadow, (16 + 2, 25 + 2 + i * 26))
                text = font.render(line, True, (255, 255, 255))
                screen.blit(text, (16, 25 + i * 26))

        # Dibujar Timer
        mm = remaining_ms // 1000 // 60
        ss = (remaining_ms // 1000) % 60
        time_str = f"{mm}:{ss:02d}"
        margin = int(W * 0.04)
        panel_w, panel_h = int(W * 0.18), int(H * 0.11)
        panel_rect = pygame.Rect(W - margin - panel_w, margin, panel_w, panel_h)

        if timer_panel_img:
            scaled = pygame.transform.smoothscale(timer_panel_img, (panel_rect.w, panel_rect.h))
            screen.blit(scaled, panel_rect.topleft)
        else:
            pygame.draw.rect(screen, (30, 20, 15), panel_rect, border_radius=10)
            inner = panel_rect.inflate(-10, -10)
            pygame.draw.rect(screen, (210, 180, 140), inner, border_radius=8)

        txt = timer_font.render(time_str, True, (20, 15, 10))
        sh  = timer_font.render(time_str, True, (0, 0, 0))
        cx = panel_rect.centerx - int(panel_rect.w * 0.12)
        cy = panel_rect.centery
        screen.blit(sh,  sh.get_rect(center=(cx + 2, cy + 2)))
        screen.blit(txt, txt.get_rect(center=(cx, cy)))

        # Mensaje temporal central (Semilla recogida / Árbol plantado)
        if show_message and message_timer > 0.0:
            # alpha basado en tiempo restante (fade out)
            a = int(255 * (message_timer / message_duration))
            msg_surf = popup_font.render(show_message, True, (255, 255, 255))
            bg = pygame.Surface((msg_surf.get_width() + 20, msg_surf.get_height() + 12), pygame.SRCALPHA)
            pygame.draw.rect(bg, (0, 0, 0, 200), bg.get_rect(), border_radius=10)
            bg.blit(msg_surf, msg_surf.get_rect(center=bg.get_rect().center))
            bg.set_alpha(a)
            screen.blit(bg, bg.get_rect(midtop=(W//2, int(H * 0.06))))

        if game_over:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            msg = big_font.render("¡Tiempo agotado!", True, (255, 255, 255))
            screen.blit(msg, msg.get_rect(center=(W // 2, H // 2 - 10)))

        if paused:
            if not game_over:
                overlay = pygame.Surface((W, H), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 160))
                screen.blit(overlay, (0, 0))
            
            panel_w2, panel_h2 = int(W * 0.52), int(H * 0.52)
            panel2 = pygame.Rect(W//2 - panel_w2//2, H//2 - panel_h2//2, panel_w2, panel_h2)
            
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
                return hov and mouse_click # Click debe ser detectado en el bucle de eventos

            if draw_btn(r_cont, pause_button_assets["cont_hover"]):
                play_sfx("sfx_click", assets_dir)
                paused = False
            elif draw_btn(r_restart, pause_button_assets["restart_hover"]):
                play_sfx("sfx_click", assets_dir)
                reset_level()
                paused = False
            elif draw_btn(r_menu, pause_button_assets["menu_hover"]):
                play_sfx("sfx_click", assets_dir)
                stop_level_music()
                running = False

        pygame.display.flip()
            
    stop_level_music()
    return {
        "estado": "victoria" if victory else ("tiempo_agotado" if game_over else "menu"),
        "plantadas": total_semillas_plantadas
    }
