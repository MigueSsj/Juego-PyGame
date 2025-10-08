from __future__ import annotations
import pygame, math, random
from pathlib import Path
from typing import Optional

# ====== SFX click ======
_click_snd: pygame.mixer.Sound | None = None
def play_click(assets_dir: Path):
    global _click_snd
    if _click_snd is None:
        try:
            audio_dir = assets_dir / "msuiquita"
            for stem in ["musica_botoncitos", "click", "boton"]:
                for ext in (".ogg", ".wav", ".mp3"):
                    for p in list(audio_dir.glob(f"{stem}{ext}")) + list(audio_dir.glob(f"{stem}*{ext}")):
                        if not pygame.mixer.get_init(): pygame.mixer.init()
                        _click_snd = pygame.mixer.Sound(str(p))
                        _click_snd.set_volume(0.9)
                        break
                if _click_snd: break
        except Exception:
            _click_snd = None
    if _click_snd:
        try: _click_snd.play()
        except Exception: pass

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

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height() * r)))

def make_glow(radius: int) -> pygame.Surface:
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        a = max(5, int(180 * (r / radius) ** 2))
        pygame.draw.circle(s, (255, 255, 120, a), (radius, radius), r)
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

def load_char_frames(assets_dir: Path, target_h: int) -> dict[str, list[pygame.Surface]]:
    right = [load_surface(p) for p in find_many_by_prefix(assets_dir, "ecoguardian_walk_right")]
    left  = [load_surface(p) for p in find_many_by_prefix(assets_dir, "ecoguardian_walk_left")]
    if not right and not left:
        one = None
        for stem in ["ecoguardian_idle", "ecoguardian", "EcoGuardian", "eco_guardian", "guardian", "player", "personaje"]:
            p = find_by_stem(assets_dir, stem)
            if p:
                one = load_surface(p); break
        if not one:
            one = pygame.Surface((60, 90), pygame.SRCALPHA)
            pygame.draw.rect(one, (250, 210, 90), one.get_rect(), border_radius=6)
        left  = [pygame.transform.flip(one, True, False)]
        right = [one]
    if right and not left:
        left = [pygame.transform.flip(f, True, False) for f in right]
    if left and not right:
        right = [pygame.transform.flip(f, True, False) for f in left]
    def scale_list(lst): 
        return [pygame.transform.smoothscale(f, (int(f.get_width()*(target_h/f.get_height())), target_h)) for f in lst]
    return {"right": scale_list(right), "left": scale_list(left)}

# ---------- entidades ----------
class Player(pygame.sprite.Sprite):
    def __init__(self, frames: dict[str, list[pygame.Surface]], pos, bounds: pygame.Rect, speed: float = 320):
        super().__init__()
        self.frames = frames
        self.dir = "right"
        self.frame_idx = 0
        self.anim_timer = 0.0
        self.anim_speed = 0.12
        self.image = self.frames[self.dir][0]
        self.rect = self.image.get_rect(center=pos)
        self.speed = speed
        self.bounds = bounds

    def handle_input(self, dt: float):
        k = pygame.key.get_pressed()
        dx = dy = 0
        if k[pygame.K_a] or k[pygame.K_LEFT]:  dx -= 1
        if k[pygame.K_d] or k[pygame.K_RIGHT]: dx += 1
        if k[pygame.K_w] or k[pygame.K_UP]:    dy -= 1
        if k[pygame.K_s] or k[pygame.K_DOWN]:  dy += 1
        moving = (dx or dy)
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

# ---------- nivel principal ----------
def run(screen: pygame.Surface, assets_dir: Path, personaje: str = "EcoGuardian", dificultad: str = "Fácil"):
    pygame.font.init()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 26, bold=True)
    big  = pygame.font.SysFont("arial", 54, bold=True)

    W, H = screen.get_size()
    background = load_bg(assets_dir, W, H)

    # Botón back
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
    player = Player(frames, (int(W * 0.16), int(H * 0.75)), pygame.Rect(0, 0, W, H))

    carrying: Optional[Trash] = None
    delivered = 0

    PICK_KEYS = (pygame.K_e, pygame.K_RETURN)
    INTERACT_DIST = int(W * 0.055)

    paused = False
    t = 0.0

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
        dt = clock.tick(60) / 1000.0
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

            # mantener basura cargada
            if carrying:
                carrying.carried = True
                carrying.rect.center = (player.rect.centerx, player.rect.top + carrying.rect.height // 2 - 6)

            # Interacción recoger/depositar
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

        # PAUSA
        if paused:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            screen.blit(overlay, (0, 0))

            panel_w, panel_h = int(W * 0.52), int(H * 0.52)
            btn_w, btn_h = int(panel_w * 0.70), int(panel_h * 0.17)
            panel = pygame.Rect(W//2 - panel_w//2, H//2 - panel_h//2, panel_w, panel_h)
            pygame.draw.rect(screen, (30, 20, 15), panel, border_radius=16)
            inner = panel.inflate(-10, -10)
            pygame.draw.rect(screen, (210, 180, 140), inner, border_radius=14)

            title = big.render("PAUSA", True, (25, 20, 15))
            screen.blit(title, title.get_rect(midtop=(W//2, inner.top + 20)))

            cx = W // 2
            start_y = inner.top + int(panel_h * 0.28)
            gap = int(panel_h * 0.06)
            r_cont    = pygame.Rect(0, 0, btn_w, btn_h); r_cont.center    = (cx, start_y)
            r_restart = pygame.Rect(0, 0, btn_w, btn_h); r_restart.center = (cx, start_y + btn_h + gap)
            r_menu    = pygame.Rect(0, 0, btn_w, btn_h); r_menu.center    = (cx, start_y + (btn_h + gap) * 2)

            mouse = pygame.mouse.get_pos()
            click = pygame.mouse.get_pressed()[0]

            def draw_btn(rect: pygame.Rect, label: str) -> bool:
                hov = rect.collidepoint(mouse)
                pygame.draw.rect(screen, (30, 20, 15), rect, border_radius=16)
                pygame.draw.rect(screen, (225, 190, 145) if hov else (205, 170, 125),
                                 rect.inflate(-8, -8), border_radius=14)
                lbl = pygame.font.SysFont("arial", max(28, int(H * 0.03)), bold=True).render(label, True, (25, 20, 15))
                screen.blit(lbl, lbl.get_rect(center=rect.center))
                return hov and click

            if draw_btn(r_cont, "Continuar"):
                play_click(assets_dir)
                paused = False
            elif draw_btn(r_restart, "Reiniciar"):
                play_click(assets_dir)
                reset_level()
                paused = False
            elif draw_btn(r_menu, "Menú"):
                play_click(assets_dir)
                return None

        # VICTORIA
        if not paused and delivered >= total_trash:
            win = pygame.Surface((W, H), pygame.SRCALPHA)
            win.fill((0, 120, 0, 90))
            screen.blit(win, (0, 0))
            wtxt = big.render("¡Parque limpio!", True, (255, 255, 255))
            screen.blit(wtxt, wtxt.get_rect(center=(W // 2, H // 2 - 10)))
            pygame.display.flip()
            pygame.time.delay(1200)
            return {"estado": "completado", "recolectadas": total_trash}

        pygame.display.flip()
