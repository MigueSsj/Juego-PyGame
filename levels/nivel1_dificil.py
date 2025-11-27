from __future__ import annotations
import pygame, math, random, re
from pathlib import Path
from typing import Optional
import config

# === Importar funciones de música (si existen) ===
try:
    from audio_shared import start_level_music, start_suspense_music, stop_level_music
except ImportError:
    print("WARN: No se pudo importar audio_shared. La música no funcionará.")
    def start_level_music(assets_dir: Path): pass
    def start_suspense_music(assets_dir: Path): pass
    def stop_level_music(): pass


# ====== SFX click (VOLÚMEN AJUSTABLE) ======
CLICK_VOL = 0.25
_click_snd: pygame.mixer.Sound | None = None

def play_click(assets_dir: Path):
    global _click_snd
    try:
        if _click_snd is None:
            audio_dir = assets_dir / "msuiquita"
            for stem in ["musica_botoncitos", "click", "boton"]:
                for ext in (".ogg", ".wav", ".mp3"):
                    for p in list(audio_dir.glob(f"{stem}{ext}")) + list(audio_dir.glob(f"{stem}*{ext}")):
                        if not pygame.mixer.get_init():
                            pygame.mixer.init()
                        _click_snd = pygame.mixer.Sound(str(p))
                        break
                if _click_snd:
                    break
        if _click_snd:
            _click_snd.set_volume(max(0.0, min(1.0, float(CLICK_VOL))))
            _click_snd.play()
    except Exception:
        pass

# ---------- Helpers ----------
def find_by_stem(folder: Path, stem: str) -> Optional[Path]:
    exts = (".png", ".jpg", ".jpeg")
    for ext in exts:
        p = folder / f"{stem}{ext}"
        if p.exists():
            return p
    cands = []
    for ext in exts:
        cands += list(folder.glob(f"{stem}*{ext}"))
    return min(cands, key=lambda p: len(p.name)) if cands else None

def find_many_by_prefix(folder: Path, prefix: str) -> list[Path]:
    exts = (".png", ".jpg", ".jpeg")
    out: list[Path] = []
    for ext in exts:
        out += sorted(folder.glob(f"{prefix}*{ext}"))
    return out

def load_surface(p: Path) -> pygame.Surface:
    img = pygame.image.load(str(p))
    return img.convert_alpha() if p.suffix.lower() == ".png" else img.convert()

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    r = new_w / img.get_width() if img.get_width() != 0 else 1.0
    return pygame.transform.smoothscale(img, (new_w, max(1, int(img.get_height() * r))))

def make_glow(radius: int) -> pygame.Surface:
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for rr in range(radius, 0, -1):
        a = max(5, int(180 * (rr / radius) ** 2))
        pygame.draw.circle(s, (255, 255, 120, a), (radius, radius), rr)
    return s

