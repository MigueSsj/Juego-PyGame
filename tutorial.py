from __future__ import annotations
import pygame, math, re
from pathlib import Path
from typing import Optional, List

# === Importar funciones de música (si existen) ===
try:
    from audio_shared import play_sfx, start_level_music, stop_level_music
except ImportError:
    def play_sfx(*args, **kwargs): pass
    def start_level_music(assets_dir: Path): pass
    def stop_level_music(): pass

# ==========================================
# === FUNCIONES DE CARGA ===
# ==========================================
def find_by_stem(assets_dir: Path, stem: str) -> Optional[Path]:
    exts = (".png", ".jpg", ".jpeg")
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists(): return p
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{stem}*{ext}"))
    return min(cands, key=lambda p: len(p.name)) if cands else None

def load_image(assets_dir: Path, stems: List[str], fallback_color=(100,100,100)) -> pygame.Surface:
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            try:
                img = pygame.image.load(str(p))
                return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
            except Exception:
                pass
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.circle(s, fallback_color, (32,32), 30)
    return s

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    if img.get_width() == 0: return img
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height() * r)))

# ==========================================
# === CLASES DEL JUEGO ===
# ==========================================

class TutorialItem(pygame.sprite.Sprite):
    def __init__(self, x, y, img, kind):
        super().__init__()
        self.image = img
        self.rect = self.image.get_rect(center=(x, y))
        self.start_pos = (x, y)
        self.kind = kind
        self.carried = False
        self.completed = False
        # Glow más grande
        self.glow = pygame.Surface((self.rect.width + 60, self.rect.height + 60), pygame.SRCALPHA)
        pygame.draw.circle(self.glow, (255, 255, 150, 100), (self.glow.get_width()//2, self.glow.get_height()//2), self.glow.get_width()//2)

    def reset(self):
        self.rect.center = self.start_pos
        self.carried = False
        self.completed = False

    def draw(self, screen, t):
        if not self.completed:
            if not self.carried:
                off = math.sin(t * 5) * 5
                r = self.rect.copy()
                r.y += int(off)
                screen.blit(self.glow, self.glow.get_rect(center=r.center))
                screen.blit(self.image, r)
            else:
                screen.blit(self.image, self.rect)

class TutorialTarget(pygame.sprite.Sprite):
    def __init__(self, x, y, img_normal, img_done, kind, align_bottom=False):
        super().__init__()
        self.image_normal = img_normal
        self.image_done = img_done
        self.image = self.image_normal
        
        # Definir posición inicial
        self.rect = self.image.get_rect()
        if align_bottom:
            self.rect.midbottom = (x, y) # Usar el punto inferior para alinear suelo
        else:
            self.rect.center = (x, y)
            
        self.kind = kind
        self.done = False
        
        # Guardar puntos de referencia para mantener posición al cambiar imagen
        self.pos_center = self.rect.center
        self.pos_midbottom = self.rect.midbottom 
        self.align_bottom = align_bottom

    def complete(self):
        self.done = True
        self.image = self.image_done
        # Recalcular rect mantieniendo la posición correcta
        if self.align_bottom:
            self.rect = self.image.get_rect(midbottom=self.pos_midbottom)
        else:
            self.rect = self.image.get_rect(center=self.pos_center)

# ==========================================
# === JUGADOR ===
# ==========================================
def load_char_frames(assets_dir: Path, target_h: int, *, char_folder: str = "PERSONAJE H") -> dict[str, list[pygame.Surface] | pygame.Surface]:
    char_dir = assets_dir / char_folder
    if not char_dir.exists():
        alt = "PERSONAJE M" if "H" in char_folder else "PERSONAJE H"
        if (assets_dir / alt).exists(): char_dir = assets_dir / alt
    
    prefix = "womanguardian" if "M" in char_folder.upper() or "WOMAN" in char_folder.upper() else "ecoguardian"

    def _load_seq(name: str) -> list[pygame.Surface]:
        files = []
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

    right = _load_seq("walk_right"); left  = _load_seq("walk_left")
    down  = _load_seq("walk_down");  up    = _load_seq("walk_up")
    idle_right = _load_idle("right_idle"); idle_left  = _load_idle("left_idle")
    idle_down  = _load_idle("down_idle");  idle_up    = _load_idle("up_idle")

    if right and not left: left = [pygame.transform.flip(f, True, False) for f in right]
    if left and not right: right = [pygame.transform.flip(f, True, False) for f in left]
    if not down: down = right[:1] if right else []
    if not up:   up   = right[:1] if right else []

    if idle_right is None and right: idle_right = right[0]
    if idle_left  is None and idle_right is not None: idle_left = pygame.transform.flip(idle_right, True, False)
    if idle_down  is None and down:  idle_down = down[0]
    if idle_up    is None and up:    idle_up   = up[0]

    def _scale(f: pygame.Surface) -> pygame.Surface:
        if f.get_height() == 0: return pygame.Surface((int(target_h*0.7), target_h), pygame.SRCALPHA)
        h = target_h
        w = int(f.get_width() * (h / f.get_height()))
        return pygame.transform.smoothscale(f, (w, h))

    def _normalize_list(seq: list[pygame.Surface]) -> list[pygame.Surface]:
        if not seq: return seq
        max_w = max(f.get_width() for f in seq)
        H = seq[0].get_height()
        out = []
        for f in seq:
            c = pygame.Surface((max_w, H), pygame.SRCALPHA)
            rect = f.get_rect(midbottom=(max_w//2, H))
            c.blit(f, rect)
            out.append(c)
        return out

    def _normalize_single(s: pygame.Surface | None) -> pygame.Surface | None:
        if s is None:
             h = target_h
             w = int(h * 0.7)
             return pygame.Surface((w, h), pygame.SRCALPHA)
        S = _scale(s)
        c = pygame.Surface((S.get_width(), S.get_height()), pygame.SRCALPHA)
        c.blit(S, S.get_rect(midbottom=(c.get_width()//2, c.get_height())))
        return c

    right = _normalize_list([_scale(f) for f in right])
    left  = _normalize_list([_scale(f) for f in left])
    down  = _normalize_list([_scale(f) for f in down])
    up    = _normalize_list([_scale(f) for f in up])

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
    def __init__(self, frames, pos, bounds, speed=300, anim_fps=8.0):
        super().__init__()
        self.frames = frames
        self.dir = "down"
        self.frame_idx = 0
        self.anim_timer = 0.0
        self.anim_dt = 1.0 / max(1.0, anim_fps)
        
        idle = self.frames.get("idle_down")
        if isinstance(idle, pygame.Surface): start_img = idle
        elif self.frames.get("down"): start_img = self.frames["down"][0]
        else: start_img = pygame.Surface((40,60), pygame.SRCALPHA)
            
        self.image = start_img 
        self.rect = self.image.get_rect(center=pos)
        self.speed = speed
        self.bounds = bounds
        self.carrying_item = None

    def handle_input(self, dt):
        k = pygame.key.get_pressed()
        dx = (k[pygame.K_d] or k[pygame.K_RIGHT]) - (k[pygame.K_a] or k[pygame.K_LEFT])
        dy = (k[pygame.K_s] or k[pygame.K_DOWN])  - (k[pygame.K_w] or k[pygame.K_UP])
        moving = (dx != 0 or dy != 0)

        if moving:
            l = math.hypot(dx, dy);  dx, dy = dx / l, dy / l
            if abs(dx) >= abs(dy): self.dir = "left" if dx > 0 else "right"
            else: self.dir = "down" if dy > 0 else "up"
            
            self.rect.x += int(dx * self.speed * dt)
            self.rect.y += int(dy * self.speed * dt)
            self.rect.clamp_ip(self.bounds)
            
            self.anim_timer += dt
            if self.anim_timer >= self.anim_dt:
                self.anim_timer -= self.anim_dt
                seq = self.frames.get(self.dir, []) 
                if seq: self.frame_idx = (self.frame_idx + 1) % len(seq)
            seq = self.frames.get(self.dir, []) 
            if seq: self.image = seq[self.frame_idx % len(seq)]
        else:
            ik = f"idle_{self.dir}"
            img = self.frames.get(ik)
            if isinstance(img, pygame.Surface):
                self.image = img
            elif self.frames.get(self.dir):
                self.image = self.frames[self.dir][0]
            self.frame_idx = 0
        
        new_midbottom = self.rect.midbottom
        self.rect = self.image.get_rect(midbottom=new_midbottom)
        self.rect.clamp_ip(self.bounds)
        
        if self.carrying_item:
            self.carrying_item.rect.center = (self.rect.centerx, self.rect.centery - 60)

    def draw(self, screen):
        screen.blit(self.image, self.rect)

# ==========================================
# === FUNCIÓN PRINCIPAL DEL TUTORIAL ===
# ==========================================
def run(screen: pygame.Surface, assets_dir: Path, personaje: str = "EcoGuardian"):
    clock = pygame.time.Clock()
    W, H = screen.get_size()
    
    pygame.font.init()
    font_hud = pygame.font.SysFont("arial", 26, bold=True)
    
    pixel_font_path = find_by_stem(assets_dir, "pixel") or find_by_stem(assets_dir, "press_start")
    if pixel_font_path:
        font_label = pygame.font.Font(str(pixel_font_path), 20)
        font_e = pygame.font.Font(str(pixel_font_path), 30)
    else:
        font_label = pygame.font.SysFont("arial", 24, bold=True)
        font_e = pygame.font.SysFont("arial", 40, bold=True)

    # --- CARGAR IMÁGENES ---
    
    # Nivel 1: Basura y Bote (GIGANTE)
    img_basura = scale_to_width(load_image(assets_dir, ["trash_lata", "trash_1", "basura"], (100,100,100)), 60)
    img_bote = scale_to_width(load_image(assets_dir, ["basurero", "bote_basura", "trash_bin"], (50,50,50)), 180) # 180px
    
    # Nivel 2: Semilla y Árbol
    img_semilla = scale_to_width(load_image(assets_dir, ["n2_semilla", "semilla"], (139,69,19)), 60)
    img_hoyo = scale_to_width(load_image(assets_dir, ["n2_hoyo", "hoyo"], (30,30,30)), 80)
    img_arbol = scale_to_width(load_image(assets_dir, ["n2_arbol", "arbol"], (0,100,0)), 160)

    # Nivel 3: Herramienta y Reparación
    img_herramienta = scale_to_width(load_image(assets_dir, ["herramienta", "tool", "martillo", "wrench"], (0,0,255)), 60)
    img_roto = load_image(assets_dir, ["grieta", "crack", "roto", "original"], (100,0,0))
    if img_roto.get_width() == 64: 
        s = pygame.Surface((100, 100)); s.fill((150, 150, 150)); pygame.draw.line(s, (50,0,0), (10,10), (90,90), 8); pygame.draw.line(s, (50,0,0), (90,10), (10,90), 8); img_roto = s
    else: img_roto = scale_to_width(img_roto, 100)
    
    img_reparado = pygame.Surface(img_roto.get_size()); img_reparado.fill((100, 200, 100))
    pygame.draw.rect(img_reparado, (255,255,255), img_reparado.get_rect(), 6)

    # Palomita
    img_check = scale_to_width(load_image(assets_dir, ["basurita_entregada", "check", "palomita", "ok"], (0,255,0)), 80)
    
    # Botón Back (Más grande y abajo a la izquierda)
    img_back_raw = load_image(assets_dir, ["btn_back", "flecha_atras", "back", "volver"], (200,50,50))
    img_back = scale_to_width(img_back_raw, 100) # Tamaño grande 100px
    # Posición: Abajo a la izquierda con margen
    rect_back = img_back.get_rect(bottomleft=(30, H - 30))

    # Personaje
    frames = load_char_frames(assets_dir, 130, char_folder=personaje)
    player = Player(frames, (W//2, H - 150), screen.get_rect())

    # --- ESCENARIO ---
    col_w = W // 3
    y_items = H//2 + 100
    
    # Suelo de los objetivos (alineados visualmente)
    y_floor_targets = H//2 + 20 

    # 1. Basura -> Bote (alineado al suelo)
    item1 = TutorialItem(col_w * 0.5 - 80, y_items, img_basura, "basura")
    target1 = TutorialTarget(col_w * 0.5 + 80, y_floor_targets, img_bote, img_bote, "basura", align_bottom=True)
    
    # 2. Semilla -> Árbol (alineado al suelo para que crezca hacia arriba)
    item2 = TutorialItem(col_w * 1.5 - 80, y_items, img_semilla, "semilla")
    target2 = TutorialTarget(col_w * 1.5 + 80, y_floor_targets, img_hoyo, img_arbol, "semilla", align_bottom=True)
    
    # 3. Reparar (alineado al centro o suelo, usaremos centro para la grieta)
    item3 = TutorialItem(col_w * 2.5 - 80, y_items, img_herramienta, "reparar")
    target3 = TutorialTarget(col_w * 2.5 + 80, y_floor_targets - 40, img_roto, img_reparado, "reparar")

    items = pygame.sprite.Group(item1, item2, item3)
    targets = pygame.sprite.Group(target1, target2, target3)
    
    # Icono E
    icon_e = font_e.render("E", True, (255,255,255))
    bg_e = pygame.Surface((50,50), pygame.SRCALPHA)
    pygame.draw.rect(bg_e, (0,0,0,180), (0,0,50,50), border_radius=10)
    bg_e.blit(icon_e, icon_e.get_rect(center=(25,25)))

    # Cartel HUD
    hud_lines = [
        "TUTORIAL DE ENTRENAMIENTO",
        "Mover: WASD/Flechas | Acción: E / Enter"
    ]
    
    labels = [
        ("NIVEL 1", "Lleva la basura", col_w * 0.5),
        ("NIVEL 2", "Planta la semilla", col_w * 1.5),
        ("NIVEL 3", "Repara la zona", col_w * 2.5)
    ]

    t = 0.0
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        t += dt
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False; return 
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if rect_back.collidepoint(mouse_pos):
                    play_sfx("sfx_click", assets_dir)
                    running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: play_sfx("sfx_click", assets_dir); running = False 
                
                if event.key == pygame.K_e or event.key == pygame.K_RETURN:
                    if player.carrying_item:
                        hit = pygame.sprite.spritecollideany(player, targets)
                        if hit:
                            if hit.kind == player.carrying_item.kind and not hit.done:
                                player.carrying_item.completed = True
                                player.carrying_item.carried = False
                                player.carrying_item = None
                                hit.complete() 
                                play_sfx("sfx_plant", assets_dir) 
                            else:
                                player.carrying_item.carried = False
                                player.carrying_item.reset()
                                player.carrying_item = None
                        else:
                            player.carrying_item.carried = False
                            player.carrying_item.reset()
                            player.carrying_item = None
                    else:
                        for it in items:
                            if not it.completed and not it.carried:
                                dist = math.hypot(player.rect.centerx - it.rect.centerx, player.rect.centery - it.rect.centery)
                                if dist < 100: 
                                    player.carrying_item = it
                                    it.carried = True
                                    play_sfx("sfx_pick_seed", assets_dir)
                                    break

        player.handle_input(dt)

        screen.fill((60, 140, 70)) 
        # Líneas divisorias
        pygame.draw.line(screen, (255,255,255), (col_w, 130), (col_w, H-20), 3)
        pygame.draw.line(screen, (255,255,255), (col_w*2, 130), (col_w*2, H-20), 3)

        # --- DIBUJAR HUD ---
        for i, line in enumerate(hud_lines):
            shadow = font_hud.render(line, True, (15, 15, 15))
            screen.blit(shadow, (16 + 2, 20 + 2 + i * 28))
            text = font_hud.render(line, True, (255, 255, 255))
            screen.blit(text, (16, 20 + i * 28))

        # Botón Back (Abajo Izquierda)
        if rect_back.collidepoint(mouse_pos):
             scaled_back = pygame.transform.smoothscale(img_back, (int(rect_back.width * 1.1), int(rect_back.height * 1.1)))
             screen.blit(scaled_back, scaled_back.get_rect(center=rect_back.center))
        else:
             screen.blit(img_back, rect_back)

        # Etiquetas
        for title, desc, cx in labels:
            lbl_t = font_label.render(title, True, (255, 255, 0))
            lbl_d = font_label.render(desc, True, (240, 240, 240))
            screen.blit(lbl_t, lbl_t.get_rect(center=(cx, 100)))
            screen.blit(lbl_d, lbl_d.get_rect(center=(cx, 130)))

        for tar in targets:
            screen.blit(tar.image, tar.rect)
            if tar.done:
                off = math.sin(t * 8) * 5
                # Palomita encima del objeto
                cr = img_check.get_rect(center=tar.rect.center)
                cr.y -= (tar.rect.height//2 + 20 + off)
                screen.blit(img_check, cr)

        for it in items: it.draw(screen, t)
        player.draw(screen)

        show_e = False
        if player.carrying_item:
            hit = pygame.sprite.spritecollideany(player, targets)
            if hit and hit.kind == player.carrying_item.kind and not hit.done: show_e = True
        else:
            for it in items:
                if not it.completed and not it.carried:
                    dist = math.hypot(player.rect.centerx - it.rect.centerx, player.rect.centery - it.rect.centery)
                    if dist < 100: show_e = True; break
        
        if show_e:
            b = math.sin(t * 10) * 3
            screen.blit(bg_e, bg_e.get_rect(midbottom=(player.rect.centerx, player.rect.top - 15 + b)))

        pygame.display.flip()
    stop_level_music()