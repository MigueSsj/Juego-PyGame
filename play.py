# play.py
import pygame
from pathlib import Path
from audio_shared import play_sfx 
import config # IMPORTAR CONFIG
import traceback # Necesario para el try/except de dificultad

# --- IMPORT ROBUSTO DE dificultad ---
try:
    import dificultad as dificultad
except ModuleNotFoundError:
    from levels import dificultad as dificultad

### --- MODIFICACIÓN DE IDIOMA (find_by_stem) --- ###
def find_by_stem(assets_dir: Path, stem: str) -> Path | None:
    real_name = config.obtener_nombre(stem)
    exts = (".png", ".jpg", ".jpeg")
    
    for ext in exts:
        p = assets_dir / f"{real_name}{ext}"
        if p.exists(): return p
        
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{real_name}*{ext}"))
    
    # Fallback al stem original
    if not cands and real_name != stem:
        for ext in exts:
            cands += list(assets_dir.glob(f"{stem}*{ext}"))
            
    return sorted(cands, key=lambda p: len(p.name))[0] if cands else None
### --- FIN MODIFICACIÓN DE IDIOMA --- ###

def load_image(assets_dir: Path, stems: list[str]) -> pygame.Surface | None:
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            return img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
    return None

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    if img.get_width() == 0: return pygame.Surface((new_w, new_w), pygame.SRCALPHA)
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height()*r)))

def _stop_menu_music():
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.fadeout(400)
    except Exception:
        pass

# ✨ Nueva función mejorada: zoom al pasar el mouse
def draw_card(screen, img, rect, mouse, scale_factor=1.10):
    if rect.collidepoint(mouse):
        zoom_w = int(rect.width * scale_factor)
        zoom_h = int(rect.height * scale_factor)
        zoom_img = pygame.transform.smoothscale(img, (zoom_w, zoom_h))
        zoom_rect = zoom_img.get_rect(center=rect.center)
        screen.blit(zoom_img, zoom_rect)
    else:
        screen.blit(img, rect)


def run(screen: pygame.Surface, assets_dir: Path):
    clock = pygame.time.Clock()
    W, H = screen.get_size()

    background = load_image(assets_dir, ["Background_f"])
    if background is None: raise FileNotFoundError("Fondo 'Background_f*' no encontrado.")
    background = pygame.transform.smoothscale(background, (W, H))
    scroll_x = 0; SCROLL_SPEED = 2

    ### --- MODIFICACIÓN DE IDIOMA (STEMS para carga de botones) --- ###
    # Usamos las claves de config.py para que la traducción funcione
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

    # Título de niveles
    title_img = load_image(assets_dir, ["title_levels", "seleccione", "title_niveles"])
    if not title_img: raise FileNotFoundError("Falta 'title_levels.png'.")
    title_img = scale_to_width(title_img, int(W * 0.45))
    title_rect = title_img.get_rect(center=(W // 2, int(H * 0.18)))

    # Botón Back
    back_img = load_image(assets_dir, ["btn_back", "regresar", "btn_regresar", "back"])
    if not back_img: raise FileNotFoundError("Falta 'btn_back*'.")
    ### --- FIN MODIFICACIÓN DE IDIOMA --- ###
    
    HOVER_SCALE = 1.08
    desired_w = max(120, min(int(W * 0.12), 240))
    back_img = scale_to_width(back_img, desired_w)
    back_img_hover = scale_to_width(back_img, int(back_img.get_width() * HOVER_SCALE))
    back_rect = back_img.get_rect()
    back_rect.bottomleft = (10, H - 12)

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

        # ✨ Hover zoom en las tarjetas
        draw_card(screen, card1, r1, mouse)
        draw_card(screen, card2, r2, mouse)
        draw_card(screen, card3, r3, mouse)

        # Hover zoom del botón regresar (ya existente)
        if back_rect.collidepoint(mouse):
            r = back_img_hover.get_rect(center=back_rect.center)
            screen.blit(back_img_hover, r)
            current_back_rect = r
        else:
            screen.blit(back_img, back_rect)
            current_back_rect = back_rect

        if click:

            def _handle_choice_for_level(lvl_num):
                try:
                    choice = dificultad.run(screen, assets_dir, nivel=lvl_num)
                except Exception as e:
                    print(f"ERROR en dificultad.run({lvl_num}):", e)
                    traceback.print_exc()
                    return None

                if not isinstance(choice, dict) or "dificultad" not in choice:
                    return None

                CHARACTER_FOLDER_MAP = {
                    "EcoGuardian": "PERSONAJE H",
                    "EcoGuardianM": "PERSONAJE M",
                    "H": "PERSONAJE H",
                    "M": "PERSONAJE M",
                }

                personaje_folder = None
                if "personaje_folder" in choice:
                    personaje_folder = choice["personaje_folder"]
                elif "personaje" in choice:
                    val = choice["personaje"]
                    if isinstance(val, str) and val.upper().startswith("PERSONAJE"):
                        personaje_folder = val
                    else:
                        personaje_folder = CHARACTER_FOLDER_MAP.get(val)
                if not personaje_folder:
                    personaje_folder = "PERSONAJE H"

                return {
                    "nivel": lvl_num,
                    "dificultad": choice["dificultad"],
                    "personaje": personaje_folder
                }

            if r1.collidepoint(mouse):
                play_sfx("select", assets_dir)
                result = _handle_choice_for_level(1)
                if result:
                    _stop_menu_music()
                    return result

            elif r2.collidepoint(mouse):
                play_sfx("select", assets_dir)
                result = _handle_choice_for_level(2)
                if result:
                    _stop_menu_music()
                    return result

            elif r3.collidepoint(mouse):
                play_sfx("select", assets_dir)
                result = _handle_choice_for_level(3)
                if result:
                    _stop_menu_music()
                    return result

            elif current_back_rect.collidepoint(mouse):
                play_sfx("back", assets_dir)
                return None

        pygame.display.flip()
        clock.tick(60)