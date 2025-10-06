# nivel1_facil.py
import pygame
from pathlib import Path
from typing import Optional
import math, random

# ---------- helpers ----------
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

def find_many_by_prefix(assets_dir: Path, prefix: str) -> list[Path]:
    exts = (".png", ".jpg", ".jpeg")
    out: list[Path] = []
    for ext in exts:
        out += sorted(assets_dir.glob(f"{prefix}*{ext}"))
    return out

def load_surface(p: Path) -> pygame.Surface:
    img = pygame.image.load(str(p))
    return img.convert_alpha() if p.suffix.lower() == ".png" else img.convert()

def load_bg(assets_dir: Path) -> pygame.Surface:
    for s in ["nivel1_parque", "parque_nivel1", "park_level1", "nivel1", "bg_parque", "nivel1_bg"]:
        p = find_by_stem(assets_dir, s)
        if p:
            return load_surface(p)
    raise FileNotFoundError("No encontré la imagen del parque para Nivel 1.")

def load_char_frames(assets_dir: Path) -> dict[str, list[pygame.Surface]]:
    frames_right = [load_surface(p) for p in find_many_by_prefix(assets_dir, "ecoguardian_walk_right")]
    frames_left  = [load_surface(p) for p in find_many_by_prefix(assets_dir, "ecoguardian_walk_left")]

    if not frames_right and not frames_left:
        one = None
        for s in ["ecoguardian_idle", "ecoguardian", "EcoGuardian", "eco_guardian", "guardian", "player", "personaje"]:
            p = find_by_stem(assets_dir, s)
            if p:
                one = load_surface(p)
                break
        if not one:
            raise FileNotFoundError("No encontré sprite del personaje (ecoguardian*/guardian/player/personaje).")
        return {"right": [one], "left": [pygame.transform.flip(one, True, False)]}

    if frames_right and not frames_left:
        frames_left = [pygame.transform.flip(f, True, False) for f in frames_right]
    if frames_left and not frames_right:
        frames_right = [pygame.transform.flip(f, True, False) for f in frames_left]
    return {"right": frames_right, "left": frames_left}

def load_char_thumb(assets_dir: Path) -> Optional[pygame.Surface]:
    for stem in ["ecoguardian_idle", "ecoguardian", "EcoGuardian", "eco_guardian", "guardian"]:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = load_surface(p)
            return img.convert_alpha() if img.get_alpha() is not None else img.convert()
    return None

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height() * r)))

def make_glow(radius: int) -> pygame.Surface:
    surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        alpha = max(5, int(180 * (r / radius) ** 2))
        pygame.draw.circle(surf, (255, 255, 120, alpha), (radius, radius), r)
    return surf

def load_trash_images(assets_dir: Path) -> list[pygame.Surface]:
    imgs: list[pygame.Surface] = []
    for p in find_many_by_prefix(assets_dir, "trash_"):
        s = load_surface(p)
        imgs.append(s.convert_alpha() if p.suffix.lower() == ".png" else s)
    return imgs

def generate_random_points(W: int, H: int, count: int, min_dist: int,
                           x_range=(0.15, 0.85), y_range=(0.45, 0.88)) -> list[tuple[int,int]]:
    """
    Genera 'count' puntos aleatorios separados al menos 'min_dist' pixeles entre sí.
    Si tras varios intentos no se logra, completa con lo que haya.
    """
    pts: list[tuple[int,int]] = []
    max_attempts = count * 40  # margen amplio
    attempts = 0
    xmin, xmax = int(W * x_range[0]), int(W * x_range[1])
    ymin, ymax = int(H * y_range[0]), int(H * y_range[1])

    while len(pts) < count and attempts < max_attempts:
        attempts += 1
        x = random.randint(xmin, xmax)
        y = random.randint(ymin, ymax)
        ok = True
        for (px, py) in pts:
            if math.hypot(x - px, y - py) < min_dist:
                ok = False
                break
        if ok:
            pts.append((x, y))

    # Si faltan, rellena sin checar distancia para garantizar cantidad
    while len(pts) < count:
        pts.append((random.randint(xmin, xmax), random.randint(ymin, ymax)))
    return pts

