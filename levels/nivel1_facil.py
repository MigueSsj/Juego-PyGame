# levels/nivel1_facil.py
from __future__ import annotations
import pygame, math, random, re
from pathlib import Path
from typing import Optional

# ====== SFX click (VOLÚMEN AJUSTABLE) ======
CLICK_VOL = 0.25   # <-- AJUSTA AQUÍ (0.0 = mudo, 1.0 = máximo)
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

def load_bg(assets_dir: Path, W: int, H: int) -> pygame.Surface:
    for stem in ["nivel1_parque", "parque_nivel1", "park_level1", "nivel1", "bg_parque", "nivel1_bg"]:
        p = find_by_stem(assets_dir, stem)
        if p:
            return pygame.transform.smoothscale(load_surface(p), (W, H))
    bg = pygame.Surface((W, H)); bg.fill((40, 120, 40))
    return bg

def load_trash_images(assets_dir: Path) -> list[pygame.Surface]:
    imgs: list[pygame.Surface] = []
    for p in find_many_by_prefix(assets_dir, "trash_"):
        s = load_surface(p)
        imgs.append(s.convert_alpha() if p.suffix.lower() == ".png" else s)
    return imgs


# === CARGA DE FRAMES DESDE /assets/PERSONAJE H/ ============================
def load_char_frames(assets_dir: Path, target_h: int) -> dict[str, list[pygame.Surface] | pygame.Surface]:
    """
    Carga animaciones desde: assets/PERSONAJE H/
    Walk: ecoguardian_walk_<dir>_1..4.png
    Idle opcional: ecoguardian_<dir>_idle.png (down/right/up; left se espeja si no existe)
    """
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

    if idle_right is None and right:
        idle_right = right[0]
    if idle_left is None and idle_right is not None:
        idle_left = pygame.transform.flip(idle_right, True, False)
    if idle_down is None and down:
        idle_down = down[0]
    if idle_up is None and up:
        idle_up = up[0]

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


# === NUEVO: punto de anclaje para llevar la basura (panza/manos) ==========
def _carry_anchor(player: pygame.sprite.Sprite, carrying: pygame.sprite.Sprite) -> tuple[int, int]:
    """
    Devuelve el punto (cx, cy) donde se sostiene la basura:
    a la altura de la panza/manos, con leve desplazamiento según dirección.
    """
    rect = player.rect
    cx, cy = rect.centerx, rect.centery

    # Altura panza/manos
    cy = rect.centery + int(rect.height * 0.08)

    # Ajuste según dirección
    d = getattr(player, "dir", "down")
    if d == "left":
        cx -= int(rect.width * 0.12)
    elif d == "right":
        cx += int(rect.width * 0.12)
    elif d == "up":
        cy -= int(rect.height * 0.02)
    else:  # down
        cy += int(rect.height * 0.02)

    return cx, cy


