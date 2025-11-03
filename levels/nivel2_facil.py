from __future__ import annotations
import pygame, random, re, math
from pathlib import Path
from typing import Optional, List, Tuple

try:
    # Esta función espera (nombre_sfx, assets_dir)
    from audio_shared import play_sfx
except Exception:
    # Esta función 'falsa' aceptará cualquier argumento y no hará nada
    def play_sfx(*args, **kwargs): pass

# ---------- helpers assets ----------
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

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    """Escala una imagen a un nuevo ancho, manteniendo la proporción."""
    if img.get_width() == 0: return pygame.Surface((new_w, new_w), pygame.SRCALPHA)
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height() * r)))

ASSET_STEMS = {
    "fondo":   ["n2_fondo_calle"],
    "hoyo":    ["n2_hoyo"],
    "semilla": ["n2_semilla"],
    "arbol":   ["n2_arbol"],
    "victoria":["n2_victoria_calle_verde"],
}

# ---------- posiciones y reglas nivel ----------

# ***** Posiciones como las dejaste *****
HOLE_POSITIONS_DEFAULT = [
    (280, 360),   # Arriba-izquierda (Se queda igual)
    (760, 360),   # Arriba-centro 
    (1220, 360),  # Arriba-derecha (Se queda igual)
    (240, 640),   # Abajo-izquierda (Este se queda igual)
    (1365, 700)   # Abajo-derecha (Se queda igual)
]

# Áreas donde aparecen las semillas (césped superior y calle)
SEED_SPAWN_AREAS = [
    pygame.Rect(80, 380, 1200, 80), # Área superior (césped, Y: 380-460)
    pygame.Rect(80, 540, 1200, 140), # Área inferior (calle, Y: 540-680)
]

# ***** CAMBIO 2: Reducir el número de semillas *****
SEEDS_TO_SPAWN = 5 # Estaba en 6
GROW_STEPS = 3
GROW_TIME_PER_STEP = 220  # ms