# ---------- entidades ----------
class Player(pygame.sprite.Sprite):
    def __init__(self, frames: dict[str, list[pygame.Surface]], pos: tuple[int, int], speed: float, bounds: pygame.Rect):
        super().__init__()
        self.frames = frames
        self.dir = "right"
        self.frame_idx = 0
        self.anim_timer = 0.0
        self.anim_speed = 0.12
        target_h = int(bounds.height * 0.16)
        self.frames["right"] = [pygame.transform.smoothscale(f, (int(f.get_width() * (target_h/f.get_height())), target_h)) for f in self.frames["right"]]
        self.frames["left"]  = [pygame.transform.smoothscale(f, (int(f.get_width() * (target_h/f.get_height())), target_h)) for f in self.frames["left"]]
        self.image = self.frames[self.dir][0]
        self.rect = self.image.get_rect(center=pos)
        self.speed = speed
        self.bounds = bounds

    def handle_input(self, dt: float):
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1

        moving = (dx != 0 or dy != 0)
        if moving:
            if dx > 0: self.dir = "right"
            elif dx < 0: self.dir = "left"
            l = math.hypot(dx, dy)
            dx, dy = dx / l, dy / l
            self.rect.x += int(dx * self.speed * dt)
            self.rect.y += int(dy * self.speed * dt)
            self.rect.clamp_ip(self.bounds)
            self.anim_timer += dt
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0.0
                self.frame_idx = (self.frame_idx + 1) % len(self.frames[self.dir])
        else:
            self.frame_idx = 0
        self.image = self.frames[self.dir][self.frame_idx]

class Trash(pygame.sprite.Sprite):
    def __init__(self, img: pygame.Surface, pos: tuple[int,int], scale_w: int):
        super().__init__()
        self.image = scale_to_width(img, scale_w)
        self.rect = self.image.get_rect(center=pos)
        self.glow_base = make_glow(int(max(self.rect.width, self.rect.height) * 0.9))
        self.phase = random.uniform(0, math.tau)

    def draw_with_glow(self, surface: pygame.Surface, t: float):
        pul = (math.sin(t + self.phase) + 1) * 0.5
        alpha = int(80 + 90 * pul)
        glow = self.glow_base.copy()
        glow.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        grect = glow.get_rect(center=self.rect.center)
        surface.blit(glow, grect)
        surface.blit(self.image, self.rect)

