import pygame
from pathlib import Path
from typing import Optional

# ---------- helpers ----------
def find_by_stem(assets_dir: Path, stem: str) -> Optional[Path]:
    """
    Devuelve el Path del primer archivo que coincida exactamente con 'stem'
    + extensión, o por prefijo (nombre que empiece con 'stem').
    Extensiones válidas: .png, .jpg, .jpeg
    """
    exts = (".png", ".jpg", ".jpeg")
    # Coincidencia exacta
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists():
            return p
    # Coincidencia por prefijo (elige el nombre más corto)
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{stem}*{ext}"))
    return min(cands, key=lambda p: len(p.name)) if cands else None

def load_bg(assets_dir: Path) -> pygame.Surface:
    """
    Carga el fondo del Nivel 1 (parque).
    Busca por varios prefijos para mayor flexibilidad.
    """
    for s in ["nivel1_parque", "parque_nivel1", "park_level1", "nivel1"]:
        p = find_by_stem(assets_dir, s)
        if p:
            return pygame.image.load(str(p)).convert()
    raise FileNotFoundError("No encontré la imagen del parque para Nivel 1.")

def load_char_thumb(assets_dir: Path) -> Optional[pygame.Surface]:
    """
    Intenta cargar un 'retrato' pequeño del personaje para el HUD.
    Busca por prefijos típicos del EcoGuardian. Si no existe, devuelve None.
    """
    candidates = ["ecoguardian_idle", "ecoguardian", "EcoGuardian", "eco_guardian", "guardian"]
    for stem in candidates:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            # si tiene alpha, conservamos alpha
            return img.convert_alpha() if img.get_alpha() is not None else img.convert()
    return None

# ---------- loop principal del nivel ----------
def run(screen: pygame.Surface, assets_dir: Path, personaje: str = "EcoGuardian", dificultad: str = "Fácil"):
    """
    Nivel 1 - Modo Fácil
    - Muestra fondo escalado a la ventana
    - HUD con temporizador y velocidad
    - Botón back (btn_back*.png) para salir/regresar
    - (Opcional) Mini retrato del personaje si existe en assets
    Parámetros extra (opcionales):
        personaje  -> nombre que se mostrará en el HUD (default: "EcoGuardian")
        dificultad -> texto para el HUD (default: "Fácil")
    """
    print("[DEBUG] Entrando a nivel1_facil.run()", f"personaje={personaje}", f"dificultad={dificultad}")

    pygame.font.init()
    clock = pygame.time.Clock()

    # Tamaño ventana
    W, H = screen.get_size()

    # Fondo escalado al tamaño de la ventana
    background = pygame.transform.smoothscale(load_bg(assets_dir), (W, H))

    # Temporizador (60s)
    tiempo_total_ms = 60_000
    inicio = pygame.time.get_ticks()

    # Fuentes
    font = pygame.font.SysFont("arial", 28)
    font_small = pygame.font.SysFont("arial", 22, bold=True)

    # Botón de regreso (esquina inferior izquierda)
    back_p = find_by_stem(assets_dir, "btn_back") or find_by_stem(assets_dir, "back")
    if not back_p:
        raise FileNotFoundError("Falta btn_back*.png")
    back_img = pygame.image.load(str(back_p)).convert_alpha()
    dw = max(120, min(int(W * 0.12), 240))
    ratio = dw / back_img.get_width()
    back_img = pygame.transform.smoothscale(back_img, (dw, int(back_img.get_height() * ratio)))
    back_rect = back_img.get_rect()
    back_rect.bottomleft = (10, H - 12)

    # (Opcional) Retrato del personaje en HUD
    char_thumb = load_char_thumb(assets_dir)
    if char_thumb:
        # Escalar a alto ~ 48 px para HUD
        target_h = 48
        scale = target_h / char_thumb.get_height()
        char_thumb = pygame.transform.smoothscale(
            char_thumb, (int(char_thumb.get_width() * scale), target_h)
        )
        char_thumb_rect = char_thumb.get_rect()
        char_thumb_rect.topleft = (10, 54)  # debajo del HUD principal

    # Placeholder para entidades del juego
    speed = 3

    # ----------- bucle del nivel -----------
    while True:
        dt = clock.tick(60)

        # Eventos
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                print("[DEBUG] Quit en nivel1_facil → return None")
                return None
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    # ESC también regresa (por si no quieres usar el botón)
                    print("[DEBUG] ESC presionado → return None")
                    return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if back_rect.collidepoint(e.pos):
                    print("[DEBUG] Click en back → return None")
                    return None

        # Tiempo restante (en segundos)
        elapsed = pygame.time.get_ticks() - inicio
        restante = max(0, (tiempo_total_ms - elapsed) // 1000)

        # ----------- DIBUJO -----------
        screen.blit(background, (0, 0))

        # HUD principal (arriba izquierda)
        hud_text = f"Nivel 1 – {dificultad} | Tiempo: {restante}s | Vel: {speed}"
        hud = font.render(hud_text, True, (255, 255, 255))
        screen.blit(hud, (10, 10))

        # Nombre del personaje y mini retrato (si existe)
        name_label = font_small.render(f"Personaje: {personaje}", True, (255, 230, 90))
        # sombra para legibilidad
        name_shadow = font_small.render(f"Personaje: {personaje}", True, (0, 0, 0))
        screen.blit(name_shadow, (12, 42))
        screen.blit(name_label, (10, 40))

        if char_thumb:
            screen.blit(char_thumb, char_thumb_rect)

        # Botón back
        screen.blit(back_img, back_rect)

        pygame.display.flip()
