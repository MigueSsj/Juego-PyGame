import pygame
from pathlib import Path

def find_by_stem(assets_dir: Path, stem: str):
    exts = (".png", ".jpg", ".jpeg")
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists(): return p
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{stem}*{ext}"))
    return min(cands, key=lambda p: len(p.name)) if cands else None

def load_bg(assets_dir: Path) -> pygame.Surface:
    for s in ["nivel1_parque", "parque_nivel1", "park_level1", "nivel1"]:
        p = find_by_stem(assets_dir, s)
        if p: return pygame.image.load(str(p)).convert()
    raise FileNotFoundError("No encontré la imagen del parque para Nivel 1.")

def run(screen: pygame.Surface, assets_dir: Path):
    clock = pygame.time.Clock()
    W, H = screen.get_size()
    background = pygame.transform.smoothscale(load_bg(assets_dir), (W, H))

    tiempo_total_ms = 30_000
    inicio = pygame.time.get_ticks()
    font = pygame.font.SysFont("arial", 28)

    back_p = find_by_stem(assets_dir, "btn_back") or find_by_stem(assets_dir, "back")
    if not back_p: raise FileNotFoundError("Falta btn_back*.png")
    back_img = pygame.image.load(str(back_p)).convert_alpha()
    dw = max(120, min(int(W * 0.12), 240))
    ratio = dw / back_img.get_width()
    back_img = pygame.transform.smoothscale(back_img, (dw, int(back_img.get_height()*ratio)))
    back_rect = back_img.get_rect(); back_rect.bottomleft = (10, H-12)

    speed = 5

    while True:
        dt = clock.tick(60)
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if back_rect.collidepoint(e.pos): return None

        elapsed = pygame.time.get_ticks() - inicio
        restante = max(0, (tiempo_total_ms - elapsed)//1000)

        screen.blit(background, (0,0))
        hud = font.render(f"Nivel 1 – Difícil | Tiempo: {restante}s | Vel: {speed}", True, (255,255,255))
        screen.blit(hud, (10,10))
        screen.blit(back_img, back_rect)
        pygame.display.flip()
