# seleccion_personaje.py
from __future__ import annotations
import pygame
from pathlib import Path
from typing import Optional, List, Tuple
from audio_shared import play_sfx  # <<< usamos el banco SFX compartido

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
            return img.convert_alpha() if p.suffix.lower() == ".png" else img.convert()
    return None

def scale_to_height(img: pygame.Surface, target_h: int) -> tuple[int, int]:
    h = target_h
    w = int(img.get_width() * (h / img.get_height()))
    return (w, h)

def scale_to_width(img: pygame.Surface, target_w: int) -> tuple[int, int]:
    w = target_w
    h = int(img.get_height() * (w / img.get_width()))
    return (w, h)

def _scale_to_fit(img: pygame.Surface, box_w: int, box_h: int) -> pygame.Surface:
    r = min(box_w / img.get_width(), box_h / img.get_height(), 1.0)
    if r < 1.0:
        return pygame.transform.smoothscale(img, (int(img.get_width() * r), int(img.get_height() * r)))
    return img

def _find_person_images(assets_dir: Path) -> List[Path]:
    """Busca candidatos en assets/personajes y, si no hay, en assets/."""
    exts = (".png", ".jpg", ".jpeg")
    res: List[Path] = []
    for base in [assets_dir / "personajes", assets_dir]:
        if not base.exists():
            continue
        for ext in exts:
            res += list(base.glob(f"*{ext}"))
    # Prioriza archivos que contengan 'frente'
    def key(p: Path) -> Tuple[int, int]:
        name = p.stem.lower()
        return (0 if "frente" in name else 1, len(name))
    res.sort(key=key)
    return res

def _pretty_name(p: Path) -> str:
    """Convierte nombre de archivo a nombre visible."""
    stem = p.stem.lower()
    # mapeos comunes de tu proyecto
    if "eco" in stem and "m" in stem and ("frente" in stem or "eco_m" in stem or "-m" in stem or "_m" in stem):
        return "EcoGuardian (M)"
    if "eco" in stem and "f" in stem and ("frente" in stem or "eco_f" in stem or "-f" in stem or "_f" in stem):
        return "EcoGuardian (F)"
    nice = stem.replace("frente", "").replace("_", " ").replace("-", " ").strip()
    nice = " ".join(n for n in nice.split() if n)  # limpia dobles espacios
    return nice.title() if nice else "Personaje"

# ===== botón =====
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
            surf = self.hover_surf if self.is_hover else self.base_surf
            surface.blit(surf, surf.get_rect(center=self.rect.center))
        else:
            base, hover, press = (205,170,125), (225,190,145), (190,155,110)
            color = press if self.is_pressed else (hover if self.is_hover else base)
            pygame.draw.rect(surface, (30,20,15), self.rect, border_radius=10)  # marco
            pygame.draw.rect(surface, color, self.rect.inflate(-8, -8), border_radius=8)
            lbl = self.font.render(self.text, True, (25,20,15))
            surface.blit(lbl, lbl.get_rect(center=self.rect.center))

