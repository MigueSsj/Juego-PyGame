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
CLICK_VOL = 0.25  # <-- AJUSTA AQUÍ (0.0 = mudo, 1.0 = máximo)
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
    """Carga el fondo y lo AJUSTA manteniendo proporción (fit), sin recortar."""
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

# === Punto de anclaje para sostener la basura ===
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

# === CARGA DE FRAMES (AHORA DETECTA M/H) ===
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

    # === ¡NUEVA LÓGICA DE PREFIJO! ===
    # Si es PERSONAJE M, busca "womanguardian_". Si no, busca "ecoguardian_"
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
    if not up:   up   = right[:1] if right else []

    if idle_right is None and right: idle_right = right[0]
    if idle_left  is None and idle_right is not None: idle_left = pygame.transform.flip(idle_right, True, False)
    if idle_down  is None and down:  idle_down = down[0]
    if idle_up    is None and up:    idle_up   = up[0]

    def _scale(f: pygame.Surface) -> pygame.Surface:
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

    def _normalize_single(s: pygame.Surface) -> pygame.Surface:
        if s is None: # Añadir check por si idle_up o down son None
             # Devuelve una superficie vacía del tamaño escalado_base
             h = target_h
             w = int(h * 0.7) # Asumir una proporción si no hay imagen
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

