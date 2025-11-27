from __future__ import annotations
import pygame, sys, math, random, re
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
    def play_sfx(*args, **kwargs): pass

# === COLORES / CONSTANTES ===
BLANCO = (255, 255, 255)
NEGRO = (0, 0, 0)
VERDE = (0, 200, 0)
ROJO = (200, 0, 0)
NARANJA_DEBUG = (255, 100, 0)
CYAN_DEBUG = (0, 200, 200)
GRIS_PANEL = (50, 50, 50)

TIEMPO_REPARACION = 120      # ticks (~2s a 60fps)
TOTAL_MS = 50_000            # 50 segundos para este modo difícil
SUSPENSE_TIME_MS = 30_000    # 30s para poner en rojo (ajustado)

# --- HELPERS (búsqueda y carga de imágenes) ---
def find_by_stem(assets_dir: Path, stem: str) -> Optional[Path]:
    exts = (".png", ".jpg", ".jpeg")
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists():
            return p
    stem_low = stem.lower()
    candidates = []
    try:
        for p in assets_dir.iterdir():
            if not p.is_file(): continue
            if p.suffix.lower() not in exts: continue
            name_no_ext = p.stem.lower()
            if name_no_ext == stem_low or name_no_ext.startswith(stem_low):
                candidates.append(p)
    except FileNotFoundError:
        return None
    if candidates:
        return min(candidates, key=lambda p: len(p.name))
    try:
        for sub in assets_dir.iterdir():
            if not sub.is_dir(): continue
            for ext in exts:
                p = sub / f"{stem}{ext}"
                if p.exists(): return p
            for p in sub.iterdir():
                if not p.is_file(): continue
                if p.suffix.lower() not in exts: continue
                name_no_ext = p.stem.lower()
                if name_no_ext == stem_low or name_no_ext.startswith(stem_low):
                    candidates.append(p)
    except Exception:
        pass
    if candidates:
        return min(candidates, key=lambda p: len(p.name))
    return None

def load_image(assets_dir: Path, stems: List[str]) -> Optional[pygame.Surface]:
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            try:
                img = pygame.image.load(str(p))
                return img.convert_alpha() if p.suffix.lower() == ".png" else img.convert()
            except Exception as e:
                print(f"[DEBUG] Error cargando {p}: {e}")
    return None

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    if img.get_width() == 0:
        return pygame.Surface((new_w, new_w), pygame.SRCALPHA)
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height() * r)))

