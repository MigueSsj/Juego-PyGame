from __future__ import annotations
import pygame
from pathlib import Path
from typing import Optional, List, Tuple
from audio_shared import play_sfx  # <<< usamos el banco SFX compartido
import re

# ===== helpers (find_by_stem, load_image, scale_to_width) =====
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

def scale_to_width(img: pygame.Surface, new_w: int) -> pygame.Surface:
    if img.get_width() == 0: return pygame.Surface((new_w, int(new_w*1.5)))
    r = new_w / img.get_width()
    return pygame.transform.smoothscale(img, (new_w, int(img.get_height() * r)))

def scale_to_height(img: pygame.Surface, new_h: int) -> pygame.Surface:
    """Escala una imagen a una nueva altura, manteniendo la proporción."""
    if img.get_height() == 0: return pygame.Surface((int(new_h*0.75), new_h))
    r = new_h / img.get_height()
    return pygame.transform.smoothscale(img, (int(img.get_width() * r), new_h))

def _scale_to_fit(img: pygame.Surface, box_w: int, box_h: int) -> pygame.Surface:
    if img.get_width() == 0 or img.get_height() == 0:
        return pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    # Escalar para que quepa
    r = min(box_w / img.get_width(), box_h / img.get_height())
    return pygame.transform.smoothscale(img, (int(img.get_width() * r), int(img.get_height() * r)))

# === Botón (El mismo que tenías) ===
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

# === Helper para cargar 1 frame de preview ===
def _load_character_preview(assets_dir: Path, char_folder: str, max_w: int, max_h: int) -> pygame.Surface:
    """Carga un frame de preview (idle) de la carpeta del personaje."""
    folder = assets_dir / char_folder
    if not folder.exists():
        print(f"WARN: No se encuentra la carpeta {char_folder}")
        ph = pygame.Surface((max_w, max_h), pygame.SRCALPHA); ph.fill((0,0,0,0)); return ph # Placeholder transparente

    # === CAMBIO: Priorizar 'ecoguardian_walk_down_1' ===
    candidates = [
        "ecoguardian_walk_down_1", # <-- ¡Prioridad!
        "ecoguardian_down_idle", 
        "ecoguardian_frente", 
        "idle_down", 
        "ecoguardian_walk_down_0",
        "ecoguardian"
    ]
    # ===================================================
    
    img = None
    for stem in candidates:
        p = find_by_stem(folder, stem)
        if p:
            img = pygame.image.load(str(p))
            img = img.convert_alpha() if p.suffix.lower()==".png" else img.convert()
            break
    
    if img is None:
        ph = pygame.Surface((max_w, max_h), pygame.SRCALPHA); ph.fill((0,0,0,0)) # Placeholder transparente
        return ph
        
    return _scale_to_fit(img, max_w, max_h)