# ---------- cargador de frames + Player (como en nivel 1) ----------
def load_char_frames(assets_dir: Path, target_h: int, *, char_folder: str = "PERSONAJE H") -> dict[str, list[pygame.Surface] | pygame.Surface]:
    char_dir = assets_dir / char_folder
    if not char_dir.exists():
        raise FileNotFoundError(f"No se encontró la carpeta 'assets/{char_folder}'")

    def _load_seq(prefix: str) -> list[pygame.Surface]:
        files: list[Path] = []
        for ext in (".png", ".jpg", ".jpeg"):
            files += list(char_dir.glob(f"{prefix}_[0-9]*{ext}"))
        def _num(p: Path) -> int:
            m = re.search(r"_(\d+)\.\w+$", p.name);  return int(m.group(1)) if m else 0
        files.sort(key=_num)
        seq: list[pygame.Surface] = []
        for p in files:
            img = pygame.image.load(str(p))
            seq.append(img.convert_alpha() if p.suffix.lower()==".png" else img.convert())
        return seq

    def _load_idle(name: str) -> Optional[pygame.Surface]:
        for ext in (".png", ".jpg", ".jpeg"):
            p = char_dir / f"{name}{ext}"
            if p.exists():
                img = pygame.image.load(str(p))
                return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
        return None

    right = _load_seq("ecoguardian_walk_right")
    left  = _load_seq("ecoguardian_walk_left")
    down  = _load_seq("ecoguardian_walk_down")
    up    = _load_seq("ecoguardian_walk_up")

    idle_right = _load_idle("ecoguardian_right_idle")
    idle_left  = _load_idle("ecoguardian_left_idle")
    idle_down  = _load_idle("ecoguardian_down_idle")
    idle_up    = _load_idle("ecoguardian_up_idle")

    if right and not left: left = [pygame.transform.flip(f, True, False) for f in right]
    if left and not right: right = [pygame.transform.flip(f, True, False) for f in left]
    if not down: down = right[:1] if right else []
    if not up:   up   = right[:1] if right else []

    if idle_right is None and right: idle_right = right[0]
    if idle_left  is None and idle_right is not None: idle_left = pygame.transform.flip(idle_right, True, False)
    if idle_down  is None and down:  idle_down = down[0]
    if idle_up    is None and up:    idle_up   = up[0]

    def _scale(f: pygame.Surface) -> pygame.Surface:
        h = target_h
        if f.get_height() == 0: return pygame.Surface((int(target_h*0.7), target_h), pygame.SRCALPHA)
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

    def _normalize_single(s: pygame.Surface) -> pygame.Surface:
        S = _scale(s)
        canvas = pygame.Surface((S.get_width(), S.get_height()), pygame.SRCALPHA)
        rect = S.get_rect(midbottom=(canvas.get_width()//2, canvas.get_height()))
        canvas.blit(S, rect)
        return canvas

    right = _normalize(_scale_list(right))
    left  = _normalize(_scale_list(left))
    down  = _normalize(_scale_list(down))
    up    = _normalize(_scale_list(up))

    if idle_right: idle_right = _normalize_single(idle_right)
    if idle_left:  idle_left  = _normalize_single(idle_left)
    if idle_down:  idle_down  = _normalize_single(idle_down)
    if idle_up:    idle_up    = _normalize_single(idle_up)

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
        self.image = start_img
        self.rect = self.image.get_rect(center=pos)
        self.speed = speed
        self.bounds = bounds
        
        self.carrying_image: Optional[pygame.Surface] = None # Imagen a dibujar en la mano

    def handle_input(self, dt: float):
        k = pygame.key.get_pressed()
        dx = (k[pygame.K_d] or k[pygame.K_RIGHT]) - (k[pygame.K_a] or k[pygame.K_LEFT])
        dy = (k[pygame.K_s] or k[pygame.K_DOWN])  - (k[pygame.K_w] or k[pygame.K_UP])
        moving = (dx != 0 or dy != 0)

        if moving:
            l = math.hypot(dx, dy);  dx, dy = dx / l, dy / l
            
            # Lógica de dirección (v1) que funciona para tus assets
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
                seq: list[pygame.Surface] = self.frames.get(self.dir, []) # type: ignore[assignment]
                if seq:
                    self.frame_idx = (self.frame_idx + 1) % len(seq)

            seq: list[pygame.Surface] = self.frames.get(self.dir, []) # type: ignore[assignment]
            if seq:
                self.image = seq[self.frame_idx % len(seq)]
        else:
            idle_key = f"idle_{self.dir}"
            idle_img = self.frames.get(idle_key)
            if isinstance(idle_img, pygame.Surface):
                self.image = idle_img
            else:
                seq: list[pygame.Surface] = self.frames.get(self.dir, []) # type: ignore[assignment]
                self.image = seq[0] if seq else self.image
            self.frame_idx = 0

        new_midbottom = self.rect.midbottom
        self.rect = self.image.get_rect(midbottom=new_midbottom)
        self.rect.clamp_ip(self.bounds)

    def _get_carry_anchor(self) -> tuple[int, int]:
        """Calcula dónde dibujar la semilla (anclaje en las manos)."""
        rect = self.rect
        cx, cy = rect.centerx, rect.centery
        cy = rect.centery + int(rect.height * 0.22)
        
        if self.dir == "left":
            cx -= int(rect.width * 0.12); cy += int(rect.height * 0.02)
        elif self.dir == "right":
            cx += int(rect.width * 0.12); cy += int(rect.height * 0.02)
        elif self.dir == "up":
            cy += int(rect.height * 0.06)
        else: # down
            cy += int(rect.height * 0.04)
        return cx, cy

    def draw(self, surf: pygame.Surface):
        surf.blit(self.image, self.rect)
        if self.carrying_image:
            cx, cy = self._get_carry_anchor()
            anchor_rect = self.carrying_image.get_rect(center=(cx, cy))
            surf.blit(self.carrying_image, anchor_rect)


# ---------- entidades del nivel ----------
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
                    play_sfx("sfx_grow", assets_dir)
    
    def draw(self, surf: pygame.Surface, highlight_surf: Optional[pygame.Surface],
             arbol_img: pygame.Surface, semilla_img: pygame.Surface):
        
        surf.blit(self.base_img, self.rect)
            
        cx, cy = self.rect.center
        
        # ***** CORRECCIÓN PARA ÁRBOL FLOTANTE (¡EL ÚLTIMO TOQUE!) *****
        # Aumentamos el offset de 40% a 43% para que baje ese "casi nada".
        offset_y = int(self.rect.height * 0.43) # <-- ¡CAMBIO AQUÍ! (Era 0.40)
        tree_midbottom_y = cy + offset_y 
        
        if not self.has_tree and self.grow_timer > 0:
            if self.grow_step == 1:
                # La semilla también la bajamos (usando el nuevo ancla) para que quede dentro
                surf.blit(semilla_img, semilla_img.get_rect(center=(cx, tree_midbottom_y - 6))) 
            elif self.grow_step == 2:
                small = pygame.transform.smoothscale(arbol_img, (int(arbol_img.get_width()*0.45), int(arbol_img.get_height()*0.45)))
                surf.blit(small, small.get_rect(midbottom=(cx, tree_midbottom_y)))
            else:
                medium = pygame.transform.smoothscale(arbol_img, (int(arbol_img.get_width()*0.8), int(arbol_img.get_height()*0.8)))
                surf.blit(medium, medium.get_rect(midbottom=(cx, tree_midbottom_y)))
        elif self.has_tree:
            surf.blit(arbol_img, arbol_img.get_rect(midbottom=(cx, tree_midbottom_y)))

# ---------- util ----------
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

# ---------- estado del nivel ----------
class Nivel2Facil:
    def __init__(self, screen: pygame.Surface, assets_dir: Path,
                 hole_positions: Optional[List[Tuple[int,int]]] = None,
                 *, char_folder: str = "PERSONAJE H"):
        
        self.screen = screen
        self.assets_dir = assets_dir # Guardamos esto para usarlo en el sonido

        self.img_fondo    = load_image(assets_dir, ASSET_STEMS["fondo"]);    assert self.img_fondo, "Falta n2_fondo_calle.*"
        self.img_hoyo     = load_image(assets_dir, ASSET_STEMS["hoyo"]);     assert self.img_hoyo, "Falta n2_hoyo.*"
        self.img_semilla  = load_image(assets_dir, ASSET_STEMS["semilla"]);  assert self.img_semilla, "Falta n2_semilla.*"
        self.img_arbol    = load_image(assets_dir, ASSET_STEMS["arbol"]);    assert self.img_arbol, "Falta n2_arbol.*"
        self.img_victoria = load_image(assets_dir, ASSET_STEMS["victoria"]); assert self.img_victoria, "Falta n2_ victoria_calle_verde.*"

        self.img_fondo = pygame.transform.scale(self.img_fondo, self.screen.get_size())
        
        # ***** CAMBIO 3: Escalar victoria a pantalla completa *****
        self.img_victoria = pygame.transform.scale(self.img_victoria, self.screen.get_size())


        HOLE_WIDTH = 66
        SEED_WIDTH = 44
        
        # ***** CAMBIO 1: Aumentar tamaño del árbol *****
        # Lo subí de 90 a 180 para que coincida con los árboles del fondo
        TREE_WIDTH = 180 # <--- ¡CAMBIO AQUÍ! 
        
        self.img_hoyo = scale_to_width(self.img_hoyo, HOLE_WIDTH)
        self.img_semilla = scale_to_width(self.img_semilla, SEED_WIDTH)
        # Escalar el árbol al nuevo ancho definido
        self.img_arbol = scale_to_width(self.img_arbol, TREE_WIDTH)

        target_h = max(40, int(self.screen.get_height() * 0.16))
        frames = load_char_frames(assets_dir, target_h=target_h, char_folder=char_folder)
        self.player = Player(frames, (120, 490), self.screen.get_rect(), speed=320, anim_fps=8.0)

        # Aquí se usan las nuevas posiciones
        pos_list = hole_positions if hole_positions else HOLE_POSITIONS_DEFAULT
        self.holes: List[Hole] = [Hole(p, self.img_hoyo) for p in pos_list]

        avoid = [h.rect for h in self.holes]
        seed_pts = non_overlapping_spawn(avoid, SEED_SPAWN_AREAS, SEEDS_TO_SPAWN)
        self.seeds: List[Seed] = [Seed(p, self.img_semilla) for p in seed_pts]

        self.carrying_seed = False
        self.victory = False
        self.victory_timer = 0

    def update(self, dt_ms: int) -> Optional[str]:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: return "quit"
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_SPACE: return "pause"
                if ev.key == pygame.K_e: self._try_interact()

        # No actualizar el player si ya ganamos
        if not self.victory:
            self.player.handle_input(dt_ms / 1000.0)
        
        for h in self.holes: h.update(dt_ms, self.assets_dir)

        all_grown = all(h.has_tree for h in self.holes)
        if all_grown and len(self.holes) > 0 and not self.victory:
            self.victory, self.victory_timer = True, 1800
            play_sfx("sfx_grow", self.assets_dir)
            
        if self.victory:
            self.victory_timer -= dt_ms
            if self.victory_timer <= 0:
                return "home"
        return None

    def _try_interact(self):
        # No permitir interacción si ya ganamos
        if self.victory: return
        
        try:
            # 1. Intentar recoger una semilla
            if not self.carrying_seed:
                player_center = self.player.rect.center
                closest_seed: Optional[Seed] = None
                min_dist_sq = float('inf')

                for s in self.seeds:
                    if not s.taken and self.player.rect.colliderect(s.rect):
                        dist_sq = (player_center[0] - s.rect.centerx)**2 + (player_center[1] - s.rect.centery)**2
                        if dist_sq < min_dist_sq:
                            min_dist_sq = dist_sq
                            closest_seed = s
                
                if closest_seed:
                    closest_seed.taken = True
                    self.carrying_seed = True
                    self.player.carrying_image = self.img_semilla
                    play_sfx("sfx_pick_seed", self.assets_dir)
                    return
            
            # 2. Intentar plantar una semilla
            if self.carrying_seed:
                player_center = self.player.rect.center
                closest_hole: Optional[Hole] = None
                min_dist_sq = float('inf')
                
                for h in self.holes:
                    if not h.has_tree and h.grow_timer == 0 and self.player.rect.colliderect(h.rect.inflate(20,20)):
                        dist_sq = (player_center[0] - h.rect.centerx)**2 + (player_center[1] - h.rect.centery)**2
                        if dist_sq < min_dist_sq:
                            min_dist_sq = dist_sq
                            closest_hole = h

                if closest_hole:
                    self.carrying_seed = False
                    self.player.carrying_image = None
                    closest_hole.start_grow()
                    play_sfx("sfx_plant", self.assets_dir)
                    return
        
        except Exception as e:
            print(f"ADVERTENCIA: Ocurrió un error durante la interacción: {e}")


    def draw(self):
        # ***** CAMBIO 3: Lógica de dibujado para victoria *****
        if self.victory:
            # Si se ganó, mostrar solo la imagen de victoria (ya escalada)
            self.screen.blit(self.img_victoria, (0, 0))
        else:
            # Dibujado normal del juego
            self.screen.blit(self.img_fondo, (0,0))
            for s in self.seeds: s.draw(self.screen)
            for h in self.holes: h.draw(self.screen, None, self.img_arbol, self.img_semilla)
            self.player.draw(self.screen)
            
            font = pygame.font.SysFont(None, 22)
            hint = font.render("Flechas/WASD: mover | E: recoger/plantar | Espacio: pausa", True, (240,240,240))
            self.screen.blit(hint, (16, self.screen.get_height()-28))
        
# --- demo opcional ---
def run_demo():
    pygame.init()
    pygame.font.init() # Asegurar que las fuentes estén listas
    screen = pygame.display.set_mode((1366, 768))
    clock = pygame.time.Clock()
    
    assets_dir = Path(".")
    if not (assets_dir / "assets").exists():
        assets_dir = Path("..")
        if not (assets_dir / "assets").exists():
            print("Error: No se encuentra la carpeta 'assets'")
            print("Asegúrate de que 'assets' esté junto a este script o en la carpeta superior.")
            return

    assets_path = assets_dir / "assets"
    
    try:
        level = Nivel2Facil(screen, assets_path, char_folder="PERSONAJE H")
    except Exception as e:
        print(f"Error al cargar el nivel. ¿Faltan assets o la carpeta del personaje?")
        print(f"Error: {e}")
        return
        
    running = True
    while running:
        dt = clock.tick(60)
        res = level.update(dt)
        if res in ("quit", "home"): running = False
        level.draw(); pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    run_demo()