# === CARGA PERSONAJE (versión robusta normalizada) ===
def load_char_frames(char_dir: Path, target_h: int) -> dict[str, list[pygame.Surface] | pygame.Surface]:
    if not char_dir.exists():
        raise FileNotFoundError(f"No se encontró la carpeta '{char_dir}'")
    folder_name = char_dir.name.upper()
    if "M" in folder_name or "WOMAN" in folder_name:
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
            try:
                img = pygame.image.load(str(p))
                seq.append(img.convert_alpha() if p.suffix.lower() == ".png" else img.convert())
            except: pass
        return seq

    def _load_idle(name: str) -> Optional[pygame.Surface]:
        for ext in (".png", ".jpg", ".jpeg"):
            p = char_dir / f"{prefix}_{name}{ext}"
            if p.exists():
                try:
                    img = pygame.image.load(str(p))
                    return img.convert_alpha() if p.suffix.lower() == ".png" else img.convert()
                except: pass
        return None

    right = _load_seq("walk_right"); left = _load_seq("walk_left")
    down = _load_seq("walk_down"); up = _load_seq("walk_up")
    idle_right = _load_idle("right_idle"); idle_left = _load_idle("left_idle")
    idle_down = _load_idle("down_idle"); idle_up = _load_idle("up_idle")

    if right and not left: left = [pygame.transform.flip(f, True, False) for f in right]
    if left and not right: right = [pygame.transform.flip(f, True, False) for f in left]
    if not down: down = right[:1] if right else []
    if not up: up = right[:1] if right else []

    if idle_right is None and right: idle_right = right[0]
    if idle_left is None and idle_right is not None: idle_left = pygame.transform.flip(idle_right, True, False)
    if idle_down is None and down: idle_down = down[0]
    if idle_up is None and up: idle_up = up[0]

    def _scale(f: pygame.Surface) -> pygame.Surface:
        if f.get_height() == 0:
            return pygame.Surface((int(target_h*0.7), target_h), pygame.SRCALPHA)
        h = target_h
        w = int(f.get_width() * (h / f.get_height()))
        return pygame.transform.smoothscale(f, (w, h))

    def _normalize_to_max(f: pygame.Surface, max_w: int) -> pygame.Surface:
        canvas = pygame.Surface((max_w, target_h), pygame.SRCALPHA)
        rect = f.get_rect(midbottom=(max_w//2, target_h))
        canvas.blit(f, rect)
        return canvas

    right = [_scale(f) for f in right]
    left = [_scale(f) for f in left]
    down = [_scale(f) for f in down]
    up = [_scale(f) for f in up]
    placeholder = pygame.Surface((int(target_h * 0.7), target_h), pygame.SRCALPHA)
    scaled_idle_right = _scale(idle_right) if idle_right else placeholder
    scaled_idle_left = _scale(idle_left) if idle_left else placeholder
    scaled_idle_down = _scale(idle_down) if idle_down else placeholder
    scaled_idle_up = _scale(idle_up) if idle_up else placeholder

    all_frames = []
    for seq in [right, left, down, up]:
        all_frames.extend(seq)
    all_frames.extend([scaled_idle_right, scaled_idle_left, scaled_idle_down, scaled_idle_up])
    max_w = max((f.get_width() for f in all_frames), default=int(target_h * 0.7))

    right = [_normalize_to_max(f, max_w) for f in right]
    left = [_normalize_to_max(f, max_w) for f in left]
    down = [_normalize_to_max(f, max_w) for f in down]
    up = [_normalize_to_max(f, max_w) for f in up]

    idle_right = _normalize_to_max(scaled_idle_right, max_w)
    idle_left = _normalize_to_max(scaled_idle_left, max_w)
    idle_down = _normalize_to_max(scaled_idle_down, max_w)
    idle_up = _normalize_to_max(scaled_idle_up, max_w)

    return {
        "right": right, "left": left, "down": down, "up": up,
        "idle_right": idle_right, "idle_left": idle_left,
        "idle_down": idle_down, "idle_up": idle_up
    }

# === CLASES ===
class ToolItem(pygame.sprite.Sprite):
    def __init__(self, img: pygame.Surface, area_juego: pygame.Rect, center_pos: Tuple[int, int]):
        super().__init__()
        self.image = img
        self.rect = self.image.get_rect()
        self.area = area_juego
        self.glow_timer = 0.0
        self.rect.center = center_pos

    def respawn(self):
        self.rect.center = self.area.center

    def draw(self, screen):
        self.glow_timer += 0.15
        offset = math.sin(self.glow_timer) * 8
        glow_surf = pygame.Surface((80, 80), pygame.SRCALPHA)
        alpha = 150 + int(50*math.sin(self.glow_timer*2))
        pygame.draw.circle(glow_surf, (255, 255, 0, alpha), (40, 40), 35)
        draw_rect = self.rect.copy()
        draw_rect.y += int(offset)
        screen.blit(glow_surf, glow_surf.get_rect(center=draw_rect.center))
        screen.blit(self.image, draw_rect)

class Player(pygame.sprite.Sprite):
    def __init__(self, frames: dict[str, list[pygame.Surface] | pygame.Surface],
                 pos, bounds: pygame.Rect, speed: float = 320, anim_fps: float = 8.0):
        super().__init__()
        self.frames = frames
        self.dir = "down"
        self.frame_idx = 0
        self.anim_timer = 0.0
        self.anim_dt = 1.0 / max(1.0, anim_fps)

        start_img = self.frames.get("idle_down")
        if not isinstance(start_img, pygame.Surface):
            start_img = pygame.Surface((40, 60), pygame.SRCALPHA)

        self.image = start_img
        self.rect = self.image.get_rect(center=pos)
        self.speed = speed
        self.bounds = bounds
        self.prev_rect = self.rect.copy()
        self.has_tool = False
        self.carrying_image: Optional[pygame.Surface] = None

    def update(self, dt: float):
        """
        Movimiento con controles invertidos.
        Dirección visual corregida para que MIRE a donde realmente se mueve en pantalla.
        """
        # ✅ FORZADO A TRUE PARA CORREGIR IZQ / DER VISUAL
        FLIP_HORIZONTAL_FACING = True

        self.prev_rect = self.rect.copy()
        k = pygame.key.get_pressed()

        # Movimiento INVERTIDO (tecla -> movimiento opuesto)
        mx = 0; my = 0
        if k[pygame.K_a] or k[pygame.K_LEFT]:  mx = 1    # izquierda -> mover derecha
        if k[pygame.K_d] or k[pygame.K_RIGHT]: mx = -1   # derecha  -> mover izquierda
        if k[pygame.K_w] or k[pygame.K_UP]:    my = 1    # arriba   -> mover abajo
        if k[pygame.K_s] or k[pygame.K_DOWN]:  my = -1   # abajo    -> mover arriba

        is_moving = (mx != 0 or my != 0)
        if is_moving:
            # Normalizar
            l = math.hypot(mx, my)
            norm_x, norm_y = (mx / l, my / l) if l != 0 else (0, 0)

            # Aplicar movimiento
            self.rect.x += int(norm_x * self.speed * dt)
            self.rect.y += int(norm_y * self.speed * dt)
            self.rect.clamp_ip(self.bounds)

            # Desplazamiento real
            dx = self.rect.x - self.prev_rect.x
            dy = self.rect.y - self.prev_rect.y

            # ✅ Dirección visual CORREGIDA
            if abs(dx) >= abs(dy):
                if dx > 0:
                    self.dir = "left" if FLIP_HORIZONTAL_FACING else "right"
                elif dx < 0:
                    self.dir = "right" if FLIP_HORIZONTAL_FACING else "left"
            else:
                if dy > 0:
                    self.dir = "down"
                elif dy < 0:
                    self.dir = "up"

            # Animación
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
            if isinstance(img, pygame.Surface):
                self.image = img
            else:
                seq = self.frames.get(self.dir, [])
                if seq:
                    self.image = seq[0]
            self.frame_idx = 0


    def _get_carry_anchor(self) -> tuple[int, int]:
        rect = self.rect
        cx, cy = rect.centerx, rect.centery
        cy = rect.centery + int(rect.height * 0.22)
        if self.dir == "left":
            cx -= int(rect.width * 0.12); cy += int(rect.height * 0.02)
        elif self.dir == "right":
            cx += int(rect.width * 0.12); cy += int(rect.height * 0.02)
        elif self.dir == "up":
            cy += int(rect.height * 0.06)
        else:
            cy += int(rect.height * 0.04)
        return cx, cy

    def draw(self, surf: pygame.Surface):
        surf.blit(self.image, self.rect)
        if self.carrying_image:
            cx, cy = self._get_carry_anchor()
            anchor_rect = self.carrying_image.get_rect(center=(cx, cy))
            surf.blit(self.carrying_image, anchor_rect)
        if self.has_tool and not self.carrying_image:
            pygame.draw.circle(surf, (0, 0, 255), (self.rect.centerx, self.rect.top - 15), 8)
            pygame.draw.circle(surf, (255, 255, 255), (self.rect.centerx, self.rect.top - 15), 8, 2)

# === FUNCIÓN PRINCIPAL (Nivel Difícil) ===
def run(screen: pygame.Surface, assets_dir: Path, personaje: str = "PERSONAJE H", dificultad: str = "Difícil"):
    print(f"--- [DEBUG] Nivel 3 (Difícil) iniciado. Personaje: {personaje} ---")
    W, H = screen.get_size()
    clock = pygame.time.Clock()

    # --- Fondos ---
    bg_roto = load_image(assets_dir, ["original", "background_broken"])
    if not bg_roto:
        bg_roto = pygame.Surface((W,H)); bg_roto.fill(NARANJA_DEBUG)
    bg_roto = pygame.transform.scale(bg_roto, (W, H))

    bg_todo = load_image(assets_dir, ["img_4_todo", "background_repaired"])
    if not bg_todo:
        bg_todo = pygame.Surface((W,H)); bg_todo.fill((100, 200, 100))
    bg_todo = pygame.transform.scale(bg_todo, (W, H))

    # --- Herramienta ---
    raw_img_tool = load_image(assets_dir, ["herramienta", "tool", "martillo", "wrench"])
    if not raw_img_tool:
        raw_img_tool = pygame.Surface((40,40), pygame.SRCALPHA); raw_img_tool.fill((0,0,255))
    img_tool = scale_to_width(raw_img_tool, 60)

    # --- UI Fonts ---
    pygame.font.init()
    font_hud = pygame.font.SysFont("Arial", 22, bold=True)
    font_timer = pygame.font.SysFont("Arial", 36, bold=True)
    font_big = pygame.font.SysFont("Arial", 48, bold=True)
    font_count = pygame.font.SysFont("Arial", 30, bold=True)

    # --- Cargar paneles HUD ---
    contador_panel_img = load_image(assets_dir, ["contador_edificios", "contador", "panel_contador", "panel_reparacion"])
    timer_panel_img = load_image(assets_dir, ["temporizador", "timer_panel", "panel_tiempo", "TEMPORIZADOR", "TEMPORAZIDOR"])
    pausa_panel_img = load_image(assets_dir / "PAUSA", ["nivelA 2", "panel_pausa", "pausa_panel"])
    if pausa_panel_img is None:
        pausa_panel_img = load_image(assets_dir, ["nivelA 2", "panel_pausa", "pausa_panel"])

    # pausa button assets (lazy)
    pause_button_assets = {"cont_base": None, "cont_hover": None, "restart_base": None, "restart_hover": None, "menu_base": None, "menu_hover": None}

    # --- Zonas y jugador ---
    zones = {
        "TL": pygame.Rect(0, 0, W//4, H//2 - 50),
        "TM": pygame.Rect(W//4, 0, W//4, H//2 - 50),
        "BL": pygame.Rect(0, H//2 + 20, W//2, H//2 - 50),
        "BR": pygame.Rect(W*2//3 + 80, H//2 + 40 - 30, W//3 - 80, H//2 - 50)
    }
    repaired_status = {k: False for k in zones}
    TOTAL_ZONES = len(zones)

    try:
        ruta_personaje = assets_dir / personaje
        char_frames = load_char_frames(ruta_personaje, int(H*0.12))
    except FileNotFoundError:
        char_frames = {"right": [], "left": [], "down": [], "up": [], "idle_right": None, "idle_left": None, "idle_down": None, "idle_up": None}
    player = Player(char_frames, (W//2, H//2), screen.get_rect().inflate(-50, -50), speed=340)

    tool_item = ToolItem(img_tool, screen.get_rect().inflate(-100, -100), (W//2, H//2 + 100))

    # --- Estado del juego ---
    remaining_ms = TOTAL_MS
    repair_progress = 0
    current_repairing = None
    victory = False; game_over = False; paused = False
    msg_text = ""; msg_timer = 0
    suspense_started = False
    num_edificios_reparados = 0

    start_level_music(assets_dir)

    def show_msg(txt):
        nonlocal msg_text, msg_timer
        msg_text = txt; msg_timer = 2.0

    def reset_level():
        nonlocal repaired_status, repair_progress, current_repairing, victory, game_over
        nonlocal paused, remaining_ms, suspense_started, num_edificios_reparados
        repaired_status = {k: False for k in zones}
        repair_progress = 0
        current_repairing = None
        victory = False
        game_over = False
        paused = False
        remaining_ms = TOTAL_MS
        suspense_started = False
        num_edificios_reparados = 0
        player.rect.center = (W//2, H//2)
        player.has_tool = False
        player.carrying_image = None
        tool_item.respawn()
        start_level_music(assets_dir)

    # --- Bucle principal ---
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        ms = int(dt * 1000)

        mouse_click = False
        mouse_pos = pygame.mouse.get_pos()

        for e in pygame.event.get():
            if e.type == pygame.QUIT: stop_level_music(); return "quit"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mouse_click = True
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: stop_level_music(); return "menu"
                if e.key == pygame.K_SPACE:
                    paused = not paused
                    if paused:
                        play_sfx("sfx_pause", assets_dir)
                    else:
                        play_sfx("sfx_click", assets_dir)

                if not paused and not game_over and not victory:
                    if e.key == pygame.K_e or e.key == pygame.K_RETURN:
                        if not player.has_tool:
                            if player.rect.colliderect(tool_item.rect.inflate(40, 40)):
                                player.has_tool = True
                                w_hand = max(18, player.rect.width // 3)
                                player.carrying_image = scale_to_width(raw_img_tool, w_hand)
                                play_sfx("sfx_pick_seed", assets_dir)
                                show_msg("¡Herramienta obtenida!")
                            else:
                                if msg_timer <= 0: show_msg("Presiona [E] cerca de la herramienta para recogerla.")
                        else:
                            show_msg("Ya tienes una herramienta")

        if not paused and not game_over and not victory:
            remaining_ms -= ms
            if remaining_ms <= 0:
                game_over = True
                stop_level_music()

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
                        player.carrying_image = None
                        play_sfx("sfx_plant", assets_dir)
                        num_edificios_reparados = sum(repaired_status.values())
                        if all(repaired_status.values()):
                            victory = True
                            stop_level_music()
                        else:
                            tool_item.respawn()
                            show_msg("¡Zona Reparada! Encuentra la herramienta de nuevo.")
                else:
                    if msg_timer <= 0: show_msg("¡Necesitas la herramienta!")
            else:
                repair_progress = 0; current_repairing = None

            if msg_timer > 0: msg_timer -= dt

        # --- DIBUJO ---
        screen.blit(bg_roto, (0, 0))
        for k, is_fixed in repaired_status.items():
            if is_fixed: screen.blit(bg_todo, zones[k], area=zones[k])

        if not player.has_tool and not victory:
            tool_item.draw(screen)
            if player.rect.colliderect(tool_item.rect.inflate(60,60)):
                txt = font_big.render("E", True, BLANCO)
                pygame.draw.rect(screen, NEGRO, (tool_item.rect.centerx-15, tool_item.rect.top-40, 30, 35), border_radius=5)
                screen.blit(txt, txt.get_rect(center=(tool_item.rect.centerx, tool_item.rect.top-25)))

        player.draw(screen)

        if current_repairing:
            bx = player.rect.centerx - 30; by = player.rect.top - 50
            pygame.draw.rect(screen, NEGRO, (bx, by, 60, 10), border_radius=3)
            pct = repair_progress / TIEMPO_REPARACION
            pygame.draw.rect(screen, VERDE, (bx+1, by+1, 58*pct, 8), border_radius=3)
            r_txt = font_hud.render("[R]", True, BLANCO)
            screen.blit(r_txt, r_txt.get_rect(center=(player.rect.centerx, by-15)))

        if player.has_tool and not current_repairing:
            for k, rect in zones.items():
                if not repaired_status[k]:
                    if player.rect.colliderect(rect):
                        tr = font_big.render("[R]", True, BLANCO)
                        bg_r = pygame.Rect(0, 0, tr.get_width() + 10, tr.get_height() + 5)
                        bg_r.center = rect.center
                        overlay = pygame.Surface((bg_r.width, bg_r.height), pygame.SRCALPHA)
                        overlay.fill((0, 0, 0, 150))
                        screen.blit(overlay, bg_r.topleft)
                        screen.blit(tr, tr.get_rect(center=rect.center))

        # -----------------------------
        # HUD (versión fácil reutilizada)
        # -----------------------------
        if not victory and not game_over:
            num_edificios_reparados = sum(repaired_status.values())

            panel_w = int(W * 0.18); panel_h = int(H * 0.11)
            margin_x = int(W * 0.04)
            margin_y = int(H * 0.04)

            counter_panel_rect = pygame.Rect(margin_x, margin_y, panel_w, panel_h)
            if contador_panel_img:
                scaled = pygame.transform.smoothscale(contador_panel_img, (counter_panel_rect.w, counter_panel_rect.h))
                screen.blit(scaled, counter_panel_rect.topleft)
            else:
                pygame.draw.rect(screen, (30, 20, 15), counter_panel_rect, border_radius=10)
                inner = counter_panel_rect.inflate(-10, -10)
                pygame.draw.rect(screen, (210, 180, 140), inner, border_radius=8)

            count_str = f"{num_edificios_reparados}/{TOTAL_ZONES}"
            txt_count_big = font_timer.render(count_str, True, NEGRO)
            sh_count_big = font_timer.render(count_str, True, (20, 15, 10))
            cx = counter_panel_rect.centerx; cy = counter_panel_rect.centery
            screen.blit(sh_count_big, sh_count_big.get_rect(center=(cx + 2, cy + 2)))
            screen.blit(txt_count_big, txt_count_big.get_rect(center=(cx, cy)))

            panel_rect = pygame.Rect(W - margin_x - panel_w, margin_y, panel_w, panel_h)
            if timer_panel_img:
                scaled = pygame.transform.smoothscale(timer_panel_img, (panel_rect.w, panel_rect.h))
                screen.blit(scaled, panel_rect.topleft)
            else:
                pygame.draw.rect(screen, (30, 20, 15), panel_rect, border_radius=10)
                inner = panel_rect.inflate(-10, -10)
                pygame.draw.rect(screen, (210, 180, 140), inner, border_radius=8)

            mm = (remaining_ms // 1000) // 60; ss = (remaining_ms // 1000) % 60
            time_str = f"{mm}:{ss:02d}"
            color_timer = ROJO if remaining_ms <= SUSPENSE_TIME_MS else (20, 15, 10)
            txt = font_timer.render(time_str, True, color_timer)
            sh = font_timer.render(time_str, True, (0, 0, 0))
            cx2 = panel_rect.centerx; cy2 = panel_rect.centery
            screen.blit(sh, sh.get_rect(center=(cx2 + 2, cy2 + 2)))
            screen.blit(txt, txt.get_rect(center=(cx2, cy2)))

            hud_help = "Reparar: [R] | Herramienta: [E] | Pausa: [ESPACIO]"
            help_txt_shadow = font_hud.render(hud_help, True, NEGRO)
            help_txt = font_hud.render(hud_help, True, BLANCO)
            screen.blit(help_txt_shadow, (15, H - 35))
            screen.blit(help_txt, (13, H - 37))

            if msg_timer > 0:
                m_surf = font_big.render(msg_text, True, BLANCO); s_surf = font_big.render(msg_text, True, NEGRO)
                center = (W//2, H//4); m_rect = m_surf.get_rect(center=center)
                screen.blit(s_surf, (m_rect.x+2, m_rect.y+2)); screen.blit(m_surf, m_rect)

        # --- PANTALLAS FINALES ---
        if victory:
            win_img = load_image(assets_dir, ["win_level3", "victory_screen"])
            if win_img:
                win_img = pygame.transform.scale(win_img, (W,H))
                screen.blit(win_img, (0,0))
            else:
                overlay = pygame.Surface((W, H), pygame.SRCALPHA); overlay.fill((0, 150, 0, 170))
                screen.blit(overlay, (0,0))
                v_surf = font_big.render("¡PLAZA REPARADA!", True, VERDE)
                screen.blit(v_surf, v_surf.get_rect(center=(W//2, H//2)))
            pygame.display.flip(); pygame.time.wait(2000)
            return "menu"

        if game_over:
            lose_img = load_image(assets_dir, ["lose_level3", "defeat_screen"])
            if lose_img:
                lose_img = pygame.transform.scale(lose_img, (W,H))
                screen.blit(lose_img, (0,0))
            else:
                overlay = pygame.Surface((W, H), pygame.SRCALPHA); overlay.fill((150, 0, 0, 170))
                screen.blit(overlay, (0,0))
                l_surf = font_big.render("¡TIEMPO AGOTADO!", True, ROJO)
                screen.blit(l_surf, l_surf.get_rect(center=(W//2, H//2)))
            pygame.display.flip(); pygame.time.wait(2000)
            return "menu"

        # --- PAUSA (MENÚ INTERACTIVO COPIADO DEL NIVEL FACIL) ---
        if paused:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA); overlay.fill((0, 0, 0, 170))
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
            y_cont = panel2.top + int(panel_h2 * 0.40)
            y_restart = panel2.top + int(panel_h2 * 0.60)
            y_menu = panel2.top + int(panel_h2 * 0.80)
            r_cont = pygame.Rect(0, 0, btn_w, btn_h); r_cont.center = (cx, y_cont)
            r_restart = pygame.Rect(0, 0, btn_w, btn_h); r_restart.center = (cx, y_restart)
            r_menu = pygame.Rect(0, 0, btn_w, btn_h); r_menu.center = (cx, y_menu)

            # Carga perezosa de las texturas de botones desde panel_scaled (si existe)
            if pause_button_assets["cont_base"] is None and panel_scaled:
                try:
                    r_cont_local = pygame.Rect(r_cont.x - panel2.x, r_cont.y - panel2.y, r_cont.w, r_cont.h)
                    r_restart_local = pygame.Rect(r_restart.x - panel2.x, r_restart.y - panel2.y, r_restart.w, r_restart.h)
                    r_menu_local = pygame.Rect(r_menu.x - panel2.x, r_menu.y - panel2.y, r_menu.w, r_menu.h)

                    base_cont = panel_scaled.subsurface(r_cont_local)
                    base_restart = panel_scaled.subsurface(r_restart_local)
                    base_menu = panel_scaled.subsurface(r_menu_local)

                    pause_button_assets["cont_base"] = base_cont
                    pause_button_assets["restart_base"] = base_restart
                    pause_button_assets["menu_base"] = base_menu

                    hover_w, hover_h = int(r_cont.w * 1.05), int(r_cont.h * 1.05)
                    pause_button_assets["cont_hover"] = pygame.transform.smoothscale(base_cont, (hover_w, hover_h))
                    pause_button_assets["restart_hover"] = pygame.transform.smoothscale(base_restart, (hover_w, hover_h))
                    pause_button_assets["menu_hover"] = pygame.transform.smoothscale(base_menu, (hover_w, hover_h))
                except Exception:
                    pause_button_assets["cont_base"] = pygame.Surface((1,1), pygame.SRCALPHA)

            def draw_btn(base_rect: pygame.Rect, hover_img: Optional[pygame.Surface], base_img: Optional[pygame.Surface]) -> bool:
                hov = base_rect.collidepoint(mouse_pos)
                img_to_blit = hover_img if hov and hover_img else (base_img if base_img else None)
                if img_to_blit and img_to_blit.get_size() != (1, 1):
                    img_rect = img_to_blit.get_rect(center=base_rect.center)
                    screen.blit(img_to_blit, img_rect)
                if img_to_blit is None or img_to_blit.get_size() == (1, 1):
                    color = (200, 200, 200) if hov else (150, 150, 150)
                    pygame.draw.rect(screen, color, base_rect, border_radius=8)
                    text = font_hud.render("Continuar" if base_rect == r_cont else ("Reiniciar" if base_rect == r_restart else "Menú"), True, NEGRO)
                    screen.blit(text, text.get_rect(center=base_rect.center))
                return hov and mouse_click

            # Botones reacciona a click (mouse_click seteado arriba cuando hubo MOUSEBUTTONDOWN)
            if draw_btn(r_cont, pause_button_assets["cont_hover"], pause_button_assets["cont_base"]):
                play_sfx("sfx_click", assets_dir)
                paused = False
            elif draw_btn(r_restart, pause_button_assets["restart_hover"], pause_button_assets["restart_base"]):
                play_sfx("sfx_click", assets_dir)
                reset_level()
            elif draw_btn(r_menu, pause_button_assets["menu_hover"], pause_button_assets["menu_base"]):
                play_sfx("sfx_click", assets_dir)
                stop_level_music()
                return "menu"

        pygame.display.flip()

    return "menu"

# === BOILERPLATE EJECUTABLE ===
if __name__ == "__main__":
    pygame.init()
    SCRIPT_DIR = Path(sys.argv[0]).parent
    ASSETS_PATH = SCRIPT_DIR / "assets"
    if not ASSETS_PATH.exists():
        ASSETS_PATH = SCRIPT_DIR

    SCREEN_WIDTH, SCREEN_HEIGHT = 1024, 768
    SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Nivel 3: Misión Crítica - Difícil")

    # DEBUG: listar assets primer nivel
    print("[DEBUG] Archivos en assets (primer nivel):")
    try:
        for p in ASSETS_PATH.iterdir():
            print("  -", p.name)
    except Exception as e:
        print("[DEBUG] error listando assets:", e)

    # DEBUG: ver si encuentra los panels clave
    def dbg(name):
        p = find_by_stem(ASSETS_PATH, name)
        print(f"[DEBUG] buscar '{name}' ->", p if p else "NO ENCONTRADO")
    dbg("contador_edificios")
    dbg("temporizador")
    dbg("TEMPORIZADOR")

    result = run(SCREEN, ASSETS_PATH, personaje="PERSONAJE H")
    print(f"--- [DEBUG] run terminó con: {result} ---")
    pygame.quit()
    sys.exit()
