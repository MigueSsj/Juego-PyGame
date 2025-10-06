# levels/seleccion_personaje.py
from __future__ import annotations
import pygame
from pathlib import Path
from typing import Optional

# ===== helpers =====
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

def load_image(assets_dir: Path, stems: list[str]) -> Optional[pygame.Surface]:
    for stem in stems:
        p = find_by_stem(assets_dir, stem)
        if p:
            img = pygame.image.load(str(p))
            return img.convert_alpha() if img.get_alpha() is not None else img.convert()
    return None

def scale_to_height(img: pygame.Surface, target_h: int) -> tuple[int, int]:
    h = target_h
    w = int(img.get_width() * (h / img.get_height()))
    return (w, h)

def scale_to_width(img: pygame.Surface, target_w: int) -> tuple[int, int]:
    w = target_w
    h = int(img.get_height() * (w / img.get_width()))
    return (w, h)

# ===== botón compatible con imagen o dibujado =====
class Button:
    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font,
                 base_surf: pygame.Surface | None = None,
                 hover_surf: pygame.Surface | None = None):
        self.rect = rect
        self.text = text
        self.font = font
        self.is_hover = False
        self.is_pressed = False
        self.base_surf = base_surf
        self.hover_surf = hover_surf

    def update(self, events: list[pygame.event.Event]) -> bool:
        mouse_pos = pygame.mouse.get_pos()
        self.is_hover = self.rect.collidepoint(mouse_pos)
        clicked = False
        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.is_hover:
                self.is_pressed = True
            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                if self.is_hover and self.is_pressed:
                    clicked = True
                self.is_pressed = False
        return clicked

    def draw(self, surface: pygame.Surface):
        if self.base_surf:
            # botón por imagen
            surf = self.hover_surf if self.is_hover else self.base_surf
            surface.blit(surf, surf.get_rect(center=self.rect.center))
        else:
            # botón dibujado
            base, hover, press = (30,160,90), (35,190,105), (25,120,70)
            color = press if self.is_pressed else (hover if self.is_hover else base)
            pygame.draw.rect(surface, color, self.rect, border_radius=10)
            pygame.draw.rect(surface, (0,0,0), self.rect, width=3, border_radius=10)
            lbl = self.font.render(self.text, True, (255,255,255))
            surface.blit(lbl, lbl.get_rect(center=self.rect.center))

