from __future__ import annotations
import pygame, math, random, re
from pathlib import Path
from typing import Optional

# === CAMBIO: Importar funciones de música ===
try:
    from audio_shared import start_level_music, start_suspense_music, stop_level_music
except ImportError:
    print("WARN: No se pudo importar audio_shared. La música no funcionará.")
    # Fallback para que el juego no crashee si audio_shared no está listo
    def start_level_music(assets_dir: Path): pass
    def start_suspense_music(assets_dir: Path): pass
    def stop_level_music(): pass
# ==========================================


# ====== SFX click (VOLÚMEN AJUSTABLE) ======
CLICK_VOL = 0.25
_click_snd: pygame.mixer.Sound | None = None

def play_click(assets_dir: Path):
    """Reproduce el sfx de click con el volumen global CLICK_VOL."""
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

# ---------- helpers ----------
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
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height() * r)))

def make_glow(radius: int) -> pygame.Surface:
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for rr in range(radius, 0, -1):
        a = max(5, int(180 * (rr / radius) ** 2))
        pygame.draw.circle(s, (255, 255, 120, a), (radius, radius), rr)
    return s

def load_bg_fit(assets_dir: Path, W: int, H: int) -> tuple[pygame.Surface, pygame.Rect]:
    """
    Carga el fondo y lo AJUSTA manteniendo proporción (fit), sin recortar.
    Devuelve (surface_escalada, rect_centrado).
    """
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
    ratio = min(W / iw, H / ih)
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
    """Anclaje más bajo (palmas) con leve ajuste por dirección."""
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

# === CARGA DE FRAMES DESDE /assets/PERSONAJE H/ (igual al fácil) ===========
def load_char_frames(assets_dir: Path, target_h: int) -> dict[str, list[pygame.Surface] | pygame.Surface]:
    char_dir = assets_dir / "PERSONAJE H"
    if not char_dir.exists():
        raise FileNotFoundError("No se encontró la carpeta 'assets/PERSONAJE H'")

    def _load_seq(prefix: str) -> list[pygame.Surface]:
        files: list[Path] = []
        for ext in (".png", ".jpg", ".jpeg"):
            files += list(char_dir.glob(f"{prefix}_[0-9]*{ext}"))
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

    if right and not left:
        left = [pygame.transform.flip(f, True, False) for f in right]
    if left and not right:
        right = [pygame.transform.flip(f, True, False) for f in left]
    if not down: down = right[:1] if right else []
    if not up:   up   = right[:1] if right else []

    if idle_right is None and right: idle_right = right[0]
    if idle_left  is None and idle_right is not None: idle_left = pygame.transform.flip(idle_right, True, False)
    if idle_down  is None and down:  idle_down = down[0]
    if idle_up    is None and up:    idle_up   = up[0]

    def _scale(f: pygame.Surface) -> pygame.Surface:
        h = target_h; w = int(f.get_width() * (h / f.get_height()))
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

# ---------- entidades ----------
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
        self.image = start_img  # type: ignore[assignment]
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
            if abs(dx) >= abs(dy):
                self.dir = "left" if dx > 0 else "right"  # invertido como en fácil
            else:
                self.dir = "down" if dy > 0 else "up"

            self.rect.x += int(dx * self.speed * dt)
            self.rect.y += int(dy * self.speed * dt)
            self.rect.clamp_ip(self.bounds)

            self.anim_timer += dt
            if self.anim_timer >= self.anim_dt:
                self.anim_timer -= self.anim_dt
                seq: list[pygame.Surface] = self.frames.get(self.dir, [])  # type: ignore[assignment]
                if seq:
                    self.frame_idx = (self.frame_idx + 1) % len(seq)

            seq: list[pygame.Surface] = self.frames.get(self.dir, [])  # type: ignore[assignment]
            if seq:
                self.image = seq[self.frame_idx % len(seq)]
        else:
            idle_key = f"idle_{self.dir}"
            idle_img = self.frames.get(idle_key)
            if isinstance(idle_img, pygame.Surface):
                self.image = idle_img
            else:
                seq: list[pygame.Surface] = self.frames.get(self.dir, [])  # type: ignore[assignment]
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