# ===== Screen selección (REDISEÑADA) =====
class SeleccionPersonajeScreen:
    def __init__(self, screen: pygame.Surface, assets_dir: Path):
        self.screen = screen
        self.assets_dir = assets_dir
        self.w, self.h = self.screen.get_size()
        self.clock = pygame.time.Clock()

        # === CAMBIO: Ajustar padding para subir todo AÚN MÁS ===
        self.PAD_TOP    = int(self.h * 0.02) # Era 0.04
        self.PAD_BOTTOM = int(self.h * 0.02) # Era 0.04

        # 1. Fondo (usamos el tuyo)
        self.bg = load_image(assets_dir, ["Background_f", "bg_inicio", "fondo"])
        if self.bg is None:
            self.bg = pygame.Surface((self.w, self.h)); self.bg.fill((10,25,40))
        self.bg_scroll_x = 0.0
        self.bg_speed = 40.0
        bg_w = int(self.bg.get_width() * (self.h / self.bg.get_height()))
        self.bg_scaled = pygame.transform.scale(self.bg, (bg_w, self.h))

        # 2. Fuentes
        pygame.font.init()
        self.font_title = pygame.font.SysFont("Arial", max(28, self.w//18), bold=True)
        self.font_btn   = pygame.font.SysFont("Arial", max(20, self.w//28), bold=True)
        self.font_name  = pygame.font.SysFont("Arial", max(22, self.w//32), bold=True)

        # 3. Título (el tuyo)
        self.title_img = load_image(self.assets_dir, ["title_personaje", "title_seleccion_personaje",
                                                     "elige_personaje", "elija_personaje", "elige_tu_personaje"])
        if self.title_img:
            self.title_img = scale_to_width(self.title_img, int(self.w*0.40))
            self.title_rect = self.title_img.get_rect(center=(self.w//2, self.PAD_TOP + self.title_img.get_height()//2))
        else:
            self.title_img = None
            self.title_rect = pygame.Rect(0,0,0,0) # dummy

        # 4. Botón Confirmar (el tuyo)
        btn_img = load_image(self.assets_dir, ["btn_confirmar", "confirmar", "btn_continuar", "continuar"])
        btn_base = btn_hover = None
        
        # === CAMBIO: Botón más chico (Era 0.22) ===
        desired_w = int(self.w * 0.20) 
        
        if btn_img:
            btn_base = scale_to_width(btn_img, desired_w)
            btn_hover = scale_to_width(btn_img, int(desired_w*1.08))
            rect = btn_base.get_rect()
        else:
            rect = pygame.Rect(0, 0, int(self.w*0.26), int(self.h*0.09)) # Fallback más chico
        
        # === CAMBIO: Posición del botón B-A-S-A-D-A en el fondo ===
        rect.center = (self.w//2, self.h - self.PAD_BOTTOM - (rect.height // 2))
        
        self.btn_confirmar = Button(rect, "Confirmar", self.font_btn, base_surf=btn_base, hover_surf=btn_hover)

        # 5. Cargar Imagen del Marco (¡NUEVO!)
        # === CAMBIO: Cargar dos imágenes separadas ===
        self.marco_h_img = load_image(self.assets_dir, ["marco_personaje_h"])
        self.marco_m_img = load_image(self.assets_dir, ["marco_personaje_m"])
        
        # === CAMBIO: Marcos más chicos (40% de la altura) ===
        box_h = int(self.h * 0.40) # Altura deseada para los marcos (Era 0.42)

        # Si no se encuentra el marco H, crear placeholder
        if not self.marco_h_img:
            print("WARN: No se encontró 'marco_personaje_h.png', usando placeholder.")
            self.marco_h_img = pygame.Surface((int(box_h * 0.75), box_h), pygame.SRCALPHA)
            self.marco_h_img.fill((87, 58, 44, 150)) # Placeholder
        else:
            # Escalar el marco H
            self.marco_h_img = scale_to_height(self.marco_h_img, box_h)

        # Si no se encuentra el marco M, crear placeholder
        if not self.marco_m_img:
            print("WARN: No se encontró 'marco_personaje_m.png', usando placeholder.")
            self.marco_m_img = pygame.Surface((int(box_h * 0.75), box_h), pygame.SRCALPHA)
            self.marco_m_img.fill((87, 58, 44, 150)) # Placeholder
        else:
            # Escalar el marco M
            self.marco_m_img = scale_to_height(self.marco_m_img, box_h)
            
        # 6. Cajas de Personajes (Nuevo Layout)
        # El área de la caja ahora se recalcula con el botón más arriba
        box_area_top = self.title_rect.bottom + int(self.h * 0.03)
        box_area_bottom = self.btn_confirmar.rect.top - int(self.h * 0.03)
        box_area_h = box_area_bottom - box_area_top
        
        # Usar el tamaño de los marcos cargados
        box_w_h = self.marco_h_img.get_width()
        box_w_m = self.marco_m_img.get_width()
        # box_h ya está definido
        
        gap = int(self.w * 0.1) # Espacio entre cajas
        total_boxes_w = box_w_h + box_w_m + gap
        
        start_x = (self.w - total_boxes_w) // 2
        box_y = box_area_top + (box_area_h - box_h) // 2 # Centrado vertical

        self.box_h_rect = pygame.Rect(start_x, box_y, box_w_h, box_h)
        self.box_m_rect = pygame.Rect(start_x + box_w_h + gap, box_y, box_w_m, box_h)
        

        # 7. Cargar Previews de Personajes
        # === CAMBIO: Reducir el tamaño del "espejo" para que quepa el personaje ===
        preview_max_w_h = int(self.box_h_rect.width * 0.35)  # Era 0.40
        preview_max_h_h = int(self.box_h_rect.height * 0.50) # Era 0.45
        preview_max_w_m = int(self.box_m_rect.width * 0.35)  # Era 0.40
        preview_max_h_m = int(self.box_m_rect.height * 0.50) # Era 0.45
        
        self.preview_h = _load_character_preview(assets_dir, "PERSONAJE H", preview_max_w_h, preview_max_h_h)
        self.preview_m = _load_character_preview(assets_dir, "PERSONAJE M", preview_max_w_m, preview_max_h_m)

        # 8. Estado
        self.selected_char: Optional[str] = None # Almacena "PERSONAJE H" o "PERSONAJE M"
        
        # === CAMBIO: Añadir botón de Regresar (btn_back) ===
        self.back_img = load_image(assets_dir, ["btn_back", "regresar", "btn_regresar", "back"])
        self.back_img_hover = None
        self.back_rect = pygame.Rect(0,0,1,1) # Dummy rect
        if self.back_img:
            desired_w = max(120, min(int(self.w * 0.12), 240))
            self.back_img = scale_to_width(self.back_img, desired_w)
            self.back_img_hover = scale_to_width(self.back_img, int(self.back_img.get_width() * 1.08))
            # === CAMBIO: Posición clásica en la esquina ===
            self.back_rect = self.back_img.get_rect(bottomleft=(10, self.h - 12))


    def _draw_scrolling_bg(self, dt: float):
        """Dibuja el fondo de tu juego con scroll"""
        self.bg_scroll_x = (self.bg_scroll_x - self.bg_speed*dt) % self.bg_scaled.get_width()
        x = -self.bg_scroll_x
        while x < self.w:
            self.screen.blit(self.bg_scaled, (int(x), 0)); x += self.bg_scaled.get_width()


    def run(self) -> Optional[str]:
        """
        Devuelve la carpeta del personaje seleccionada:
          -> "PERSONAJE H" ó "PERSONAJE M"
          -> None si el usuario sale
        """
        while True:
            dt = self.clock.tick(60) / 1000.0
            events = pygame.event.get()
            
            # --- Eventos ---
            mouse_pos = pygame.mouse.get_pos()
            clicked_back = False
            
            for ev in events:
                if ev.type == pygame.QUIT:
                    return None
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        play_sfx("back", self.assets_dir)
                        return None
                
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    # Hacemos clic en toda la caja del marco
                    if self.box_h_rect.collidepoint(mouse_pos):
                        self.selected_char = "PERSONAJE H"
                        play_sfx("select", self.assets_dir)
                    elif self.box_m_rect.collidepoint(mouse_pos):
                        self.selected_char = "PERSONAJE M"
                        play_sfx("select", self.assets_dir)
                    
                    # === CAMBIO: Comprobar clic en el botón Back ===
                    # Usamos 'current_back_rect' para la colisión
                    if self.back_rect.collidepoint(mouse_pos):
                         clicked_back = True

            # --- Botón Confirmar ---
            if self.btn_confirmar.update(events):
                if self.selected_char: # Solo funciona si se ha seleccionado uno
                    play_sfx("select", self.assets_dir)
                    # Devuelve la carpeta, no el nombre bonito
                    return self.selected_char 
                else:
                    play_sfx("back", self.assets_dir) # Sonido de "error" si no se ha elegido

            # === CAMBIO: Lógica del botón Back ===
            if clicked_back:
                play_sfx("back", self.assets_dir)
                return None
            
            # --- Dibujo ---
            self._draw_scrolling_bg(dt)

            # Título
            if self.title_img:
                self.screen.blit(self.title_img, self.title_rect)
            else:
                title = self.font_title.render("Elige tu personaje", True, (20,15,10))
                self.screen.blit(title, title.get_rect(center=(self.w//2, self.PAD_TOP + 20)))

            # --- Cajas de Personajes (NUEVA LÓGICA DE DIBUJO) ---
            
            # 1. Dibujar los marcos SEPARADOS
            self.screen.blit(self.marco_h_img, self.box_h_rect)
            self.screen.blit(self.marco_m_img, self.box_m_rect)

            # 2. Dibujar los previews de personajes (centrados dentro de CADA marco)
            # === CAMBIO: Centrar el personaje en el espejo ===
            center_h = (self.box_h_rect.centerx, self.box_h_rect.centery - int(self.h * 0.02))
            center_m = (self.box_m_rect.centerx, self.box_m_rect.centery - int(self.h * 0.02))
            
            img_rect_h = self.preview_h.get_rect(center=center_h)
            img_rect_m = self.preview_m.get_rect(center=center_m)
            self.screen.blit(self.preview_h, img_rect_h)
            self.screen.blit(self.preview_m, img_rect_m)

            # 3. Dibujar etiquetas de nombre (debajo de los marcos)
            # === CAMBIO: ELIMINADO EL BLOQUE DE TEXTO ===


            # 4. Dibujar Resalte (Highlight)
            COLOR_HIGHLIGHT = (255, 255, 255, 180) # Blanco semitransparente
            if self.selected_char == "PERSONAJE H":
                # Dibuja un rectángulo simple de selección alrededor del marco izquierdo
                pygame.draw.rect(self.screen, COLOR_HIGHLIGHT, self.box_h_rect.inflate(6,6), 5, 10)
            elif self.selected_char == "PERSONAJE M":
                # Dibuja un rectángulo simple de selección alrededor del marco derecho
                pygame.draw.rect(self.screen, COLOR_HIGHLIGHT, self.box_m_rect.inflate(6,6), 5, 10)

            # Botón confirmar
            self.btn_confirmar.draw(self.screen)
            
            # === CAMBIO: Dibujar botón Back (lógica corregida) ===
            if self.back_img and self.back_img_hover:
                if self.back_rect.collidepoint(mouse_pos):
                    # Dibuja el hover centrado en la posición base
                    r = self.back_img_hover.get_rect(center=self.back_rect.center)
                    self.screen.blit(self.back_img_hover, r)
                else:
                    self.screen.blit(self.back_img, self.back_rect)


            pygame.display.flip()