# ===== Screen selección =====
class SeleccionPersonajeScreen:
    def __init__(self, screen: pygame.Surface, assets_dir: Path):
        self.screen = screen
        self.assets_dir = assets_dir
        self.w, self.h = self.screen.get_size()
        self.clock = pygame.time.Clock()

        self.PAD_TOP    = int(self.h * 0.08)
        self.PAD_BOTTOM = int(self.h * 0.08)

        # Fondo (usa tu fondo principal si existe)
        self.bg = load_image(assets_dir, ["Background_f", "bg_inicio", "fondo_inicio", "pantalla_inicio", "background_inicio", "fondo"])
        if self.bg is None:
            self.bg = pygame.Surface((self.w, self.h)); self.bg.fill((10,25,40))
        self.bg_scroll_x = 0.0
        self.bg_speed = 40.0
        self.bg_scaled = pygame.transform.scale(self.bg, scale_to_height(self.bg, self.h))

        # Fuentes
        pygame.font.init()
        self.font_title = pygame.font.SysFont("Arial", max(28, self.w//18), bold=True)
        self.font_btn   = pygame.font.SysFont("Arial", max(20, self.w//28), bold=True)
        self.font_name  = pygame.font.SysFont("Arial", max(18, self.w//34), bold=True)

        # Título
        self.title_img = load_image(self.assets_dir, ["title_personaje", "title_seleccion_personaje",
                                                      "elige_personaje", "elija_personaje", "elige_tu_personaje"])
        if self.title_img:
            self.title_img = pygame.transform.scale(self.title_img, scale_to_width(self.title_img, int(self.w*0.28)))
            self.title_rect = self.title_img.get_rect(center=(self.w//2, self.PAD_TOP + self.title_img.get_height()//2))
        else:
            self.title_img = None

        # Botón Confirmar (con hover)
        btn_img = load_image(self.assets_dir, ["btn_confirmar", "confirmar", "btn_continuar", "continuar"])
        btn_base = btn_hover = None
        btn_center = (self.w//2, self.h - self.PAD_BOTTOM - int(self.h * 0.06))
        if btn_img:
            desired_w = int(self.w * 0.22)
            btn_base = pygame.transform.scale(btn_img, scale_to_width(btn_img, desired_w))
            btn_hover = pygame.transform.scale(btn_img, scale_to_width(btn_img, int(desired_w*1.08)))
            rect = btn_base.get_rect(center=btn_center)
        else:
            rect = pygame.Rect(0, 0, int(self.w*0.28), int(self.h*0.10))
            rect.center = btn_center
        if rect.bottom > self.h - self.PAD_BOTTOM:
            rect.bottom = self.h - self.PAD_BOTTOM
        self.btn_confirmar = Button(rect, "Confirmar", self.font_btn, base_surf=btn_base, hover_surf=btn_hover)

        # Área del preview (donde va el personaje) — la hice un poco más grande
        preview_w = int(self.w * 0.22)   # antes 0.18
        preview_h = int(self.h * 0.42)   # antes 0.36
        self.preview_rect = pygame.Rect(0, 0, preview_w, preview_h)
        self.preview_rect.center = (self.w//2, int(self.h*0.50))

        # Zonas de clic para cambiar (invisibles)
        sep = int(self.w*0.08)
        self.left_rect  = pygame.Rect(self.preview_rect.left - sep,  self.preview_rect.top, sep, self.preview_rect.height)
        self.right_rect = pygame.Rect(self.preview_rect.right,       self.preview_rect.top, sep, self.preview_rect.height)

        # Cargar candidatos
        self.candidatos = self._load_personajes()
        self.idx = 0 if self.candidatos else -1

    # --- carga personajes ---
    def _load_personajes(self):
        items = []
        for p in _find_person_images(self.assets_dir):
            try:
                img = pygame.image.load(str(p))
                img = img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
                name = _pretty_name(p)
                items.append({"path": p, "img": img, "name": name})
            except Exception:
                pass
        # Si no hay, crea un placeholder
        if not items:
            ph = pygame.Surface((64, 96), pygame.SRCALPHA)
            ph.fill((0,0,0,0)); pygame.draw.rect(ph, (240,200,0), ph.get_rect()); pygame.draw.rect(ph, (0,0,0), ph.get_rect(), 3)
            items.append({"path": Path("placeholder"), "img": ph, "name": "EcoGuardian"})
        return items

    # --- fondo scroll ---
    def _draw_scrolling_bg(self, dt: float):
        self.bg_scroll_x = (self.bg_scroll_x - self.bg_speed*dt) % self.bg_scaled.get_width()
        x = -self.bg_scroll_x
        while x < self.w:
            self.screen.blit(self.bg_scaled, (int(x), 0)); x += self.bg_scaled.get_width()

    def run(self) -> Optional[str]:
        while True:
            dt = self.clock.tick(60) / 1000.0
            events = pygame.event.get()
            for ev in events:
                if ev.type == pygame.QUIT:
                    return None
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if self.idx >= 0:
                            play_sfx("select", self.assets_dir)
                            return self.candidatos[self.idx]["name"]
                    if ev.key == pygame.K_ESCAPE:
                        play_sfx("back", self.assets_dir)
                        return None
                    if ev.key == pygame.K_LEFT and self.candidatos:
                        self.idx = (self.idx - 1) % len(self.candidatos)
                        play_sfx("select", self.assets_dir)
                    if ev.key == pygame.K_RIGHT and self.candidatos:
                        self.idx = (self.idx + 1) % len(self.candidatos)
                        play_sfx("select", self.assets_dir)

            # clicks
            if self.btn_confirmar.update(events):
                if self.idx >= 0:
                    play_sfx("select", self.assets_dir)
                    return self.candidatos[self.idx]["name"]

            for ev in events:
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    mouse = pygame.mouse.get_pos()
                    if self.left_rect.collidepoint(mouse) and self.candidatos:
                        self.idx = (self.idx - 1) % len(self.candidatos)
                        play_sfx("select", self.assets_dir)
                    elif self.right_rect.collidepoint(mouse) and self.candidatos:
                        self.idx = (self.idx + 1) % len(self.candidatos)
                        play_sfx("select", self.assets_dir)

            # DIBUJO
            self._draw_scrolling_bg(dt)

            # Título
            if self.title_img:
                self.screen.blit(self.title_img, self.title_img.get_rect(center=(self.w//2, self.PAD_TOP + self.title_img.get_height()//2)))
            else:
                title_y = self.PAD_TOP + 20
                title = self.font_title.render("Elige tu personaje", True, (20,15,10))
                self.screen.blit(title, title.get_rect(center=(self.w//2, title_y)))

            # Recuadro/placa detrás del sprite
            pygame.draw.rect(self.screen, (35,25,20), self.preview_rect, 6, border_radius=8)
            inner = self.preview_rect.inflate(-10, -10)
            pygame.draw.rect(self.screen, (250, 230, 120), inner, 0, border_radius=6)  # similar a tu “amarillo panel”

            # Imagen (AGRANDADA) — sin texto debajo
            if self.idx >= 0:
                item = self.candidatos[self.idx]
                iw, ih = item["img"].get_size()

                # Queremos agrandar hasta 1.35x pero sin salirnos del rectángulo
                max_scale = 1.35
                # Escala máxima que cabe en el recuadro (con margen de 8px)
                fit_scale_w = (inner.w - 8) / iw
                fit_scale_h = (inner.h - 8) / ih
                r = min(max_scale, fit_scale_w, fit_scale_h)
                if r < 1.0:
                    # Si aún no cabe a 1.0, reduce para entrar
                    r = min(fit_scale_w, fit_scale_h)
                new_size = (int(iw * r), int(ih * r))
                img_big = pygame.transform.smoothscale(item["img"], new_size)

                self.screen.blit(img_big, img_big.get_rect(center=inner.center))

            # Botón confirmar
            self.btn_confirmar.draw(self.screen)

            pygame.display.flip()
