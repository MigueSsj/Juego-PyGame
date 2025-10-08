import pygame, math
from pathlib import Path

# ====== SFX click ======
_click_snd = None
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

def find_by_stem(assets_dir: Path, stem: str) -> Path | None:
    exts = (".png", ".jpg", ".jpeg")
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists():
            return p
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{stem}*{ext}"))
    if not cands:
        return None
    return sorted(cands, key=lambda p: len(p.name))[0]

def load_image(assets_dir: Path, stems: list[str]) -> pygame.Surface | None:
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
    return None

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    ratio = new_w / img.get_width()
    new_h = int(img.get_height() * ratio)
    return pygame.transform.smoothscale(img, (new_w, new_h))

def run(screen: pygame.Surface, assets_dir: Path) -> None:
    W, H = screen.get_size()
    clock = pygame.time.Clock()

    bg_img = load_image(assets_dir, ["Background_f"])
    if not bg_img:
        raise FileNotFoundError("No encontré fondo para instrucciones")
    background = bg_img.convert()
    bg_w, _ = background.get_size()
    scroll_x = 0; SCROLL_SPEED = 2

    instr_img = load_image(assets_dir, ["instrucciones", "panel_instrucciones"])
    if not instr_img:
        raise FileNotFoundError("No encontré imagen de instrucciones en assets/")
    iw, ih = instr_img.get_size()
    ratio = min(W*0.9/iw, H*0.9/ih, 1.0)
    if ratio < 1.0:
        instr_img = pygame.transform.smoothscale(instr_img, (int(iw*ratio), int(ih*ratio)))
    instr_rect = instr_img.get_rect(center=(W//2, H//2))

    back_img = load_image(assets_dir, ["btn_back", "regresar", "btn_regresar", "back"])
    back_rect = None
    HOVER_SCALE = 1.08
    if back_img:
        desired_w = max(120, min(int(W * 0.12), 240))
        back_img = scale_to_width(back_img, desired_w)
        back_img_hover = scale_to_width(back_img, int(back_img.get_width() * HOVER_SCALE))
        back_rect = back_img.get_rect()
        back_rect.bottomleft = (10, H - 12)

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                play_click(assets_dir)
                return
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        scroll_x -= SCROLL_SPEED
        if scroll_x <= -bg_w: scroll_x = 0
        screen.blit(background, (scroll_x, 0))
        screen.blit(background, (scroll_x + bg_w, 0))

        screen.blit(instr_img, instr_rect)

        if back_rect:
            if back_rect.collidepoint(mouse_pos):
                r = back_img_hover.get_rect(center=back_rect.center)
                screen.blit(back_img_hover, r)
                if clicked:
                    play_click(assets_dir)
                    return
            else:
                screen.blit(back_img, back_rect)

        pygame.display.flip()
        clock.tick(60)
