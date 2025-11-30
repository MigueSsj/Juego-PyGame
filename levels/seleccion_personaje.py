from __future__ import annotations
import pygame
from pathlib import Path
from typing import Optional, List, Tuple
from audio_shared import play_sfx
import re
import config # IMPORTAR CONFIG

# ===== helpers (MODIFICADO: Usa config.obtener_nombre) =====
def find_by_stem(assets_dir: Path, stem: str) -> Optional[Path]:
    real_name = config.obtener_nombre(stem)
    exts = (".png", ".jpg", ".jpeg")
    
    for ext in exts:
        p = assets_dir / f"{real_name}{ext}"
        if p.exists():
            return p
            
    cands = []
    for ext in exts:
        cands += list(assets_dir.glob(f"{real_name}*{ext}"))
        
    # Fallback al stem original
    if not cands and real_name != stem:
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

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    if img.get_width() == 0: return pygame.Surface((new_w, int(new_w*1.5)), pygame.SRCALPHA)
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height() * r)))

def scale_to_height(img: pygame.Surface, new_h: int) -> pygame.Surface:
    if img.get_height() == 0: return pygame.Surface((int(new_h*0.75), new_h), pygame.SRCALPHA)
    r = new_h / img.get_height()
    return pygame.transform.smoothscale(img, (int(img.get_width() * r), new_h))

def _scale_to_fit(img: pygame.Surface, box_w: int, box_h: int) -> pygame.Surface:
    if img.get_width() == 0 or img.get_height() == 0:
        return pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    r = min(box_w / img.get_width(), box_h / img.get_height())
    return pygame.transform.smoothscale(img, (int(img.get_width() * r), int(img.get_height() * r)))