# ===== Screen selección =====
class SeleccionPersonajeScreen:
    def __init__(self, screen: pygame.Surface, assets_dir: Path):
        self.screen = screen
        self.assets_dir = assets_dir
        self.w, self.h = self.screen.get_size()
        self.clock = pygame.time.Clock()

        # Fondo (incluye "fondo" por si tu archivo se llama así)
        self.bg = load_image(assets_dir, ["bg_inicio", "fondo_inicio", "pantalla_inicio", "background_inicio", "fondo"])
        if self.bg is None:
            self.bg = pygame.Surface((self.w, self.h)); self.bg.fill((10,25,40))
        self.bg_scroll_x = 0
        self.bg_speed = 40
        self.bg_scaled = pygame.transform.scale(self.bg, scale_to_height(self.bg, self.h))

        # Sprite EcoGuardian (más chico)
        eco = load_image(assets_dir, ["ecoguardian_idle", "ecoguardian", "EcoGuardian", "eco_guardian", "guardian"])
        if eco is None:
            eco = pygame.Surface((64,96), pygame.SRCALPHA)
            eco.fill((0,0,0,0)); pygame.draw.rect(eco, (240,200,0), eco.get_rect()); pygame.draw.rect(eco, (0,0,0), eco.get_rect(), 3)
        SPRITE_H_RATIO = 0.48  # ← antes ~0.60
        target_h = int(self.h * SPRITE_H_RATIO)
        self.eco_big = pygame.transform.scale(eco, scale_to_height(eco, target_h))

        # Fuentes
        pygame.font.init()
        self.font_title = pygame.font.SysFont("Arial", max(28, self.w//18), bold=True)
        self.font_name  = pygame.font.SysFont("Arial", max(22, self.w//26), bold=True)
        self.font_btn   = pygame.font.SysFont("Arial", max(20, self.w//28), bold=True)

        # Título como imagen (fallback a texto)
        self.title_img = load_image(self.assets_dir, [
            "title_personaje", "title_seleccion_personaje",
            "elige_personaje", "elige_tu_personaje"
        ])
        if self.title_img:
            self.title_img = pygame.transform.scale(self.title_img, scale_to_width(self.title_img, int(self.w*0.2)))
            self.title_rect = self.title_img.get_rect(center=(self.w//2, int(self.h*0.10)))
        else:
            self.title_img = None  # usaremos texto

        # Botón Confirmar con diseño igual a tus otros botones
        btn_img = load_image(self.assets_dir, ["btn_confirmar", "confirmar", "btn_continuar", "continuar"])
        btn_base = btn_hover = None
        btn_center = (self.w//2, int(self.h*0.88))
        if btn_img:
            desired_w = int(self.w * 0.22)
            btn_base = pygame.transform.scale(btn_img, scale_to_width(btn_img, desired_w))
            btn_hover = pygame.transform.scale(btn_img, scale_to_width(btn_img, int(desired_w*1.08)))
            rect = btn_base.get_rect(center=btn_center)
        else:
            # usamos botón dibujado
            rect = pygame.Rect(0, 0, int(self.w*0.28), int(self.h*0.10))
            rect.center = btn_center

        self.btn_confirmar = Button(rect, "Confirmar", self.font_btn, base_surf=btn_base, hover_surf=btn_hover)
        self.personaje_nombre = "EcoGuardian"

    # --- utils ---
    def _draw_scrolling_bg(self, dt: float):
        self.bg_scroll_x = (self.bg_scroll_x - self.bg_speed*dt) % self.bg_scaled.get_width()
        x = -self.bg_scroll_x
        while x < self.w:
            self.screen.blit(self.bg_scaled, (int(x), 0)); x += self.bg_scaled.get_width()

    def run(self) -> None:
        # IMPORT RELATIVO (funciona dentro de 'levels') + fallback
        try:
            from . import nivel1_facil as nivel1_facil
        except Exception:
            import nivel1_facil  # fallback si se ejecuta desde la raíz

        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            events = pygame.event.get()
            for ev in events:
                if ev.type == pygame.QUIT:
                    return
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        return nivel1_facil.run(self.screen, self.assets_dir,
                                                personaje=self.personaje_nombre, dificultad="Fácil")
                    if ev.key == pygame.K_ESCAPE:
                        return

            if self.btn_confirmar.update(events):
                return nivel1_facil.run(self.screen, self.assets_dir,
                                        personaje=self.personaje_nombre, dificultad="Fácil")

            # DIBUJO
            self._draw_scrolling_bg(dt)

            # Título
            if self.title_img:
                self.screen.blit(self.title_img, self.title_rect)
            else:
                title = self.font_title.render("Elige tu personaje", True, (255,255,255))
                title_o = self.font_title.render("Elige tu personaje", True, (0,0,0))
                self.screen.blit(title_o, title_o.get_rect(center=(self.w//2+2, int(self.h*0.12)+2)))
                self.screen.blit(title,   title.get_rect(center=(self.w//2,   int(self.h*0.12))))

            # Sprite centrado (un poco más arriba para que no tape el botón)
            sprite_rect = self.eco_big.get_rect(center=(self.w//2, int(self.h*0.52)))
            plate = pygame.Surface((sprite_rect.width+36, sprite_rect.height+36), pygame.SRCALPHA)
            plate.fill((0,0,0,80))
            self.screen.blit(plate, plate.get_rect(center=sprite_rect.center))
            self.screen.blit(self.eco_big, sprite_rect)

            # Nombre debajo
            name_s = self.font_name.render(self.personaje_nombre, True, (255,230,90))
            name_o = self.font_name.render(self.personaje_nombre, True, (0,0,0))
            name_pos = (self.w//2, int(self.h*0.77))
            self.screen.blit(name_o, name_o.get_rect(center=(name_pos[0]+2, name_pos[1]+2)))
            self.screen.blit(name_s, name_s.get_rect(center=name_pos))

            # Botón
            self.btn_confirmar.draw(self.screen)

            pygame.display.flip()

# (opcional) prueba rápida
if __name__ == "__main__":
    pygame.init()
    scr = pygame.display.set_mode((1280, 720))
    SeleccionPersonajeScreen(scr, Path(__file__).parent.parent / "assets").run()
    pygame.quit()