# ---------- NIVEL PRINCIPAL ----------
def run(screen: pygame.Surface, assets_dir: Path, personaje: str = "EcoGuardian", dificultad: str = "Difícil"):
    pygame.font.init()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 26, bold=True)
    big  = pygame.font.SysFont("arial", 54, bold=True)
    timer_font = pygame.font.SysFont("arial", 42, bold=True)

    W, H = screen.get_size()
    background, bg_rect = load_bg_fit(assets_dir, W, H)

    # --- Basurero ---
    bin_p = (find_by_stem(assets_dir, "basurero")
             or find_by_stem(assets_dir, "bote_basura")
             or find_by_stem(assets_dir, "trash_bin"))
    if bin_p:
        bin_img = scale_to_width(load_surface(bin_p), int(W * 0.14))
    else:
        bin_img = pygame.Surface((int(W * 0.10), int(W * 0.15)), pygame.SRCALPHA)
        pygame.draw.rect(bin_img, (90, 90, 90), bin_img.get_rect(), border_radius=12)
        pygame.draw.rect(bin_img, (255, 255, 255), bin_img.get_rect(), 2, border_radius=12)
    bin_rect = bin_img.get_rect()
    bin_rect.bottomright = (W - int(W * 0.03), H - int(W * 0.03))
    BIN_RADIUS = max(32, int(W * 0.028))  # un poco menor que en fácil

    # --- Basuras (12) ---
    sprite_trash = load_trash_images(assets_dir)
    if not sprite_trash:
        for col in [(160, 160, 160), (70, 160, 70), (60, 130, 200)]:
            s = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.rect(s, col, (4, 4, 32, 32), border_radius=6)
            sprite_trash.append(s)
    trash_group = pygame.sprite.Group()
    total_trash = 12
    for i in range(total_trash):
        x = random.randint(int(W * 0.16), int(W * 0.84))
        y = random.randint(int(H * 0.46), int(H * 0.86))
        img = sprite_trash[i % len(sprite_trash)]
        trash_group.add(Trash(img, (x, y), int(W * 0.032)))

    # --- Personaje ---
    frames = load_char_frames(assets_dir, target_h=int(H * 0.14))
    player = Player(frames, (int(W * 0.16), int(H * 0.75)), pygame.Rect(0, 0, W, H), speed=340, anim_fps=9.0)

    carrying: Optional[Trash] = None
    delivered = 0

    PICK_KEYS = (pygame.K_e, pygame.K_RETURN)
    INTERACT_DIST = int(W * 0.05)      # un poco más exigente

    # =====================================================================
    # === CAMBIO 1: Lógica del temporizador (Igual que en 'facil') ===
    # =====================================================================
    TOTAL_MS = 60_000  # <-- 60 SEGUNDOS PARA DIFICIL
    remaining_ms = TOTAL_MS  # <-- Usamos esta variable
    
    # === CAMBIO: Iniciar música de nivel ===
    start_level_music(assets_dir)

    # --- Panel del temporizador (tu imagen) ---
    timer_panel = None
    for nm in ["temporizador", "timer_panel", "panel_tiempo", "TEMPORAZIDOR"]:
        p = find_by_stem(assets_dir, nm)
        if p:
            timer_panel = load_surface(p)
            break

    # =====================================================================
    # === CAMBIO 2: Añadir assets del menú de pausa (Igual que en 'facil') ===
    # =====================================================================
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

    # =====================================================================
    # === AÑADIR ESTO: Cargar la imagen de derrota ===
    # =====================================================================
    img_derrota = None
    # Intenta encontrar la imagen de derrota (asumimos que la llamaste 'derrota_nivel.jpg')
    p_derrota = find_by_stem(assets_dir, "derrota_nivel") 
    
    if p_derrota:
        # Cargar la imagen
        temp_img = load_surface(p_derrota) 
        # Escalarla al tamaño de la pantalla (W, H)
        img_derrota = pygame.transform.smoothscale(temp_img, (W, H))
    else:
        print("ADVERTENCIA: No se encontró la imagen 'derrota_nivel.jpg' en assets/. Se usará el fondo negro.")
    # =====================================================================


    # =====================================================================
    # === CAMBIO 3: Añadir función reset_level() (Adaptada para 'dificil') ===
    # =====================================================================
    def reset_level():
        nonlocal trash_group, carrying, delivered, remaining_ms
        # === CAMBIO: Añadir 'suspense_music_started' ===
        nonlocal suspense_music_started
        trash_group.empty()
        # Usa los parámetros de 'dificil' (12 basuras, coords, tamaño)
        for i in range(total_trash):
            x = random.randint(int(W * 0.16), int(W * 0.84))
            y = random.randint(int(H * 0.46), int(H * 0.86))
            img = sprite_trash[i % len(sprite_trash)]
            trash_group.add(Trash(img, (x, y), int(W * 0.032)))
        carrying = None
        delivered = 0
        remaining_ms = TOTAL_MS  # <-- Reinicia el tiempo
        # === CAMBIO: Reiniciar estado de música ===
        suspense_music_started = False
        start_level_music(assets_dir)

    paused = False
    t = 0.0

    # === CAMBIO: Variable de estado para música de suspenso ===
    suspense_music_started = False

    while True:
        dt = min(clock.tick(60) / 1000.0, 0.033)
        t += dt
        interact = False

        # --- CAMBIO 4: Lógica de tiempo movida ---
        # (ya no se calcula 'elapsed' o 'remaining' aquí)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                # === CAMBIO: Detener música ===
                stop_level_music()
                return None
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    play_click(assets_dir)
                    # === CAMBIO: Detener música ===
                    stop_level_music()
                    return None
                if e.key == pygame.K_SPACE:
                    paused = not paused
                    play_click(assets_dir)
                if e.key in PICK_KEYS:
                    interact = True

        # =====================================================================
        # === CAMBIO 5: Actualización del juego y timer (Igual que en 'facil') ===
        # =====================================================================
        if not paused and remaining_ms > 0:
            # Restamos el tiempo de este frame
            remaining_ms -= int(dt * 1000)
            remaining_ms = max(0, remaining_ms)
            
            # === CAMBIO: Lógica del trigger de música de suspenso ===
            if remaining_ms <= 30000 and not suspense_music_started:
                start_suspense_music(assets_dir)
                suspense_music_started = True
            
            player.handle_input(dt)

            if carrying:
                carrying.carried = True
                ax, ay = _carry_anchor(player, carrying) # Mantenemos esta línea de 'dificil'
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
                else:
                    d = math.hypot(player.rect.centerx - bin_rect.centerx,
                                    player.rect.centery - bin_rect.centery)
                    if d <= BIN_RADIUS * 1.15:
                        trash_group.remove(carrying)
                        carrying = None
                        delivered += 1

        # --- DIBUJO ---
        screen.fill((34, 45, 38))
        screen.blit(background, bg_rect)

        screen.blit(bin_img, bin_rect)
        for tr in trash_group:
            tr.draw(screen, t)
        screen.blit(player.image, player.rect)
        if carrying:
            screen.blit(carrying.image, carrying.rect)

        # HUD
        hud = [
            "Nivel 1 – El Parque (Difícil, con tiempo)", # Texto 'dificil'
            "Mover: WASD/Flechas | Recoger/Depositar: E / Enter | Pausa: Espacio",
            f"Entregadas: {delivered} / {total_trash}",
        ]
        for i, line in enumerate(hud):
            screen.blit(font.render(line, True, (15, 15, 15)), (16, 25 + i * 26))

        # =====================================================================
        # === CAMBIO 6: Display del timer usa 'remaining_ms' (Igual que en 'facil') ===
        # =====================================================================
        remaining = remaining_ms # <-- Lee de la variable correcta
        
        mm = remaining // 1000 // 60
        ss = (remaining // 1000) % 60
        time_str = f"{mm}:{ss:02d}"

        margin = int(W * 0.04)
        panel_w, panel_h = int(W * 0.18), int(H * 0.11)   # compacto
        panel_rect = pygame.Rect(W - margin - panel_w, margin, panel_w, panel_h)

        if timer_panel:
            scaled = pygame.transform.smoothscale(timer_panel, (panel_rect.w, panel_rect.h))
            screen.blit(scaled, panel_rect.topleft)
        else:
            pygame.draw.rect(screen, (30, 20, 15), panel_rect, border_radius=10)
            inner = panel_rect.inflate(-10, -10)
            pygame.draw.rect(screen, (210, 180, 140), inner, border_radius=8)
            pygame.draw.rect(screen, (30, 20, 15), inner, 3, border_radius=8)

        # número ligeramente desplazado a la IZQUIERDA para no tapar el reloj de arena
        txt = timer_font.render(time_str, True, (20, 15, 10))
        sh  = timer_font.render(time_str, True, (0, 0, 0))
        cx = panel_rect.centerx - int(panel_rect.w * 0.12)
        cy = panel_rect.centery
        screen.blit(sh,  sh.get_rect(center=(cx + 2, cy + 2)))
        screen.blit(txt, txt.get_rect(center=(cx, cy)))

        # =====================================================================
        # === CAMBIO 7: Bloque de dibujo del menú de pausa (Igual que en 'facil') ===
        # =====================================================================
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

            # Tamaños y posiciones para los botones
            btn_w, btn_h = int(panel_w2 * 0.80), int(panel_h2 * 0.18)
            cx = panel2.centerx
            
            y_cont_pct    = 0.40
            y_restart_pct = 0.60
            y_menu_pct    = 0.80
            
            y_cont    = panel2.top + int(panel_h2 * y_cont_pct)
            y_restart = panel2.top + int(panel_h2 * y_restart_pct)
            y_menu    = panel2.top + int(panel_h2 * y_menu_pct)

            r_cont    = pygame.Rect(0, 0, btn_w, btn_h); r_cont.center    = (cx, y_cont)
            r_restart = pygame.Rect(0, 0, btn_w, btn_h); r_restart.center = (cx, y_restart)
            r_menu    = pygame.Rect(0, 0, btn_w, btn_h); r_menu.center    = (cx, y_menu)

            # Crear botones "recortados" y versiones "hover"
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
                    
                    hover_w_cont, hover_h_cont = int(r_cont.w * 1.05), int(r_cont.h * 1.05)
                    hover_w_rest, hover_h_rest = int(r_restart.w * 1.05), int(r_restart.h * 1.05)
                    hover_w_menu, hover_h_menu = int(r_menu.w * 1.05), int(r_menu.h * 1.05)
                    
                    pause_button_assets["cont_hover"] = pygame.transform.smoothscale(base_cont, (hover_w_cont, hover_h_cont))
                    pause_button_assets["restart_hover"] = pygame.transform.smoothscale(base_restart, (hover_w_rest, hover_h_rest))
                    pause_button_assets["menu_hover"] = pygame.transform.smoothscale(base_menu, (hover_w_menu, hover_h_menu))
                except ValueError:
                    pause_button_assets["cont_base"] = None
                    print("Advertencia: No se pudieron crear los subsurfaces de los botones.")
                

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
                reset_level() # <-- Llama a la nueva función
                paused = False
            elif draw_btn(r_menu, pause_button_assets["menu_hover"]):
                play_click(assets_dir)
                # === CAMBIO: Detener música ===
                stop_level_music()
                return None


        # =====================================================================
        # === CAMBIO 8: Lógica de victoria/derrota actualizada (Igual que en 'facil') ===
        # =====================================================================
        
        # --- victoria ---
        if not paused and delivered >= total_trash: # <-- Añadido 'not paused'
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
                while elapsed2 < 2.0:
                    dt2 = clock.tick(60) / 1000.0
                    elapsed2 += dt2
                    for ev in pygame.event.get():
                        if ev.type == pygame.QUIT:
                            # === CAMBIO: Detener música ===
                            stop_level_music()
                            return {"estado": "completado", "recolectadas": total_trash}
                        if ev.type == pygame.KEYDOWN or (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1):
                            play_click(assets_dir)
                            # === CAMBIO: Detener música ===
                            stop_level_music()
                            return {"estado": "completado", "recolectadas": total_trash}
                # === CAMBIO: Detener música ===
                stop_level_music()
                return {"estado": "completado", "recolectadas": total_trash}
            else:
                overlay = pygame.Surface((W, H), pygame.SRCALPHA)
                overlay.fill((0, 120, 0, 90))
                screen.blit(overlay, (0, 0))
                wtxt = big.render("¡Parque limpio (Difícil)!", True, (255, 255, 255)) # Mantenemos texto
                screen.blit(wtxt, wtxt.get_rect(center=(W // 2, H // 2 - 10)))
                pygame.display.flip()
                pygame.time.delay(1200)
                # === CAMBIO: Detener música ===
                stop_level_music()
                return {"estado": "completado", "recolectadas": total_trash}

        # =====================================================================
        # === INICIO: CÓDIGO DE DERROTA MODIFICADO ===
        # =====================================================================
        
        # --- derrota por tiempo ---
        if remaining_ms <= 0 and delivered < total_trash: # <-- Usa 'remaining_ms'
            
            # === CAMBIO: Mostrar imagen de derrota en lugar de texto ===
            
            # Detener la música de fondo
            stop_level_music() 
            
            if img_derrota:
                # Si la imagen FUE cargada, la mostramos
                screen.blit(img_derrota, (0, 0))
                pygame.display.flip()
                
                # Esperar 2.5 segundos O hasta que el jugador haga clic/presione tecla
                elapsed_derrota = 0.0
                while elapsed_derrota < 2.5:
                    dt_derrota = clock.tick(60) / 1000.0
                    elapsed_derrota += dt_derrota
                    for ev in pygame.event.get():
                        if ev.type == pygame.QUIT:
                            return {"estado": "tiempo_agotado", "recolectadas": delivered}
                        if ev.type == pygame.KEYDOWN or (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1):
                            play_click(assets_dir) # Sonido de clic opcional
                            return {"estado": "tiempo_agotado", "recolectadas": delivered}
                
                # Si se acaba el tiempo, simplemente salimos
                return {"estado": "tiempo_agotado", "recolectadas": delivered}

            else:
                # --- Fallback: Si no se encontró img_derrota, usar el código original ---
                overlay = pygame.Surface((W, H), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 160))
                screen.blit(overlay, (0, 0))
                msg = big.render("¡Tiempo agotado!", True, (255, 255, 255))
                screen.blit(msg, msg.get_rect(center=(W // 2, H // 2 - 10)))
                pygame.display.flip()
                pygame.time.delay(1200)
                return {"estado": "tiempo_agotado", "recolectadas": delivered}
        
        # =====================================================================
        # === FIN: CÓDIGO DE DERROTA MODIFICADO ===
        # =====================================================================

        pygame.display.flip()