# ---------- loop principal del nivel ----------
def run(screen: pygame.Surface, assets_dir: Path, personaje: str = "EcoGuardian", dificultad: str = "Fácil"):
    """
    Nivel 1 – Modo Fácil (sin límite de tiempo)
    Controles: WASD/Flechas (mover), E/Enter (recoger), Espacio (pausa)
    Retorna {"estado":"completado","recolectadas":N} o None si se sale.
    """
    pygame.font.init()
    clock = pygame.time.Clock()
    W, H = screen.get_size()

    # Fondo
    background = pygame.transform.smoothscale(load_bg(assets_dir), (W, H))

    # Botón back
    back_p = find_by_stem(assets_dir, "btn_back") or find_by_stem(assets_dir, "back")
    if not back_p:
        raise FileNotFoundError("Falta btn_back*.png")
    back_img = load_surface(back_p).convert_alpha()
    dw = max(120, min(int(W * 0.12), 240))
    ratio = dw / back_img.get_width()
    back_img = pygame.transform.smoothscale(back_img, (dw, int(back_img.get_height() * ratio)))
    back_rect = back_img.get_rect()
    back_rect.bottomleft = (10, H - 12)

    # Jugador
    frames = load_char_frames(assets_dir)
    player = Player(frames, pos=(int(W*0.12), int(H*0.75)), speed=320, bounds=pygame.Rect(0,0,W,H))

    # Basura (prefijo trash_)
    trash_imgs = load_trash_images(assets_dir)
    if not trash_imgs:
        for color in [(170,170,170), (70,160,70), (60,130,200)]:
            s = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.rect(s, color, (4,4,32,32), border_radius=6)
            trash_imgs.append(s)

    target_w = max(42, int(W * 0.035))

    # ---- SPawns aleatorios con distancia mínima ----
    trash_count   = 6                    # cuántas basuras aparecerán
    min_distance  = int(W * 0.08)        # separación mínima entre basuras (~8% ancho)
    spawn_points  = generate_random_points(W, H, trash_count, min_distance,
                                           x_range=(0.15, 0.85), y_range=(0.45, 0.88))

    trash_group = pygame.sprite.Group()
    for i, pos in enumerate(spawn_points):
        img  = trash_imgs[i % len(trash_imgs)]
        item = pygame.transform.rotate(img, random.randint(-12, 12))
        trash_group.add(Trash(item, pos, target_w))

    # HUD
    font = pygame.font.SysFont("arial", 26, bold=True)
    big  = pygame.font.SysFont("arial", 54, bold=True)

    # Retrato HUD opcional
    char_thumb = load_char_thumb(assets_dir)
    if char_thumb:
        target_h = 48
        scale = target_h / char_thumb.get_height()
        char_thumb = pygame.transform.smoothscale(char_thumb, (int(char_thumb.get_width()*scale), target_h))
        char_thumb_rect = char_thumb.get_rect(topleft=(10, 54))

    paused = False
    PICK_KEYS = (pygame.K_e, pygame.K_RETURN)
    INTERACT_DIST = int(W * 0.055)

    t = 0.0
    while True:
        dt = clock.tick(60) / 1000.0
        t += dt
        interact_now = False

        for e in pygame.event.get():
            if e.type == pygame.QUIT: return None
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:  paused = not paused
                if e.key in PICK_KEYS:       interact_now = True
                if e.key == pygame.K_ESCAPE: return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if back_rect.collidepoint(e.pos): return None

        if not paused:
            player.handle_input(dt)

            # recoger (una) basura cercana
            if interact_now:
                to_remove = None
                for tr in trash_group:
                    if abs(player.rect.centerx - tr.rect.centerx) <= INTERACT_DIST and \
                       abs(player.rect.centery - tr.rect.centery) <= INTERACT_DIST:
                        to_remove = tr
                        break
                if to_remove:
                    trash_group.remove(to_remove)

        # ----------- DIBUJO -----------
        screen.blit(background, (0, 0))
        for tr in trash_group:
            tr.draw_with_glow(screen, t)
        screen.blit(player.image, player.rect)

        ui_lines = [
            "Nivel 1 – El Parque (Fácil, sin tiempo)",
            "Mover: WASD/Flechas | Interactuar: E / Enter | Pausa: Espacio",
            f"Basuras restantes: {len(trash_group)}",
        ]
        for i, line in enumerate(ui_lines):
            screen.blit(font.render(line, True, (15,15,15)), (16, 12 + i*26))

        if char_thumb:
            screen.blit(char_thumb, char_thumb_rect)

        if paused:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            screen.blit(overlay, (0, 0))
            ptxt = big.render("PAUSA", True, (255, 255, 255))
            screen.blit(ptxt, ptxt.get_rect(center=(W//2, H//2)))

        if not paused and len(trash_group) == 0:
            win = pygame.Surface((W, H), pygame.SRCALPHA)
            win.fill((0, 120, 0, 90))
            screen.blit(win, (0, 0))
            wtxt = big.render("¡Parque limpio!", True, (255,255,255))
            screen.blit(wtxt, wtxt.get_rect(center=(W//2, H//2 - 10)))
            pygame.display.flip()
            pygame.time.delay(1200)
            return {"estado": "completado", "recolectadas": trash_count}

        screen.blit(back_img, back_rect)
        pygame.display.flip()