# === Botón (MODIFICADO: Usa clave de texto) ===
class Button:
    def __init__(self, rect: pygame.Rect, text_key: str, font: pygame.font.Font,
                 base_surf: pygame.Surface | None = None,
                 hover_surf: pygame.Surface | None = None):
        self.rect = rect
        self.text_key = text_key 
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
        # Actualizamos el texto en cada draw por si el idioma cambió
        text = config.obtener_nombre(self.text_key)

        if self.base_surf:
            surf = self.hover_surf if self.is_hover else self.base_surf
            surface.blit(surf, surf.get_rect(center=self.rect.center))
        else:
            base, hover, press = (205,170,125), (225,190,145), (190,155,110)
            color = press if self.is_pressed else (hover if self.is_hover else base)
            pygame.draw.rect(surface, (30,20,15), self.rect, border_radius=10)
            pygame.draw.rect(surface, color, self.rect.inflate(-8, -8), border_radius=8)
        
        # Dibujar el texto traducido
        lbl = self.font.render(text, True, (25,20,15))
        if self.base_surf:
            label_rect = lbl.get_rect(center=(self.rect.w//2, int(self.rect.h*0.72)))
        else:
            label_rect = lbl.get_rect(center=(self.rect.w//2, self.rect.h//2))
        surface.blit(lbl, label_rect)


# === Cargar preview (usa find_by_stem) ===
def _load_character_preview(assets_dir: Path, char_folder: str, max_w: int, max_h: int) -> pygame.Surface:
    folder = assets_dir / char_folder
    if not folder.exists():
        ph = pygame.Surface((max_w, max_h), pygame.SRCALPHA)
        ph.fill((0,0,0,0))
        return ph

    if "M" in char_folder.upper():
        prefix = "womanguardian"
    else:
        prefix = "ecoguardian"

    candidates = [
        f"{prefix}_walk_down_1",
        f"{prefix}_down_idle",
        f"{prefix}_frente",
        f"{prefix}_idle_down",
        f"{prefix}_walk_down_0",
        prefix
    ]
    
    img = None
    for stem in candidates:
        p = find_by_stem(folder, stem) # Usa find_by_stem para buscar dentro de la subcarpeta del personaje
        if p:
            img = pygame.image.load(str(p))
            img = img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
            break
    
    if img is None:
        ph = pygame.Surface((max_w, max_h), pygame.SRCALPHA)
        ph.fill((0,0,0,0))
        return ph
        
    return _scale_to_fit(img, max_w, max_h)

# ===== Pantalla selección (MODIFICADO para offset en inglés) =====
class SeleccionPersonajeScreen:
    def __init__(self, screen: pygame.Surface, assets_dir: Path):
        self.screen = screen
        self.assets_dir = assets_dir
        self.w, self.h = self.screen.get_size()
        
        self.clock = pygame.time.Clock()

        self.PAD_TOP    = int(self.h * 0.02)
        self.PAD_BOTTOM = int(self.h * 0.02)

        # Fondo
        self.bg = load_image(assets_dir, ["Background_f", "bg_inicio", "fondo"])
        if self.bg is None:
            self.bg = pygame.Surface((self.w, self.h))
            self.bg.fill((10,25,40))

        self.bg_scroll_x = 0.0
        self.bg_speed = 40.0
        bg_w = int(self.bg.get_width() * (self.h / self.bg.get_height()))
        self.bg_scaled = pygame.transform.scale(self.bg, (bg_w, self.h))

        pygame.font.init()
        self.font_title = pygame.font.SysFont("Arial", max(28, self.w//18), bold=True)
        self.font_btn   = pygame.font.SysFont("Arial", max(20, self.w//28), bold=True)
        self.font_name  = pygame.font.SysFont("Arial", max(22, self.w//32), bold=True)

        ### --- AJUSTE DE POSICIÓN CONDICIONAL PARA IDIOMA --- ###
        title_stem = "title_personaje" 
        
        # 1. Cargar la imagen del título
        self.title_img = load_image(self.assets_dir, [title_stem, "title_seleccion_personaje",
                                                     "elige_personaje", "elija_personaje", "elige_tu_personaje"])
        
        # 2. Determinar si estamos en modo EN (título largo)
        is_english_mode = (config.obtener_nombre(title_stem) == (title_stem + "us"))
        
        # 3. Definir offsets: mover título abajo (+Y), mover botón arriba (-Y)
        title_y_offset = int(self.h * 0.07) if is_english_mode else int(self.h * 0.005) 
        button_y_offset = int(self.h * 0.05) if is_english_mode else 0 

        if self.title_img:
            self.title_img = scale_to_width(self.title_img, int(self.w*0.40))
            self.title_rect = self.title_img.get_rect(center=(self.w//2, self.PAD_TOP + self.title_img.get_height()//2 + title_y_offset))
        else:
            self.title_img = None
            self.title_rect = pygame.Rect(0,0,0,0)
        ### --- FIN AJUSTE DE POSICIÓN CONDICIONAL --- ###

        # Botón confirmar
        btn_img = load_image(self.assets_dir, ["btn_confirmar", "confirmar", "btn_continuar", "continuar"])
        btn_base = btn_hover = None
        
        desired_w = int(self.w * 0.20)
        
        if btn_img:
            btn_base = scale_to_width(btn_img, desired_w)
            btn_hover = scale_to_width(btn_img, int(desired_w*1.08))
            rect = btn_base.get_rect()
        else:
            rect = pygame.Rect(0, 0, int(self.w*0.26), int(self.h*0.09))
        
        # Ajustamos la posición del botón con el offset (sube en inglés)
        rect.center = (self.w//2, self.h - self.PAD_BOTTOM - (rect.height // 2) - button_y_offset)
        
        # Usamos la clave de texto "btn_confirmar"
        self.btn_confirmar = Button(rect, "", self.font_btn, base_surf=btn_base, hover_surf=btn_hover)

        # Marcos separados (usan find_by_stem)
        self.marco_h_img = load_image(self.assets_dir, ["marco_personaje_h"])
        self.marco_m_img = load_image(self.assets_dir, ["marco_personaje_m"])
        
        box_h = int(self.h * 0.40)

        if not self.marco_h_img:
            self.marco_h_img = pygame.Surface((int(box_h * 0.75), box_h), pygame.SRCALPHA)
            self.marco_h_img.fill((87, 58, 44, 150))
        else:
            self.marco_h_img = scale_to_height(self.marco_h_img, box_h)

        if not self.marco_m_img:
            self.marco_m_img = pygame.Surface((int(box_h * 0.75), box_h), pygame.SRCALPHA)
            self.marco_m_img.fill((87, 58, 44, 150))
        else:
            self.marco_m_img = scale_to_height(self.marco_m_img, box_h)

        # La posición de las cajas se basa en el título y el botón
        box_area_top = self.title_rect.bottom + int(self.h * 0.03)
        box_area_bottom = self.btn_confirmar.rect.top - int(self.h * 0.03)
        box_area_h = box_area_bottom - box_area_top
        
        box_w_h = self.marco_h_img.get_width()
        box_w_m = self.marco_m_img.get_width()
        
        gap = int(self.w * 0.1)
        total_boxes_w = box_w_h + box_w_m + gap
        
        start_x = (self.w - total_boxes_w) // 2
        box_y = box_area_top + (box_area_h - box_h) // 2

        self.box_h_rect = pygame.Rect(start_x, box_y, box_w_h, box_h)
        self.box_m_rect = pygame.Rect(start_x + box_w_h + gap, box_y, box_w_m, box_h)

        preview_max_w_h = int(self.box_h_rect.width * 0.35)
        preview_max_h_h = int(self.box_h_rect.height * 0.50)
        preview_max_w_m = int(self.box_m_rect.width * 0.35)
        preview_max_h_m = int(self.box_m_rect.height * 0.50)
        
        self.preview_h = _load_character_preview(assets_dir, "PERSONAJE H", preview_max_w_h, preview_max_h_h)
        self.preview_m = _load_character_preview(assets_dir, "PERSONAJE M", preview_max_w_m, preview_max_h_m)

        self.selected_char: Optional[str] = None
        
        self.back_img = load_image(assets_dir, ["btn_back", "regresar", "btn_regresar", "back"])
        self.back_img_hover = None
        self.back_rect = pygame.Rect(0,0,1,1)
        if self.back_img:
            desired_w = max(120, min(int(self.w * 0.12), 240))
            self.back_img = scale_to_width(self.back_img, desired_w)
            self.back_img_hover = scale_to_width(self.back_img, int(self.back_img.get_width() * 1.08))
            self.back_rect = self.back_img.get_rect(bottomleft=(10, self.h - 12))

        # ==== NUEVO: carga de la palomita ====
        self.check_img = load_image(self.assets_dir, ["basurita_entregada"])
        if self.check_img:
            self.check_img = scale_to_width(self.check_img, int(self.w * 0.06))

    def _draw_scrolling_bg(self, dt: float):
        self.bg_scroll_x = (self.bg_scroll_x - self.bg_speed*dt) % self.bg_scaled.get_width()
        x = -self.bg_scroll_x
        while x < self.w:
            self.screen.blit(self.bg_scaled, (int(x), 0))
            x += self.bg_scaled.get_width()

    def run(self) -> Optional[str]:
        while True:
            dt = self.clock.tick(60) / 1000.0
            events = pygame.event.get()
            
            mouse_pos = pygame.mouse.get_pos()
            clicked_back = False

            # ========= EVENTOS ===========
            for ev in events:
                if ev.type == pygame.QUIT:
                    return None
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        play_sfx("back", self.assets_dir)
                        return None
                
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if self.box_h_rect.collidepoint(mouse_pos):
                        self.selected_char = "PERSONAJE H"
                        play_sfx("select", self.assets_dir)
                    elif self.box_m_rect.collidepoint(mouse_pos):
                        self.selected_char = "PERSONAJE M"
                        play_sfx("select", self.assets_dir)

                    if self.back_rect.collidepoint(mouse_pos):
                        clicked_back = True

                # === Confirmar ===
                if self.btn_confirmar.update(events):
                    if self.selected_char:
                        play_sfx("select", self.assets_dir)
                        return self.selected_char
                    else:
                        play_sfx("back", self.assets_dir)

                # === Back ===
                if clicked_back:
                    play_sfx("back", self.assets_dir)
                    return None

            # ====================================
            # ============= DIBUJO ===============
            # ====================================
            self._draw_scrolling_bg(dt)

            if self.title_img:
                self.screen.blit(self.title_img, self.title_rect)

            # ========== MARCOS con hover persistente ==========
            marco_h = self.marco_h_img
            marco_m = self.marco_m_img

            grow_factor = 1.07

            mouse_over_h = self.box_h_rect.collidepoint(mouse_pos)
            mouse_over_m = self.box_m_rect.collidepoint(mouse_pos)

            selected_h = (self.selected_char == "PERSONAJE H")
            selected_m = (self.selected_char == "PERSONAJE M")

            # H
            if mouse_over_h or selected_h:
                marco_h = pygame.transform.smoothscale(
                    self.marco_h_img,
                    (int(self.marco_h_img.get_width()*grow_factor),
                     int(self.marco_h_img.get_height()*grow_factor))
                )
                marco_h_rect = marco_h.get_rect(center=self.box_h_rect.center)
            else:
                marco_h_rect = self.box_h_rect

            # M
            if mouse_over_m or selected_m:
                marco_m = pygame.transform.smoothscale(
                    self.marco_m_img,
                    (int(self.marco_m_img.get_width()*grow_factor),
                     int(self.marco_m_img.get_height()*grow_factor))
                )
                marco_m_rect = marco_m.get_rect(center=self.box_m_rect.center)
            else:
                marco_m_rect = self.box_m_rect

            self.screen.blit(marco_h, marco_h_rect)
            self.screen.blit(marco_m, marco_m_rect)

            # ======== PERSONAJES (mover un poquito izquierda) ========
            offset_x = -10

            center_h = (marco_h_rect.centerx + offset_x, marco_h_rect.centery - int(self.h * 0.02))
            center_m = (marco_m_rect.centerx + offset_x, marco_m_rect.centery - int(self.h * 0.02))

            img_rect_h = self.preview_h.get_rect(center=center_h)
            img_rect_m = self.preview_m.get_rect(center=center_m)

            self.screen.blit(self.preview_h, img_rect_h)
            self.screen.blit(self.preview_m, img_rect_m)

            # ======== NUEVO: Palomita en la parte inferior del marco ========
            if self.check_img and self.selected_char:
                # Altura base del pedestal (Ajustada para que esté sobre la base)
                check_offset_y = int(self.h * 0.03) 
                
                if selected_h:
                    # Posicionar sobre el pedestal H
                    check_rect = self.check_img.get_rect(
                        midbottom=(marco_h_rect.centerx, marco_h_rect.bottom - check_offset_y)
                    )
                    self.screen.blit(self.check_img, check_rect)

                if selected_m:
                    # Posicionar sobre el pedestal M
                    check_rect = self.check_img.get_rect(
                        midbottom=(marco_m_rect.centerx, marco_m_rect.bottom - check_offset_y)
                    )
                    self.screen.blit(self.check_img, check_rect)

            # Botón confirmar
            self.btn_confirmar.draw(self.screen)
            
            # Botón back
            if self.back_img and self.back_img_hover:
                if self.back_rect.collidepoint(mouse_pos):
                    r = self.back_img_hover.get_rect(center=self.back_rect.center)
                    self.screen.blit(self.back_img_hover, r)
                else:
                    self.screen.blit(self.back_img, self.back_rect)

            pygame.display.flip()