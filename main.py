import pygame, os, math
from pathlib import Path

pygame.init()

# =========================
# RUTAS (usa tus nombres)
# =========================
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
ASSETS = BASE_DIR / "assets"

# Cambia estos nombres si no coinciden EXACTO con los tuyos
bg_path       = ASSETS / "Background_fondo.jpeg"      # <-- pon aquí el nombre exacto
title_path    = ASSETS / "titulo_juego.png"
jugar_path    = ASSETS / "btn_play.jpeg"
opciones_path = ASSETS / "btn_opc.jpeg"
instru_path   = ASSETS / "btn_instrucciones.jpeg"      # <-- pon aquí el nombre exacto

# =========================
# CARGA
# =========================
background = pygame.image.load(str(bg_path))    # sin convert aún
W, H = background.get_size()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Guardianes del Planeta - Menú")
clock = pygame.time.Clock()
background = background.convert()

# Título
title_img = pygame.image.load(str(title_path)).convert_alpha()
TITLE_SCALE = 1.35  # 1.0 original, sube para hacerlo más grande
title_img = pygame.transform.smoothscale(
    title_img,
    (int(title_img.get_width()*TITLE_SCALE),
     int(title_img.get_height()*TITLE_SCALE))
)
title_w, title_h = title_img.get_size()

# Botones (nota: los .jpeg NO tienen transparencia)
def load_btn(path, scale=1.2, hover_scale=1.08):
    img = pygame.image.load(str(path)).convert()  # .jpeg -> sin alpha
    if scale != 1.0:
        img = pygame.transform.smoothscale(
            img, (int(img.get_width()*scale), int(img.get_height()*scale))
        )
    w, h = img.get_size()
    img_hover = pygame.transform.smoothscale(img, (int(w*hover_scale), int(h*hover_scale)))
    return img, img_hover

btn_jugar, btn_jugar_h = load_btn(jugar_path, 1.2)
btn_opc,   btn_opc_h   = load_btn(opciones_path, 1.2)
# Para instrucciones uso convert_alpha() por si tu PNG trae transparencia
img_inst = pygame.image.load(str(instru_path)).convert_alpha()
img_inst = pygame.transform.smoothscale(img_inst, (int(img_inst.get_width()*1.2), int(img_inst.get_height()*1.2)))
btn_inst = img_inst
btn_inst_h = pygame.transform.smoothscale(img_inst, (int(img_inst.get_width()*1.08), int(img_inst.get_height()*1.08)))

j_w, j_h = btn_jugar.get_size()
o_w, o_h = btn_opc.get_size()
i_w, i_h = btn_inst.get_size()

# =========================
# POSICIONES (como tu mockup)
# =========================
TITLE_TOP   = int(H * 0.12)   # “padding” superior del título (ajústalo)
COLUMN_TOP  = int(H * 0.34)   # inicio de la columna de botones
GAP         = 18              # separación vertical entre botones

rect_jugar = btn_jugar.get_rect(center=(W//2, COLUMN_TOP))
rect_opc   = btn_opc.get_rect(center=(W//2, COLUMN_TOP + j_h + GAP))
rect_inst  = btn_inst.get_rect(center=(W//2, COLUMN_TOP + j_h + GAP + o_h + GAP))

# =========================
# ANIMACIONES
# =========================
scroll_x = 0
SCROLL_SPEED = 2

t = 0
FLOAT_AMP   = 8
FLOAT_SPEED = 0.08

# =========================
# LOOP
# =========================

running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    click = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            click = True

    # Fondo en scroll
    scroll_x -= SCROLL_SPEED
    if scroll_x <= -W:
        scroll_x = 0
    screen.blit(background, (scroll_x, 0))
    screen.blit(background, (scroll_x + W, 0))

    # Título flotando
    y_float = int(FLOAT_AMP * math.sin(t * FLOAT_SPEED))
    screen.blit(title_img, ((W - title_w)//2, TITLE_TOP + y_float))

    # Botones con hover
    def draw_btn(img, img_hover, rect):
        if rect.collidepoint(mouse_pos):
            r = img_hover.get_rect(center=rect.center)
            r.y -= 2
            screen.blit(img_hover, r)
            return True
        else:
            screen.blit(img, rect)
            return False

    over_jugar = draw_btn(btn_jugar, btn_jugar_h, rect_jugar)
    over_opc   = draw_btn(btn_opc,   btn_opc_h,   rect_opc)
    over_inst  = draw_btn(btn_inst,  btn_inst_h,  rect_inst)

    if click:
        if rect_jugar.collidepoint(mouse_pos): print("🎮 JUGAR")
        elif rect_opc.collidepoint(mouse_pos): print("⚙️ OPCIONES")
        elif rect_inst.collidepoint(mouse_pos): print("📖 INSTRUCCIONES")

    pygame.display.flip()
    clock.tick(60)
    t += 1

pygame.quit()