# ---------- NIVEL PRINCIPAL ----------
def run(screen: pygame.Surface, assets_dir: Path, personaje: str = "EcoGuardian", dificultad: str = "Fácil"):
    pygame.font.init()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 26, bold=True)
    big  = pygame.font.SysFont("arial", 54, bold=True)

    W, H = screen.get_size()
    background = load_bg(assets_dir, W, H)

    # Botón Back
    back_p = find_by_stem(assets_dir, "btn_back") or find_by_stem(assets_dir, "back")
    if back_p:
        back_img = load_surface(back_p).convert_alpha()
        back_img = scale_to_width(back_img, max(120, min(int(W * 0.12), 240)))
        back_rect = back_img.get_rect()
        back_rect.bottomleft = (10, H - 12)
    else:
        back_img = None
        back_rect = pygame.Rect(10, H - 60, 140, 50)

    # Basurero
    bin_p = (find_by_stem(assets_dir, "basurero")
             or find_by_stem(assets_dir, "bote_basura")
             or find_by_stem(assets_dir, "trash_bin"))
    if bin_p:
        bin_img = scale_to_width(load_surface(bin_p), int(W * 0.10))
    else:
        bin_img = pygame.Surface((int(W * 0.10), int(W * 0.12)), pygame.SRCALPHA)
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
    frames = load_char_frames(assets_dir, target_h=int(H * 0.16))
    player = Player(frames, (int(W * 0.16), int(H * 0.75)), pygame.Rect(0, 0, W, H), speed=320, anim_fps=8.0)

    carrying: Optional[Trash] = None
    delivered = 0

    PICK_KEYS = (pygame.K_e, pygame.K_RETURN)
    INTERACT_DIST = int(W * 0.055)

    paused = False
    t = 0.0

    # === CARGA UI PAUSA DESDE assets/PAUSA/ ===
    pausa_dir = assets_dir / "PAUSA"

    def _load_btn_img(stem: str, max_w: int, max_h: int):
        """Carga btn por stem desde assets/PAUSA con hover escalado."""
        p = find_by_stem(pausa_dir, stem)
        if not p:
            return None, None
        img = load_surface(p)
        s = img.copy()
        ratio = min(max_w / s.get_width(), max_h / s.get_height(), 1.0)
        s = pygame.transform.smoothscale(s, (int(s.get_width() * ratio), int(s.get_height() * ratio)))
        hs = pygame.transform.smoothscale(s, (int(s.get_width() * 1.08), int(s.get_height() * 1.08)))
        return s, hs

    # Panel/fondo de la pausa (tu imagen grande)
    pausa_panel_img = None
    for nm in ["nivelA 2", "panel_pausa", "pausa_panel"]:
        ptex = find_by_stem(pausa_dir, nm)
        if ptex:
            pausa_panel_img = load_surface(ptex)
            break

    # Diccionario con imágenes de botones
    pausa_imgs = {
        "continuar": {"base": None, "hover": None},  # "inicio lm"
        "reiniciar": {"base": None, "hover": None},  # "reinicio lm"
        "menu":      {"base": None, "hover": None},  # "house"
    }

    def reset_level():
        nonlocal trash_group, carrying, delivered
        trash_group.empty()
        for i in range(total_trash):
            x = random.randint(int(W * 0.18), int(W * 0.82))
            y = random.randint(int(H * 0.50), int(H * 0.86))
            img = sprite_trash[i % len(sprite_trash)]
            trash_group.add(Trash(img, (x, y), int(W * 0.035)))
        carrying = None
        delivered = 0

    while True:
        dt = min(clock.tick(60) / 1000.0, 0.033)
        t += dt
        interact = False

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return None
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    play_click(assets_dir)
                    return None
                if e.key == pygame.K_SPACE:
                    paused = not paused
                    play_click(assets_dir)
                if e.key in PICK_KEYS:
                    interact = True
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and back_img:
                if back_rect.collidepoint(e.pos):
                    play_click(assets_dir)
                    return None

        if not paused:
            player.handle_input(dt)

            if carrying:
                carrying.carried = True
                # === NUEVO: posición del objeto cargado a la altura de la panza/manos
                carrying.rect.center = _carry_anchor(player, carrying)

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
                    if d <= BIN_RADIUS * 1.2:
                        trash_group.remove(carrying)
                        carrying = None
                        delivered += 1

        # DIBUJO
        screen.blit(background, (0, 0))
        screen.blit(bin_img, bin_rect)
        for tr in trash_group:
            tr.draw(screen, t)
        screen.blit(player.image, player.rect)
        if carrying:
            screen.blit(carrying.image, carrying.rect)

        # HUD
        hud = [
            "Nivel 1 – El Parque (Fácil, sin tiempo)",
            "Mover: WASD/Flechas | Recoger/Depositar: E / Enter | Pausa: Espacio",
            f"Entregadas: {delivered} / {total_trash}",
        ]
        for i, line in enumerate(hud):
            screen.blit(font.render(line, True, (15, 15, 15)), (16, 12 + i * 26))

        # Back
        if back_img:
            screen.blit(back_img, back_rect)
        else:
            pygame.draw.rect(screen, (240, 240, 240), back_rect, border_radius=10)
            txt = font.render("Menú", True, (10, 10, 10))
            screen.blit(txt, txt.get_rect(center=back_rect.center))

        # === PAUSA (usa assets/PAUSA/) ===
        if paused:
            # oscurecer
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))

            # panel centrado
            panel_w, panel_h = int(W * 0.52), int(H * 0.52)
            panel = pygame.Rect(W//2 - panel_w//2, H//2 - panel_h//2, panel_w, panel_h)

            if pausa_panel_img:
                # Escalar tu imagen de panel para que ocupe el rectángulo
                panel_scaled = pygame.transform.smoothscale(pausa_panel_img, (panel_w, panel_h))
                screen.blit(panel_scaled, panel)
            else:
                # Fallback minimal
                pygame.draw.rect(screen, (30, 20, 15), panel, border_radius=16)
                inner = panel.inflate(-10, -10)
                pygame.draw.rect(screen, (210, 180, 140), inner, border_radius=14)

            # título (opcional)
            title = big.render("PAUSA", True, (25, 20, 15))
            screen.blit(title, title.get_rect(midtop=(W//2, panel.top + 20)))

            # Slots de botones
            btn_w, btn_h = int(panel_w * 0.70), int(panel_h * 0.17)
            cx = W // 2
            start_y = panel.top + int(panel_h * 0.28)
            gap = int(panel_h * 0.06)
            r_cont    = pygame.Rect(0, 0, btn_w, btn_h); r_cont.center    = (cx, start_y)
            r_restart = pygame.Rect(0, 0, btn_w, btn_h); r_restart.center = (cx, start_y + btn_h + gap)
            r_menu    = pygame.Rect(0, 0, btn_w, btn_h); r_menu.center    = (cx, start_y + (btn_h + gap) * 2)

            # Cargar imágenes de botones (una sola vez)
            if pausa_imgs["continuar"]["base"] is None:
                max_w = int(btn_w * 0.92)
                max_h = int(btn_h * 0.85)
                pausa_imgs["continuar"]["base"], pausa_imgs["continuar"]["hover"] = _load_btn_img("inicio lm", max_w, max_h)
                pausa_imgs["reiniciar"]["base"],  pausa_imgs["reiniciar"]["hover"]  = _load_btn_img("reinicio lm", max_w, max_h)
                pausa_imgs["menu"]["base"],       pausa_imgs["menu"]["hover"]       = _load_btn_img("house", max_w, max_h)

            mouse = pygame.mouse.get_pos()
            click = pygame.mouse.get_pressed()[0]

            def draw_btn(rect: pygame.Rect, key: str) -> bool:
                """Dibuja SOLO la imagen del botón centrada en su slot (sin cajas)."""
                hov = rect.collidepoint(mouse)
                img = pausa_imgs[key]["hover"] if hov and pausa_imgs[key]["hover"] else pausa_imgs[key]["base"]
                if img:
                    screen.blit(img, img.get_rect(center=rect.center))
                return hov and click

            if draw_btn(r_cont, "continuar"):
                play_click(assets_dir)
                paused = False
            elif draw_btn(r_restart, "reiniciar"):
                play_click(assets_dir)
                reset_level()
                paused = False
            elif draw_btn(r_menu, "menu"):
                play_click(assets_dir)
                return None

        # === VICTORIA (pantalla win_level1) ===
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
                elapsed = 0.0
                while elapsed < 2.5:
                    dt2 = clock.tick(60) / 1000.0
                    elapsed += dt2
                    for ev in pygame.event.get():
                        if ev.type == pygame.QUIT:
                            return {"estado": "completado", "recolectadas": total_trash}
                        if ev.type == pygame.KEYDOWN or (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1):
                            play_click(assets_dir)
                            return {"estado": "completado", "recolectadas": total_trash}
                return {"estado": "completado", "recolectadas": total_trash}

            # Fallback si no hay imagen de victoria
            win = pygame.Surface((W, H), pygame.SRCALPHA)
            win.fill((0, 120, 0, 90))
            screen.blit(win, (0, 0))
            wtxt = big.render("¡Parque limpio!", True, (255, 255, 255))
            screen.blit(wtxt, wtxt.get_rect(center=(W // 2, H // 2 - 10)))
            pygame.display.flip()
            pygame.time.delay(1200)
            return {"estado": "completado", "recolectadas": total_trash}

        pygame.display.flip()