def load_bg_fit(assets_dir: Path, W: int, H: int) -> tuple[pygame.Surface, pygame.Rect]:
    candidates = ["nivel1_parque", "parque_nivel1", "park_level1", "nivel1", "bg_parque", "nivel1_bg"]
    p = None
    for stem in candidates:
        p = find_by_stem(assets_dir, stem)
        if p:
            break
    if p:
        img = load_surface(p)
    else:
        img = pygame.Surface((W, H))
        img.fill((40, 120, 40))
    iw, ih = img.get_size()
    ratio = min(W / iw, H / ih) if iw and ih else 1.0
    new_w, new_h = int(iw * ratio), int(ih * ratio)
    scaled = pygame.transform.smoothscale(img, (new_w, new_h))
    rect = scaled.get_rect(center=(W // 2, H // 2))
    return scaled, rect

def load_trash_images(assets_dir: Path) -> list[pygame.Surface]:
    imgs: list[pygame.Surface] = []
    for p in find_many_by_prefix(assets_dir, "trash_"):
        s = load_surface(p)
        imgs.append(s.convert_alpha() if p.suffix.lower() == ".png" else s)
    return imgs

def _carry_anchor(player: pygame.sprite.Sprite, carrying: pygame.sprite.Sprite) -> tuple[int, int]:
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

def load_char_frames(assets_dir: Path, target_h: int, *, char_folder: str = "PERSONAJE H") -> dict[str, list[pygame.Surface] | pygame.Surface]:
    char_dir = assets_dir / char_folder
    if not char_dir.exists():
        alt_folder = "PERSONAJE H" if "M" in char_folder else "PERSONAJE M"
        if (assets_dir / alt_folder).exists():
            print(f"WARN: Carpeta '{char_folder}' no encontrada. Usando '{alt_folder}'.")
            char_dir = assets_dir / alt_folder
        else:
            raise FileNotFoundError(f"No se encontró la carpeta 'assets/{char_folder}' ni una alternativa.")

    if "M" in char_folder.upper():
        prefix = "womanguardian"
    else:
        prefix = "ecoguardian"

    def _load_seq(name: str) -> list[pygame.Surface]:
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
        for ext in (".png", ".jpg", ".jpeg"):
            p = char_dir / f"{prefix}_{name}{ext}"
            if p.exists():
                img = pygame.image.load(str(p))
                return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
        return None

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
    if not up:   up   = right[:1] if right else []

    if idle_right is None and right: idle_right = right[0]
    if idle_left  is None and idle_right is not None: idle_left = pygame.transform.flip(idle_right, True, False)
    if idle_down  is None and down:  idle_down = down[0]
    if idle_up    is None and up:    idle_up   = up[0]

    def _scale(f: pygame.Surface) -> pygame.Surface:
        h = target_h
        w = int(f.get_width() * (h / f.get_height())) if f.get_height() != 0 else int(h * 0.7)
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

# ---------- Entidades ----------
class Player(pygame.sprite.Sprite):
    def __init__(self, frames: dict[str, list[pygame.Surface] | pygame.Surface], pos, bounds: pygame.Rect,
                 speed: float = 340, anim_fps: float = 9.0):
        super().__init__()
        self.frames = frames
        self.dir = "down"
        self.frame_idx = 0
        self.anim_timer = 0.0
        self.anim_dt = 1.0 / max(1.0, anim_fps)
        idle = self.frames.get("idle_down")
        start_img = idle if isinstance(idle, pygame.Surface) else (self.frames["down"][0] if self.frames["down"] else pygame.Surface((40,60), pygame.SRCALPHA))
        self.image = start_img 
        self.rect = self.image.get_rect(center=pos)
        self.speed = speed
        self.bounds = bounds

    def handle_input(self, dt: float):
        k = pygame.key.get_pressed()
        dx = (k[pygame.K_d] or k[pygame.K_RIGHT]) - (k[pygame.K_a] or k[pygame.K_LEFT])
        dy = (k[pygame.K_s] or k[pygame.K_DOWN])  - (k[pygame.K_w] or k[pygame.K_UP])

        moving = (dx != 0 or dy != 0)

        if moving:
            l = math.hypot(dx, dy)
            dx, dy = dx / l, dy / l

            # === LÓGICA INVERTIDA (HARD MODE) ===
            # dx > 0 -> Left, dx < 0 -> Right
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
                if seq:
                    self.frame_idx = (self.frame_idx + 1) % len(seq)

            seq: list[pygame.Surface] = self.frames.get(self.dir, []) 
            if seq:
                self.image = seq[self.frame_idx % len(seq)]

        else:
            idle_key = f"idle_{self.dir}"
            idle_img = self.frames.get(idle_key)
            if isinstance(idle_img, pygame.Surface):
                self.image = idle_img
            else:
                seq: list[pygame.Surface] = self.frames.get(self.dir, []) 
                self.image = seq[0] if seq else self.image
            self.frame_idx = 0

        new_midbottom = self.rect.midbottom
        self.rect = self.image.get_rect(midbottom=new_midbottom)
        self.rect.clamp_ip(self.bounds)

class Trash(pygame.sprite.Sprite):
    def __init__(self, img: pygame.Surface, pos, scale_w: int):
        super().__init__()
        self.image = scale_to_width(img, scale_w)
        self.rect = self.image.get_rect(center=pos)
        self.glow = make_glow(int(max(self.rect.width, self.rect.height) * 0.9))
        self.carried = False
        self.phase = random.uniform(0, math.tau)

    def draw(self, surface: pygame.Surface, t: float):
        if not self.carried:
            pul = (math.sin(t + self.phase) + 1) * 0.5
            a = int(70 + 100 * pul)
            g = self.glow.copy()
            g.fill((255, 255, 255, a), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(g, g.get_rect(center=self.rect.center))
        surface.blit(self.image, self.rect)


# ---------- NIVEL PRINCIPAL (DIFÍCIL) ----------
def run(screen: pygame.Surface, assets_dir: Path, personaje: str = "EcoGuardian", dificultad: str = "Difícil"):
    pygame.font.init()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 26, bold=True)
    big  = pygame.font.SysFont("arial", 54, bold=True)
    timer_font = pygame.font.SysFont("arial", 42, bold=True)

    W, H = screen.get_size()
    background, bg_rect = load_bg_fit(assets_dir, W, H)

    pixel_font_path = find_by_stem(assets_dir, "pixel") or find_by_stem(assets_dir, "press_start") or find_by_stem(assets_dir, "px")
    if pixel_font_path:
        try:
            pixel_font = pygame.font.Font(str(pixel_font_path), max(24, int(H * 0.09)))
        except Exception:
            pixel_font = pygame.font.SysFont("arial", max(32, int(H * 0.09)), bold=True)
    else:
        pixel_font = pygame.font.SysFont("arial", max(32, int(H * 0.09)), bold=True)

    # === Bote de basura (Más Grande) ===
    bin_p = (find_by_stem(assets_dir, "basurero")
             or find_by_stem(assets_dir, "bote_basura")
             or find_by_stem(assets_dir, "trash_bin"))
    
    BIN_SCALE = 0.24  
    if bin_p:
        bin_img = scale_to_width(load_surface(bin_p), int(W * BIN_SCALE))
    else:
        bin_img = pygame.Surface((int(W * 0.15), int(W * 0.20)), pygame.SRCALPHA)
        pygame.draw.rect(bin_img, (90, 90, 90), bin_img.get_rect(), border_radius=12)
        pygame.draw.rect(bin_img, (255, 255, 255), bin_img.get_rect(), 2, border_radius=12)
    
    bin_rect = bin_img.get_rect()
    # === Ajuste de posición (Más a la derecha) ===
    bin_rect.bottomright = (W - int(W * 0.015), H - int(W * 0.03))
    BIN_RADIUS = max(36, int(W * 0.05))

    # === Flecha indicadora ===
    arrow_img = None
    arrow_p = find_by_stem(assets_dir, "flecha") or find_by_stem(assets_dir, "arrow")
    if arrow_p:
         arrow_img = scale_to_width(load_surface(arrow_p), int(W * 0.06))
    else:
         arrow_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
         pygame.draw.polygon(arrow_surf, (0, 0, 0), [(10, 10), (50, 10), (30, 50)])
         pygame.draw.polygon(arrow_surf, (255, 220, 50), [(14, 14), (46, 14), (30, 44)])
         arrow_img = scale_to_width(arrow_surf, int(W * 0.06))

    # === Palomita ===
    palomita_img = None
    p = find_by_stem(assets_dir, "basurita_entregada")
    PALOMITA_DURATION = 1.2
    palomita_timer = 0.0
    if p:
        try:
            palomita_img = scale_to_width(load_surface(p), int(bin_rect.width * 0.55))
        except Exception:
            palomita_img = None

    # === Contador Visual (Mejora) ===
    contador_img = None
    contador_rect = None
    contador_path = find_by_stem(assets_dir, "contador_basura")
    if contador_path:
        try:
            contador_img = load_surface(contador_path)
            contador_img = scale_to_width(contador_img, int(W * 0.12))
            contador_rect = contador_img.get_rect()
            margin_top = int(H * 0.02)
            contador_rect.midtop = (W // 2, margin_top)
        except Exception:
            contador_img = None
            contador_rect = None

    # Basuras
    sprite_trash = load_trash_images(assets_dir)
    if not sprite_trash:
        for col in [(160, 160, 160), (70, 160, 70), (60, 130, 200)]:
            s = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.rect(s, col, (4, 4, 32, 32), border_radius=6)
            sprite_trash.append(s)
    trash_group = pygame.sprite.Group()
    total_trash = 12 # DIFICIL: 12 basuras
    for i in range(total_trash):
        x = random.randint(int(W * 0.16), int(W * 0.84))
        y = random.randint(int(H * 0.46), int(H * 0.86))
        img = sprite_trash[i % len(sprite_trash)]
        trash_group.add(Trash(img, (x, y), int(W * 0.032)))

    # Personaje (Rápido)
    frames = load_char_frames(assets_dir, target_h=int(H * 0.14), char_folder=personaje)
    player = Player(frames, (int(W * 0.16), int(H * 0.75)), pygame.Rect(0, 0, W, H), speed=340, anim_fps=9.0)

    carrying: Optional[Trash] = None
    delivered = 0

    PICK_KEYS = (pygame.K_e, pygame.K_RETURN)
    INTERACT_DIST = int(W * 0.05) # Más difícil interacción

    paused = False
    t = 0.0

    # Interactivos visuales
    popup_font = pygame.font.SysFont("arial", 28, bold=True)
    small_font = pygame.font.SysFont("arial", 20, bold=True)
    show_message = "" 
    message_timer = 0.0 
    message_duration = 1.5 

    icon_e_letter = popup_font.render("E", True, (255, 255, 255))
    icon_bg = pygame.Surface((icon_e_letter.get_width() + 18, icon_e_letter.get_height() + 12), pygame.SRCALPHA)
    pygame.draw.rect(icon_bg, (0, 0, 0, 180), icon_bg.get_rect(), border_radius=8)
    icon_bg.blit(icon_e_letter, icon_e_letter.get_rect(center=icon_bg.get_rect().center))

    check_font = pygame.font.SysFont("arial", 72, bold=True)
    check_surf_base = check_font.render("✓", True, (40, 180, 40))
    check_surf = check_surf_base.copy()
    check_timer = 0.0
    CHECK_DURATION = 1.0

    carry_label = small_font.render(config.obtener_nombre("txt_basura_mano"), True, (255, 255, 255))
    carry_label_bg = pygame.Surface((carry_label.get_width() + 12, carry_label.get_height() + 8), pygame.SRCALPHA)
    pygame.draw.rect(carry_label_bg, (0,0,0,160), carry_label_bg.get_rect(), border_radius=6)
    carry_label_bg.blit(carry_label, carry_label.get_rect(center=carry_label_bg.get_rect().center))

    # Temporizador (DIFICIL: 70s)
    TOTAL_MS = 70_000 
    remaining_ms = TOTAL_MS 

    start_level_music(assets_dir)

    timer_panel = None
    for nm in ["temporizador", "timer_panel", "panel_tiempo", "TEMPORAZIDOR"]:
        p = find_by_stem(assets_dir, nm)
        if p:
            timer_panel = load_surface(p)
            break

    pausa_dir = assets_dir / "PAUSA"
    pausa_panel_img = None
    for nm in ["nivelA 2", "panel_pausa", "pausa_panel"]:
        ptex = find_by_stem(pausa_dir, nm)
        if ptex:
            pausa_panel_img = load_surface(ptex)
            break
            
    pause_button_assets = {
        "cont_base": None, "cont_hover": None,
        "restart_base": None, "restart_hover": None,
        "menu_base": None, "menu_hover": None,
    }

    def reset_level():
        nonlocal trash_group, carrying, delivered, remaining_ms, message_timer, check_timer, palomita_timer
        nonlocal suspense_music_started
        trash_group.empty()
        for i in range(total_trash):
            x = random.randint(int(W * 0.16), int(W * 0.84))
            y = random.randint(int(H * 0.46), int(H * 0.86))
            img = sprite_trash[i % len(sprite_trash)]
            trash_group.add(Trash(img, (x, y), int(W * 0.032)))
        carrying = None
        delivered = 0
        remaining_ms = TOTAL_MS 
        suspense_music_started = False
        start_level_music(assets_dir)
        message_timer = 0.0
        check_timer = 0.0
        palomita_timer = 0.0

    suspense_music_started = False

    # Pantalla Lose
    pantalla_lose_img = None
    try:
        lose_folder = assets_dir / "PANTALLA LOSE"
        if lose_folder.exists():
            for stem in ["NIVEL 1P", "NIVEL1P", "NIVEL1 P", "NIVEL1P".lower(), "nivel 1p", "NIVEL1P"]:
                p = find_by_stem(lose_folder, stem)
                if p:
                    pantalla_lose_img = load_surface(p)
                    break
    except Exception:
        pantalla_lose_img = None

    while True:
        dt = min(clock.tick(60) / 1000.0, 0.033)
        t += dt
        interact = False

        if message_timer > 0.0:
            message_timer = max(0.0, message_timer - dt)
        if check_timer > 0.0:
            check_timer = max(0.0, check_timer - dt)
        if palomita_timer > 0.0:
            palomita_timer = max(0.0, palomita_timer - dt)

        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT:
                stop_level_music()
                return None
            if paused:
                pass
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    play_click(assets_dir)
                    stop_level_music()
                    return None
                if e.key == pygame.K_SPACE:
                    paused = not paused
                    play_click(assets_dir)
                if e.key in PICK_KEYS:
                    interact = True

        if not paused and remaining_ms > 0:
            remaining_ms -= int(dt * 1000)
            remaining_ms = max(0, remaining_ms)
            
            if remaining_ms <= 30000 and not suspense_music_started:
                start_suspense_music(assets_dir)
                suspense_music_started = True

            player.handle_input(dt)

            if carrying:
                carrying.carried = True
                ax, ay = _carry_anchor(player, carrying)
                carrying.rect.center = (ax, ay)

            if interact:
                if not carrying:
                    nearest = None
                    best = 1e9
                    for tr in trash_group:
                        d = math.hypot(player.rect.centerx - tr.rect.centerx,
                                       player.rect.centery - tr.rect.centery)
                        if d < best and d <= INTERACT_DIST:
                            best = d; nearest = tr
                    if nearest:
                        carrying = nearest
                        carrying.carried = True
                        show_message = config.obtener_nombre("txt_basura_recolectada")
                        message_timer = message_duration
                        play_click(assets_dir)
                else:
                    d = math.hypot(player.rect.centerx - bin_rect.centerx,
                                   player.rect.centery - bin_rect.centery)
                    if d <= BIN_RADIUS * 1.2:
                        try:
                            trash_group.remove(carrying)
                        except Exception:
                            pass
                        carrying = None
                        delivered += 1
                        check_timer = CHECK_DURATION
                        show_message = config.obtener_nombre("txt_basura_entregada")
                        message_timer = message_duration
                        palomita_timer = PALOMITA_DURATION
                        play_click(assets_dir)
            
        # DIBUJO
        screen.fill((34, 45, 38))
        screen.blit(background, bg_rect)

        screen.blit(bin_img, bin_rect)

        # === Flecha Animada (Solo si carrying) ===
        if arrow_img and carrying:
            bounce_offset = 15 * math.sin(t * 4.0)
            arrow_rect = arrow_img.get_rect(midbottom=(bin_rect.centerx, bin_rect.top - 10 + bounce_offset))
            screen.blit(arrow_img, arrow_rect)

        if palomita_img and palomita_timer > 0:
            alpha = int(255 * (palomita_timer / PALOMITA_DURATION))
            img = palomita_img.copy()
            img.set_alpha(alpha)
            pal_rect = img.get_rect(center=bin_rect.center)
            pal_rect.y -= int(bin_rect.height * 0.20)
            screen.blit(img, pal_rect)
        elif not palomita_img and check_timer > 0:
            a = int(255 * (check_timer / CHECK_DURATION))
            cs = check_surf.copy()
            cs.set_alpha(a)
            cs_rect = cs.get_rect(center=(bin_rect.centerx, bin_rect.top - int(H * 0.05)))
            screen.blit(cs, cs_rect)

        for tr in trash_group:
            tr.draw(screen, t)
        screen.blit(player.image, player.rect)
        if carrying:
            screen.blit(carrying.image, carrying.rect)

        # HUD
        hud_lines = [
            f"{config.obtener_nombre('txt_park_hud_title')} {config.obtener_nombre('txt_dificil_tiempo')}",
            config.obtener_nombre('txt_mover_accion_pausa'),
        ]
        for i, line in enumerate(hud_lines):
            shadow = font.render(line, True, (15, 15, 15))
            screen.blit(shadow, (16 + 2, 25 + 2 + i * 26))
            text = font.render(line, True, (255, 255, 255))
            screen.blit(text, (16, 25 + i * 26))

        if not carrying:
            nearest = None
            bestd = 1e9
            for tr in trash_group:
                d = math.hypot(player.rect.centerx - tr.rect.centerx,
                               player.rect.centery - tr.rect.centery)
                if d < bestd:
                    bestd = d; nearest = tr
            if nearest and bestd <= INTERACT_DIST:
                icon_pos = (nearest.rect.centerx, nearest.rect.top - int(H * 0.03))
                ib = icon_bg.copy()
                pulse = 0.5 + 0.5 * math.sin(t * 6.0)
                alpha = int(220 * (0.6 + 0.4 * pulse))
                ib.set_alpha(alpha)
                recti = ib.get_rect(center=icon_pos)
                screen.blit(ib, recti)
                recog = small_font.render(config.obtener_nombre("txt_recoger_e"), True, (255, 255, 255))
                recog_bg = pygame.Surface((recog.get_width() + 10, recog.get_height() + 6), pygame.SRCALPHA)
                pygame.draw.rect(recog_bg, (0,0,0,160), recog_bg.get_rect(), border_radius=6)
                recog_bg.blit(recog, recog.get_rect(center=recog_bg.get_rect().center))
                rrect = recog_bg.get_rect(midtop=(nearest.rect.centerx, recti.bottom + 4))
                screen.blit(recog_bg, rrect)

        if carrying:
            pulse = 0.6 + 0.4 * math.sin(t * 6.0)
            alpha = int(255 * (0.55 + 0.45 * pulse))
            carry_img = carry_label_bg.copy()
            carry_img.set_alpha(alpha)
            cb_rect = carry_img.get_rect(midbottom=(player.rect.centerx, player.rect.top - 6))
            screen.blit(carry_img, cb_rect)

        if message_timer > 0.0 and show_message:
            a = int(255 * (message_timer / message_duration))
            try:
                msg_surf = pixel_font.render(show_message, True, (255, 255, 255))
                shadow = pixel_font.render(show_message, True, (0, 0, 0))
            except Exception:
                msg_surf = pixel_font.render(show_message, True, (255, 255, 255))
                shadow = pixel_font.render(show_message, True, (0, 0, 0))
            msg_x = W // 2
            msg_y = H // 2 + int(H * 0.08)
            shadow_s = shadow.copy()
            shadow_s.set_alpha(a)
            msg_s = msg_surf.copy()
            msg_s.set_alpha(a)
            screen.blit(shadow_s, shadow_s.get_rect(center=(msg_x + 4, msg_y + 4)))
            screen.blit(msg_s, msg_s.get_rect(center=(msg_x, msg_y)))

        if palomita_img is None and check_timer > 0.0:
            a = int(255 * (check_timer / CHECK_DURATION))
            cs = check_surf.copy()
            cs.set_alpha(a)
            cs_rect = cs.get_rect(center=(bin_rect.centerx, bin_rect.top - int(H * 0.05)))
            screen.blit(cs, cs_rect)

        # Timer
        remaining = remaining_ms
        mm = remaining // 1000 // 60
        ss = (remaining // 1000) % 60
        time_str = f"{mm}:{ss:02d}"

        # === INICIO DEL CÓDIGO MODIFICADO PARA EL COLOR DEL TEMPORIZADOR ===
        text_color = (20, 15, 10)  # Color normal (marrón oscuro)
        if remaining_ms <= 30000:  # 30 segundos
            text_color = (200, 40, 40) # Color rojo para la emergencia
        # === FIN DEL CÓDIGO MODIFICADO ===

        margin = int(W * 0.04)
        panel_w, panel_h = int(W * 0.18), int(H * 0.11)
        panel_rect = pygame.Rect(W - margin - panel_w, margin, panel_w, panel_h)
        if timer_panel:
            scaled = pygame.transform.smoothscale(timer_panel, (panel_rect.w, panel_rect.h))
            screen.blit(scaled, panel_rect.topleft)
        else:
            pygame.draw.rect(screen, (30, 20, 15), panel_rect, border_radius=10)
            inner = panel_rect.inflate(-10, -10)
            pygame.draw.rect(screen, (210, 180, 140), inner, border_radius=8)
            pygame.draw.rect(screen, (30, 20, 15), inner, 3, border_radius=8)
            
        # Se utiliza la variable text_color
        txt = timer_font.render(time_str, True, text_color)
        sh  = timer_font.render(time_str, True, (0, 0, 0))
        cx = panel_rect.centerx - int(panel_rect.w * 0.12)
        cy = panel_rect.centery
        screen.blit(sh,  sh.get_rect(center=(cx + 2, cy + 2)))
        screen.blit(txt, txt.get_rect(center=(cx, cy)))

        # Contador Display
        if contador_img:
            contador_rect = contador_img.get_rect(topleft=(int(W * 0.015), int(H * 0.10)))
            screen.blit(contador_img, contador_rect)
            num_font = pygame.font.SysFont("arial", max(18, int(H * 0.055)), bold=True)
            num_surf = num_font.render(str(delivered), True, (255, 255, 255))
            num_shadow = num_font.render(str(delivered), True, (0, 0, 0))
            num_rect = num_surf.get_rect(midright=(contador_rect.right - 20, contador_rect.top + contador_rect.height // 2))
            screen.blit(num_shadow, num_shadow.get_rect(center=(num_rect.centerx + 2, num_rect.centery + 2)))
            screen.blit(num_surf, num_rect)
        else:
            # Fallback si no hay imagen
            num_font = pygame.font.SysFont("arial", max(18, int(H * 0.055)), bold=True)
            _lbl = config.obtener_nombre("txt_entregadas")
            num_surf = num_font.render(f"{_lbl} {delivered}/{total_trash}", True, (255, 255, 255))
            num_shadow = num_font.render(f"{_lbl} {delivered}/{total_trash}", True, (0, 0, 0))
            num_rect = num_surf.get_rect(topleft=(int(W * 0.02), int(H * 0.12)))
            screen.blit(num_shadow, num_shadow.get_rect(center=(num_rect.centerx + 2, num_rect.centery + 2)))
            screen.blit(num_surf, num_rect)

        # PAUSA
        if paused:
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
                inner2 = panel2.inflate(-10, -10)
                pygame.draw.rect(screen, (210, 180, 140), inner2, border_radius=14)

            btn_w, btn_h = int(panel_w2 * 0.80), int(panel_h2 * 0.18)
            cx = panel2.centerx
            y_cont = panel2.top + int(panel_h2 * 0.40)
            y_restart = panel2.top + int(panel_h2 * 0.60)
            y_menu = panel2.top + int(panel_h2 * 0.80)
            r_cont = pygame.Rect(0, 0, btn_w, btn_h); r_cont.center = (cx, y_cont)
            r_restart = pygame.Rect(0, 0, btn_w, btn_h); r_restart.center = (cx, y_restart)
            r_menu = pygame.Rect(0, 0, btn_w, btn_h); r_menu.center = (cx, y_menu)

            if pause_button_assets["cont_base"] is None and panel_scaled:
                try:
                    r_cont_local = r_cont.move(-panel2.x, -panel2.y)
                    r_restart_local = r_restart.move(-panel2.x, -panel2.y)
                    r_menu_local = r_menu.move(-panel2.x, -panel2.y)
                    base_cont = panel_scaled.subsurface(r_cont_local)
                    base_restart = panel_scaled.subsurface(r_restart_local)
                    base_menu = panel_scaled.subsurface(r_menu_local)
                    pause_button_assets["cont_base"] = base_cont
                    pause_button_assets["restart_base"] = base_restart
                    pause_button_assets["menu_base"] = base_menu
                    hwc, hhc = int(r_cont.w * 1.05), int(r_cont.h * 1.05)
                    hwr, hhr = int(r_restart.w * 1.05), int(r_restart.h * 1.05)
                    hwm, hhm = int(r_menu.w * 1.05), int(r_menu.h * 1.05)
                    pause_button_assets["cont_hover"] = pygame.transform.smoothscale(base_cont, (hwc, hhc))
                    pause_button_assets["restart_hover"] = pygame.transform.smoothscale(base_restart, (hwr, hhr))
                    pause_button_assets["menu_hover"] = pygame.transform.smoothscale(base_menu, (hwm, hhm))
                except ValueError:
                    pause_button_assets["cont_base"] = None

            mouse = pygame.mouse.get_pos()
            click = pygame.mouse.get_pressed()[0]

            def draw_btn(base_rect: pygame.Rect, hover_img: pygame.Surface) -> bool:
                hov = base_rect.collidepoint(mouse)
                if hov and hover_img:
                    hover_rect = hover_img.get_rect(center=base_rect.center)
                    screen.blit(hover_img, hover_rect)
                return hov and click

            if draw_btn(r_cont, pause_button_assets["cont_hover"]):
                play_click(assets_dir)
                paused = False
            elif draw_btn(r_restart, pause_button_assets["restart_hover"]):
                play_click(assets_dir)
                reset_level()
                paused = False
            elif draw_btn(r_menu, pause_button_assets["menu_hover"]):
                play_click(assets_dir)
                stop_level_music()
                return None

        # === Lógica de VICTORIA (Redirección a Play) ===
        if not paused and delivered >= total_trash:
            win_img = None
            p = find_by_stem(assets_dir, "win_level1")
            if p:
                img = pygame.image.load(str(p))
                win_img = img.convert_alpha() if p.suffix.lower() == ".png" else img.convert()
                win_img = pygame.transform.smoothscale(win_img, (W, H))
            if win_img:
                screen.blit(win_img, (0, 0))
                pygame.display.flip()
                elapsed2 = 0.0
                while elapsed2 < 2.5:
                    dt2 = clock.tick(60) / 1000.0
                    elapsed2 += dt2
                    for ev in pygame.event.get():
                        if ev.type == pygame.QUIT:
                            stop_level_music()
                            try: import play; play.run(screen, assets_dir)
                            except ImportError: pass
                            return
                        if ev.type == pygame.KEYDOWN or (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1):
                            play_click(assets_dir)
                            stop_level_music()
                            try: import play; play.run(screen, assets_dir)
                            except ImportError: pass
                            return
                stop_level_music()
                try: import play; play.run(screen, assets_dir)
                except ImportError: pass
                return
            # Fallback
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 120, 0, 90))
            screen.blit(overlay, (0, 0))
            wtxt = big.render("¡Parque limpio!", True, (255, 255, 255))
            screen.blit(wtxt, wtxt.get_rect(center=(W // 2, H // 2 - 10)))
            pygame.display.flip()
            pygame.time.delay(1200)
            stop_level_music()
            try: import play; play.run(screen, assets_dir)
            except ImportError: pass
            return

        # === Lógica de DERROTA (Redirección a Play) ===
        if remaining_ms <= 0 and delivered < total_trash:
            stop_level_music()
            if pantalla_lose_img:
                try:
                    iw, ih = pantalla_lose_img.get_size()
                    ratio = max(W / iw, H / ih) 
                    new_w, new_h = int(iw * ratio), int(ih * ratio)
                    scaled = pygame.transform.smoothscale(pantalla_lose_img, (new_w, new_h))
                    rect = scaled.get_rect(center=(W//2, H//2))
                    screen.blit(scaled, rect)
                except Exception:
                    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 160))
                    screen.blit(overlay, (0, 0))
                    msg = big.render(config.obtener_nombre("txt_tiempo_agotado"), True, (255, 255, 255))
                    screen.blit(msg, msg.get_rect(center=(W // 2, H // 2 - 10)))
            else:
                overlay = pygame.Surface((W, H), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 160))
                screen.blit(overlay, (0, 0))
                msg = big.render(config.obtener_nombre("txt_tiempo_agotado"), True, (255, 255, 255))
                screen.blit(msg, msg.get_rect(center=(W // 2, H // 2 - 10)))

            pygame.display.flip()
            pygame.time.delay(1200)
            try: import play; play.run(screen, assets_dir)
            except ImportError: pass
            return 

        pygame.display.flip()
