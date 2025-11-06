# play.py
import pygame
from pathlib import Path
from audio_shared import play_sfx  # <<< SFX compartidos (select/back)

# --- IMPORT ROBUSTO DE dificultad ---
try:
    import dificultad as dificultad
except ModuleNotFoundError:
    from levels import dificultad as dificultad

def find_by_stem(assets_dir: Path, stem: str) -> Path | None:
    exts = (".png", ".jpg", ".jpeg")
    for ext in exts:
        p = assets_dir / f"{stem}{ext}"
        if p.exists(): return p
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{stem}*{ext}"))
    return sorted(cands, key=lambda p: len(p.name))[0] if cands else None

def load_image(assets_dir: Path, stems: list[str]) -> pygame.Surface | None:
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
    return None

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height()*r)))

def _stop_menu_music():
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.fadeout(400)
    except Exception:
        pass

def run(screen: pygame.Surface, assets_dir: Path):
    clock = pygame.time.Clock()
    W, H = screen.get_size()

    background = load_image(assets_dir, ["Background_f"])
    if background is None: raise FileNotFoundError("Fondo 'Background_f*' no encontrado.")
    background = pygame.transform.smoothscale(background, (W, H))
    scroll_x = 0; SCROLL_SPEED = 2

    card1 = load_image(assets_dir, ["btn_nivel_1", "nivel_1"])
    card2 = load_image(assets_dir, ["btn_nivel_2", "nivel_2"])
    card3 = load_image(assets_dir, ["btn_nivel_3", "nivel_3"])
    if not all([card1, card2, card3]):
        raise FileNotFoundError("Faltan imágenes de niveles (btn_nivel_1/2/3*).")

    target_w = int(W * 0.26); gap = int(W * 0.02)
    card1 = scale_to_width(card1, target_w)
    card2 = scale_to_width(card2, target_w)
    card3 = scale_to_width(card3, target_w)

    total_w = card1.get_width() + card2.get_width() + card3.get_width() + 2*gap
    start_x = (W - total_w) // 2; center_y = int(H * 0.55)
    r1 = card1.get_rect(midleft=(start_x, center_y))
    r2 = card2.get_rect(midleft=(r1.right + gap, center_y))
    r3 = card3.get_rect(midleft=(r2.right + gap, center_y))

    title_img = load_image(assets_dir, ["title_levels", "seleccione", "title_niveles"])
    if not title_img: raise FileNotFoundError("Falta 'title_levels.png'.")
    title_img = scale_to_width(title_img, int(W * 0.45))
    title_rect = title_img.get_rect(center=(W // 2, int(H * 0.18)))

    back_img = load_image(assets_dir, ["btn_back", "regresar", "btn_regresar", "back"])
    if not back_img: raise FileNotFoundError("Falta 'btn_back*'.")
    HOVER_SCALE = 1.08
    desired_w = max(120, min(int(W * 0.12), 240))
    back_img = scale_to_width(back_img, desired_w)
    back_img_hover = scale_to_width(back_img, int(back_img.get_width() * HOVER_SCALE))
    back_rect = back_img.get_rect(); back_rect.bottomleft = (10, H - 12)

    def draw_card(img, rect, mouse):
        if rect.collidepoint(mouse):
            pygame.draw.rect(screen, (255, 255, 255), rect.inflate(10,10), 3, border_radius=10)
        screen.blit(img, rect)

    while True:
        mouse = pygame.mouse.get_pos()
        click = False
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return None
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                click = True

        scroll_x -= SCROLL_SPEED
        if scroll_x <= -W: scroll_x = 0
        screen.blit(background, (scroll_x, 0))
        screen.blit(background, (scroll_x + W, 0))

        screen.blit(title_img, title_rect)
        draw_card(card1, r1, mouse); draw_card(card2, r2, mouse); draw_card(card3, r3, mouse)

        if back_rect.collidepoint(mouse):
            r = back_img_hover.get_rect(center=back_rect.center)
            screen.blit(back_img_hover, r); current_back_rect = r
        else:
            screen.blit(back_img, back_rect); current_back_rect = back_rect

        if click:
            # debug rápido: muestra posición del click
            print("DEBUG: click at", mouse)

            def _handle_choice_for_level(lvl_num):
                try:
                    # llamar a la selección de dificultad/personaje
                    choice = dificultad.run(screen, assets_dir, nivel=lvl_num)
                except Exception as e:
                    print(f"ERROR: excepción en dificultad.run(nivel={lvl_num}):", e)
                    import traceback; traceback.print_exc()
                    # vuelve al menú principal para evitar crash silencioso
                    return None

                print("DEBUG: dificultad.run returned:", choice)

                # Si no devolvió el dict esperado, abortamos
                if not isinstance(choice, dict) or "dificultad" not in choice:
                    print("DEBUG: choice inválido, regresando al menú.")
                    return None

                # ---------- MAPPER de nombres -> carpetas de personaje ----------
                # Ajusta estas claves si tu selección devuelve otros nombres.
                CHARACTER_FOLDER_MAP = {
                    "EcoGuardian": "PERSONAJE H",
                    "EcoGuardianM": "PERSONAJE M",
                    "H": "PERSONAJE H",
                    "M": "PERSONAJE M",
                    # agrega más mapeos si tu selección devuelve otros labels
                }

                # Preferimos recibir directamente el nombre de carpeta en 'personaje_folder'
                # Si dificultad.run ya devuelve la carpeta correcta, úsala.
                personaje_folder = None
                if "personaje_folder" in choice:
                    personaje_folder = choice["personaje_folder"]
                elif "personaje" in choice:
                    val = choice["personaje"]
                    # si ya parece una carpeta válida, úsala
                    if isinstance(val, str) and val.upper().startswith("PERSONAJE"):
                        personaje_folder = val
                    else:
                        # mapear nombres user-friendly a nombres de carpeta
                        personaje_folder = CHARACTER_FOLDER_MAP.get(val, None)
                # fallback por defecto si no se resolvió:
                if not personaje_folder:
                    print("WARN: no se pudo mapear personaje recibido, usando 'PERSONAJE H' por defecto.")
                    personaje_folder = "PERSONAJE H"

                # devolvemos el dict con la carpeta ya resuelta
                return {
                    "nivel": lvl_num,
                    "dificultad": choice["dificultad"],
                    "personaje": personaje_folder
                }

            # nav click handling
            if r1.collidepoint(mouse):
                play_sfx("select", assets_dir)
                result = _handle_choice_for_level(1)
                if result:
                    _stop_menu_music()
                    print("DEBUG: iniciando nivel ->", result)
                    return result

            elif r2.collidepoint(mouse):
                play_sfx("select", assets_dir)
                result = _handle_choice_for_level(2)
                if result:
                    _stop_menu_music()
                    print("DEBUG: iniciando nivel ->", result)
                    return result

            elif r3.collidepoint(mouse):
                play_sfx("select", assets_dir)
                result = _handle_choice_for_level(3)
                if result:
                    _stop_menu_music()
                    print("DEBUG: iniciando nivel ->", result)
                    return result

            elif current_back_rect.collidepoint(mouse):
                play_sfx("back", assets_dir)
                return None

        pygame.display.flip()
        clock.tick(60)