# ---------- entidades ----------
class Player(pygame.sprite.Sprite):
    def __init__(self, frames: dict[str, list[pygame.Surface] | pygame.Surface], pos, bounds: pygame.Rect,
                 speed: float = 320, anim_fps: float = 8.0):
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

            # Invertido L/R si tus sprites están al revés
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
def run(screen: pygame.Surface, assets_dir: Path, personaje: str = "EcoGuardian", dificultad: str = "Fácil"):
    pygame.font.init()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 26, bold=True)
    big  = pygame.font.SysFont("arial", 54, bold=True)
    timer_font = pygame.font.SysFont("arial", 42, bold=True)

    W, H = screen.get_size()
    background, bg_rect = load_bg_fit(assets_dir, W, H)

    # Basurero
    bin_p = (find_by_stem(assets_dir, "basurero")
             or find_by_stem(assets_dir, "bote_basura")
             or find_by_stem(assets_dir, "trash_bin"))
    if bin_p:
        bin_img = scale_to_width(load_surface(bin_p), int(W * 0.15))
    else:
        bin_img = pygame.Surface((int(W * 0.10), int(W * 0.15)), pygame.SRCALPHA)
        pygame.draw.rect(bin_img, (90, 90, 90), bin_img.get_rect(), border_radius=12)
        pygame.draw.rect(bin_img, (255, 255, 255), bin_img.get_rect(), 2, border_radius=12)
    bin_rect = bin_img.get_rect()
    bin_rect.bottomright = (W - int(W * 0.03), H - int(W * 0.03))
    BIN_RADIUS = max(36, int(W * 0.03))

    # Basuras
    sprite_trash = load_trash_images(assets_dir)
    if not sprite_trash:
        for col in [(160, 160, 160), (70, 160, 70), (60, 130, 200)]:
            s = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.rect(s, col, (4, 4, 32, 32), border_radius=6)
            sprite_trash.append(s)
    trash_group = pygame.sprite.Group()
    total_trash = 6
    for i in range(total_trash):
        x = random.randint(int(W * 0.18), int(W * 0.82))
        y = random.randint(int(H * 0.50), int(H * 0.86))
        img = sprite_trash[i % len(sprite_trash)]
        trash_group.add(Trash(img, (x, y), int(W * 0.035)))

    # Personaje
    # === ¡AQUÍ ESTÁ LA CORRECCIÓN! ===
    # Pasa la variable 'personaje' (que puede ser "PERSONAJE M") a la función.
    frames = load_char_frames(assets_dir, target_h=int(H * 0.14), char_folder=personaje)
    player = Player(frames, (int(W * 0.16), int(H * 0.75)), pygame.Rect(0, 0, W, H), speed=320, anim_fps=8.0)

    carrying: Optional[Trash] = None
    delivered = 0

    PICK_KEYS = (pygame.K_e, pygame.K_RETURN)
    INTERACT_DIST = int(W * 0.055)

    paused = False
    t = 0.0

    # === NUEVOS ELEMENTOS VISUALES DE INTERACCIÓN ===
    popup_font = pygame.font.SysFont("arial", 28, bold=True)
    small_font = pygame.font.SysFont("arial", 20, bold=True)
    show_message = ""         # texto a mostrar temporalmente
    message_timer = 0.0       # tiempo restante del mensaje (segundos)
    message_duration = 1.5    # duración por defecto para mensajes (segundos)

    # icono "E" (fondo + letra)
    icon_e_letter = popup_font.render("E", True, (255, 255, 255))
    icon_bg = pygame.Surface((icon_e_letter.get_width() + 18, icon_e_letter.get_height() + 12), pygame.SRCALPHA)
    pygame.draw.rect(icon_bg, (0, 0, 0, 180), icon_bg.get_rect(), border_radius=8)
    icon_bg.blit(icon_e_letter, icon_e_letter.get_rect(center=icon_bg.get_rect().center))

    # palomita (se renderiza con fuente grande en verde)
    check_font = pygame.font.SysFont("arial", 72, bold=True)
    check_surf_base = check_font.render("✓", True, (40, 180, 40))
    check_surf = check_surf_base.copy()
    check_timer = 0.0
    CHECK_DURATION = 1.0

    # indicador permanente cuando llevas basura (pequeño)
    carry_label = small_font.render("Basura en las manos", True, (255, 255, 255))
    carry_label_bg = pygame.Surface((carry_label.get_width() + 12, carry_label.get_height() + 8), pygame.SRCALPHA)
    pygame.draw.rect(carry_label_bg, (0,0,0,160), carry_label_bg.get_rect(), border_radius=6)
    carry_label_bg.blit(carry_label, carry_label.get_rect(center=carry_label_bg.get_rect().center))

    # =====================================================================
    # === CAMBIO 1: Lógica del temporizador ===
    # =====================================================================
    TOTAL_MS = 80_000
    remaining_ms = TOTAL_MS  # <-- Esta es ahora la variable principal del tiempo
    
    # === CAMBIO: Iniciar música de nivel ===
    start_level_music(assets_dir)


    # === Panel del temporizador (arriba-derecha, más chico) ===
    timer_panel = None
    for nm in ["temporizador", "timer_panel", "panel_tiempo", "TEMPORAZIDOR"]:
        p = find_by_stem(assets_dir, nm)
        if p:
            timer_panel = load_surface(p)
            break

    # === PAUSA (usa assets/PAUSA/) ===
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
    # === CAMBIO 2: reset_level() ahora resetea 'remaining_ms' y música ===
    # =====================================================================
    def reset_level():
        nonlocal trash_group, carrying, delivered, remaining_ms, message_timer, check_timer
        # === CAMBIO: Añadir 'suspense_music_started' ===
        nonlocal suspense_music_started
        trash_group.empty()
        for i in range(total_trash):
            x = random.randint(int(W * 0.18), int(W * 0.82))
            y = random.randint(int(H * 0.50), int(H * 0.86))
            img = sprite_trash[i % len(sprite_trash)]
            trash_group.add(Trash(img, (x, y), int(W * 0.035)))
        carrying = None
        delivered = 0
        remaining_ms = TOTAL_MS  # <-- Se resetea el tiempo
        # === CAMBIO: Reiniciar estado de música ===
        suspense_music_started = False
        start_level_music(assets_dir)
        # reset mensajes
        message_timer = 0.0
        check_timer = 0.0

    # === CAMBIO: Variable de estado para música de suspenso ===
    suspense_music_started = False

    # === Intento: buscar pantalla de LOSE para NIVEL 1P (usuario pidió esto) ===
    pantalla_lose_img = None
    try:
        lose_folder = assets_dir / "PANTALLA LOSE"
        # el usuario indicó "mayúsculas pero sin el _" y nombre "NIVEL 1P"
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

        # actualizar timers visuales
        if message_timer > 0.0:
            message_timer = max(0.0, message_timer - dt)
        if check_timer > 0.0:
            check_timer = max(0.0, check_timer - dt)

        # =====================================================================
        # === CAMBIO 3: Cálculo de tiempo ELIMINADO de aquí ===
        # =====================================================================

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
                    # No necesitamos lógica extra del timer aquí
                if e.key in PICK_KEYS:
                    interact = True

        # =====================================================================
        # === CAMBIO 4: Lógica del juego y actualización del timer y música ===
        # =====================================================================
        if not paused and remaining_ms > 0:
            # Restamos el tiempo de este frame
            remaining_ms -= int(dt * 1000)
            remaining_ms = max(0, remaining_ms) # Nos aseguramos que no baje de 0
            
            # === CAMBIO: Lógica del trigger de música de suspenso ===
            if remaining_ms <= 30000 and not suspense_music_started:
                start_suspense_music(assets_dir)
                suspense_music_started = True

            player.handle_input(dt)

            if carrying:
                carrying.carried = True
                # === CAMBIO: Usar _carry_anchor para la posición (EN LOS BRAZOS) ===
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
                        # Mensaje: basura recolectada (fade)
                        show_message = "Basura recolectada"
                        message_timer = message_duration
                        play_click(assets_dir)
                else:
                    d = math.hypot(player.rect.centerx - bin_rect.centerx,
                                   player.rect.centery - bin_rect.centery)
                    if d <= BIN_RADIUS * 1.2:
                        # entregar
                        try:
                            trash_group.remove(carrying)
                        except Exception:
                            # si ya no está en el grupo, ignorar
                            pass
                        carrying = None
                        delivered += 1
                        # Mostrar palomita y mensaje
                        check_timer = CHECK_DURATION
                        show_message = "¡Basura entregada!"
                        message_timer = message_duration
                        play_click(assets_dir)
        
        # El resto del código (dibujo) se ejecuta siempre
        
        # DIBUJO
        screen.fill((34, 45, 38))
        screen.blit(background, bg_rect)

        screen.blit(bin_img, bin_rect)
        for tr in trash_group:
            tr.draw(screen, t)
        screen.blit(player.image, player.rect)
        if carrying:
            # el objeto ya fue bliteado con carrying rect al actualizar arriba,
            # pero igualmente lo bliteamos encima del jugador para asegurar visibilidad.
            screen.blit(carrying.image, carrying.rect)

        # HUD
        hud = [
            "Nivel 1 – El Parque (Fácil, con tiempo)",
            "Mover: WASD/Flechas | Recoger/Depositar: E / Enter | Pausa: Espacio",
            f"Entregadas: {delivered} / {total_trash}",
        ]
        for i, line in enumerate(hud):
            screen.blit(font.render(line, True, (15, 15, 15)), (16 + 2, 25 + 2 + i * 26))
            screen.blit(font.render(line, True, (255, 255, 255)), (16, 25 + i * 26))


        # =====================================================================
        # === DIBUJOS Y EFECTOS NUEVOS: icono "E", mensajes y palomita ===
        # =====================================================================

        # 1) Icono "E" sobre basura cercana (si el jugador NO lleva basura)
        if not carrying:
            # buscar la basura más cercana dentro de INTERACT_DIST
            nearest = None
            bestd = 1e9
            for tr in trash_group:
                d = math.hypot(player.rect.centerx - tr.rect.centerx,
                               player.rect.centery - tr.rect.centery)
                if d < bestd:
                    bestd = d; nearest = tr
            if nearest and bestd <= INTERACT_DIST:
                # dibujar icono un poco encima de la basura
                icon_pos = (nearest.rect.centerx, nearest.rect.top - int(H * 0.03))
                ib = icon_bg.copy()
                # hacer un pulso sutil en la opacidad
                pulse = 0.5 + 0.5 * math.sin(t * 6.0)
                alpha = int(220 * (0.6 + 0.4 * pulse))
                ib.set_alpha(alpha)
                recti = ib.get_rect(center=icon_pos)
                screen.blit(ib, recti)

                # mensaje pequeño "Recoger: E" cerca de la basura (opcional)
                recog = small_font.render("Recoger: E", True, (255, 255, 255))
                recog_bg = pygame.Surface((recog.get_width() + 10, recog.get_height() + 6), pygame.SRCALPHA)
                pygame.draw.rect(recog_bg, (0,0,0,160), recog_bg.get_rect(), border_radius=6)
                recog_bg.blit(recog, recog.get_rect(center=recog_bg.get_rect().center))
                rrect = recog_bg.get_rect(midtop=(nearest.rect.centerx, recti.bottom + 4))
                screen.blit(recog_bg, rrect)

        # 2) Indicador constante cuando llevas basura: "Basura en las manos" sobre el jugador
        if carrying:
            # dibujar con fondo y leve fade de pulso
            # pulso para hacerlo más visible
            pulse = 0.6 + 0.4 * math.sin(t * 6.0)
            alpha = int(255 * (0.55 + 0.45 * pulse))
            carry_img = carry_label_bg.copy()
            carry_img.set_alpha(alpha)
            cb_rect = carry_img.get_rect(midbottom=(player.rect.centerx, player.rect.top - 6))
            screen.blit(carry_img, cb_rect)

        # 3) Mensajes temporales (fade out usando message_timer)
        if message_timer > 0.0:
            a = int(255 * (message_timer / message_duration))
            msg_surf = popup_font.render(show_message, True, (255, 255, 255))
            bg = pygame.Surface((msg_surf.get_width() + 20, msg_surf.get_height() + 12), pygame.SRCALPHA)
            pygame.draw.rect(bg, (0, 0, 0, 200), bg.get_rect(), border_radius=10)
            bg.blit(msg_surf, msg_surf.get_rect(center=bg.get_rect().center))
            bg.set_alpha(a)
            screen.blit(bg, bg.get_rect(midtop=(W//2, int(H * 0.06))))

        # 4) Palomita al entregar (fade durante check_timer)
        if check_timer > 0.0:
            a = int(255 * (check_timer / CHECK_DURATION))
            cs = check_surf.copy()
            cs.set_alpha(a)
            # aparece centrada sobre el basurero (o un poco por encima)
            cs_rect = cs.get_rect(center=(bin_rect.centerx, bin_rect.top - int(H * 0.05)))
            screen.blit(cs, cs_rect)


        # =====================================================================
        # === CAMBIO 5: El display del timer ahora LEE de 'remaining_ms' ===
        # =====================================================================
        remaining = remaining_ms  # <-- 'remaining' es ahora solo para mostrar
        
        mm = remaining // 1000 // 60
        ss = (remaining // 1000) % 60
        time_str = f"{mm}:{ss:02d}"

        margin = int(W * 0.04)
        panel_w, panel_h = int(W * 0.18), int(H * 0.11)  # más corto y compacto
        panel_rect = pygame.Rect(W - margin - panel_w, margin, panel_w, panel_h)

        if timer_panel:
            scaled = pygame.transform.smoothscale(timer_panel, (panel_rect.w, panel_rect.h))
            screen.blit(scaled, panel_rect.topleft)
        else:
            pygame.draw.rect(screen, (30, 20, 15), panel_rect, border_radius=10)
            inner = panel_rect.inflate(-10, -10)
            pygame.draw.rect(screen, (210, 180, 140), inner, border_radius=8)
            pygame.draw.rect(screen, (30, 20, 15), inner, 3, border_radius=8)

        # número desplazado un poco a la izquierda para no tapar el reloj de arena
        txt = timer_font.render(time_str, True, (20, 15, 10))
        sh  = timer_font.render(time_str, True, (0, 0, 0))
        cx = panel_rect.centerx - int(panel_rect.w * 0.12)
        cy = panel_rect.centery
        screen.blit(sh,  sh.get_rect(center=(cx + 2, cy + 2)))
        screen.blit(txt, txt.get_rect(center=(cx, cy)))

        # === PAUSA ===
        if paused:
            # Esta sección se dibuja ENCIMA del juego y el HUD
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

            # Título "PAUSA" eliminado (comentado)
            # title = big.render("PAUSA", True, (25, 20, 15))
            # screen.blit(title, title.get_rect(midtop=(W//2, panel2.top + 20)))

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
                    # Calcular rects locales (dentro del panel)
                    r_cont_local    = r_cont.move(-panel2.x, -panel2.y)
                    r_restart_local = r_restart.move(-panel2.x, -panel2.y)
                    r_menu_local    = r_menu.move(-panel2.x, -panel2.y)
                    
                    # Recortar las imágenes base del panel escalado
                    base_cont    = panel_scaled.subsurface(r_cont_local)
                    base_restart = panel_scaled.subsurface(r_restart_local)
                    base_menu    = panel_scaled.subsurface(r_menu_local)
                    
                    pause_button_assets["cont_base"] = base_cont
                    pause_button_assets["restart_base"] = base_restart
                    pause_button_assets["menu_base"] = base_menu
                    
                    # Crear versiones "hover" (un 5% más grandes)
                    hover_w_cont, hover_h_cont = int(r_cont.w * 1.05), int(r_cont.h * 1.05)
                    hover_w_rest, hover_h_rest = int(r_restart.w * 1.05), int(r_restart.h * 1.05)
                    hover_w_menu, hover_h_menu = int(r_menu.w * 1.05), int(r_menu.h * 1.05)
                    
                    pause_button_assets["cont_hover"] = pygame.transform.smoothscale(base_cont, (hover_w_cont, hover_h_cont))
                    pause_button_assets["restart_hover"] = pygame.transform.smoothscale(base_restart, (hover_w_rest, hover_h_rest))
                    pause_button_assets["menu_hover"] = pygame.transform.smoothscale(base_menu, (hover_w_menu, hover_h_menu))
                except ValueError:
                    # Esto puede pasar si los rects están fuera del panel, reseteamos para que no falle
                    pause_button_assets["cont_base"] = None # Resetea para reintentar
                    print("Advertencia: No se pudieron crear los subsurfaces de los botones.")
                

            mouse = pygame.mouse.get_pos()
            click = pygame.mouse.get_pressed()[0]

            # Función draw_btn (Efecto de Escala)
            def draw_btn(base_rect: pygame.Rect, hover_img: pygame.Surface) -> bool:
                hov = base_rect.collidepoint(mouse)
                if hov and hover_img:
                    # Dibujar la imagen hover, centrada sobre el botón original
                    hover_rect = hover_img.get_rect(center=base_rect.center)
                    screen.blit(hover_img, hover_rect)
                
                # Devuelve True si se hace clic mientras se está sobre el botón
                return hov and click

            # Llamadas a draw_btn actualizadas
            if draw_btn(r_cont, pause_button_assets["cont_hover"]):
                play_click(assets_dir)
                paused = False
            elif draw_btn(r_restart, pause_button_assets["restart_hover"]):
                play_click(assets_dir)
                reset_level()
                paused = False
            elif draw_btn(r_menu, pause_button_assets["menu_hover"]):
                play_click(assets_dir)
                # === CAMBIO: Detener música ===
                stop_level_music()
                return None


        # =====================================================================
        # === CAMBIO 6: Condición de victoria ahora usa 'remaining_ms' ===
        # =====================================================================
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

            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 120, 0, 90))
            screen.blit(overlay, (0, 0))
            wtxt = big.render("¡Parque limpio!", True, (255, 255, 255))
            screen.blit(wtxt, wtxt.get_rect(center=(W // 2, H // 2 - 10)))
            pygame.display.flip()
            pygame.time.delay(1200)
            # === CAMBIO: Detener música ===
            stop_level_music()
            return {"estado": "completado", "recolectadas": total_trash}

        # Comprueba la derrota usando 'remaining_ms'
        if remaining_ms <= 0 and delivered < total_trash:
            # --- NUEVO: mostrar la pantalla de "LOSE" del usuario si existe ---
            stop_level_music()
            if pantalla_lose_img:
                try:
                    # escalar a pantalla completa manteniendo la proporción (fit & cover)
                    iw, ih = pantalla_lose_img.get_size()
                    ratio = max(W / iw, H / ih)  # cover-like to fill screen (keeps aspect but may crop)
                    new_w, new_h = int(iw * ratio), int(ih * ratio)
                    scaled = pygame.transform.smoothscale(pantalla_lose_img, (new_w, new_h))
                    rect = scaled.get_rect(center=(W//2, H//2))
                    screen.blit(scaled, rect)
                except Exception:
                    # fallback a mensaje de texto si algo falla
                    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 160))
                    screen.blit(overlay, (0, 0))
                    msg = big.render("¡Tiempo agotado!", True, (255, 255, 255))
                    screen.blit(msg, msg.get_rect(center=(W // 2, H // 2 - 10)))
            else:
                # Si no existe la imagen, usar el texto clásico
                overlay = pygame.Surface((W, H), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 160))
                screen.blit(overlay, (0, 0))
                msg = big.render("¡Tiempo agotado!", True, (255, 255, 255))
                screen.blit(msg, msg.get_rect(center=(W // 2, H // 2 - 10)))

            pygame.display.flip()
            pygame.time.delay(1200)
            # === CAMBIO: Detener música (ya detenida arriba) ===
            return {"estado": "tiempo_agotado", "recolectadas": delivered}

        pygame.display.flip()
