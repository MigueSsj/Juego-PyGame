import pygame
import sys
from pathlib import Path

# === CONFIGURACIÓN ===
NOMBRE_IMAGEN = "original.jpg" 
# Usamos la resolución de tu juego para que las coordenadas coincidan
ANCHO_JUEGO = 1280  
ALTO_JUEGO = 720    

def run():
    pygame.init()
    BASE_DIR = Path(__file__).resolve().parent
    ASSETS = BASE_DIR / "assets"
    
    img_path = None
    for ext in [".jpg", ".png", ".jpeg"]:
        p = ASSETS / f"{Path(NOMBRE_IMAGEN).stem}{ext}"
        if p.exists():
            img_path = p
            break
    
    if not img_path:
        print(f"ERROR: No encontré '{NOMBRE_IMAGEN}' en assets.")
        return

    # Cargar y ESCALAR la imagen al tamaño del juego
    bg_raw = pygame.image.load(str(img_path))
    bg = pygame.transform.smoothscale(bg_raw, (ANCHO_JUEGO, ALTO_JUEGO))
    
    # === MODO PANTALLA COMPLETA ===
    # Esto forzará a que se vea en toda tu pantalla
    screen = pygame.display.set_mode((ANCHO_JUEGO, ALTO_JUEGO), pygame.FULLSCREEN)
    pygame.display.set_caption("DIBUJA LAS 4 ZONAS (Espacio: Guardar, R: Reiniciar, ESC: Salir)")
    
    zones = []
    zone_names = [
        "1. Arriba Izquierda (TL)", 
        "2. Arriba Medio (TM)", 
        "3. Abajo Izquierda (BL)", 
        "4. Abajo Derecha (BR)"
    ]
    current_idx = 0
    
    start_pos = None
    current_rect = None
    font = pygame.font.SysFont("arial", 24, bold=True)
    font_big = pygame.font.SysFont("arial", 40, bold=True)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                
                if event.key == pygame.K_SPACE:
                    if current_rect:
                        zones.append(current_rect)
                        print(f"Guardada: {zone_names[current_idx]}")
                        current_idx += 1
                        start_pos = None
                        current_rect = None
                        
                        if current_idx >= len(zone_names):
                            print("\n" + "="*50)
                            print("¡COPIA Y PEGA ESTO EN TU NIVEL3_DIFICIL.PY!")
                            print("="*50)
                            print("    # Zonas Personalizadas (Generadas)")
                            print("    zones = {")
                            print(f"        'TL': pygame.Rect{zones[0]},")
                            print(f"        'TM': pygame.Rect{zones[1]},")
                            print(f"        'BL': pygame.Rect{zones[2]},")
                            print(f"        'BR': pygame.Rect{zones[3]}")
                            print("    }")
                            print("="*50)
                            running = False
                            
                if event.key == pygame.K_r:
                    start_pos = None
                    current_rect = None

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Clic izquierdo
                    start_pos = event.pos
                    current_rect = None
                
            elif event.type == pygame.MOUSEMOTION:
                if start_pos and pygame.mouse.get_pressed()[0]:
                    x = min(start_pos[0], event.pos[0])
                    y = min(start_pos[1], event.pos[1])
                    w = abs(start_pos[0] - event.pos[0])
                    h = abs(start_pos[1] - event.pos[1])
                    current_rect = pygame.Rect(x, y, w, h)

        screen.blit(bg, (0,0))
        
        # Zonas guardadas (Verde)
        for z in zones:
            s = pygame.Surface((z.width, z.height), pygame.SRCALPHA)
            s.fill((0, 255, 0, 80))
            screen.blit(s, z.topleft)
            pygame.draw.rect(screen, (0, 255, 0), z, 3)

        # Zona actual (Amarillo)
        if current_rect:
            s = pygame.Surface((current_rect.width, current_rect.height), pygame.SRCALPHA)
            s.fill((255, 255, 0, 80))
            screen.blit(s, current_rect.topleft)
            pygame.draw.rect(screen, (255, 255, 0), current_rect, 3)

        # HUD
        if current_idx < len(zone_names):
            # Fondo negro semitransparente para el texto
            pygame.draw.rect(screen, (0,0,0,180), (0, 0, ANCHO_JUEGO, 60))
            
            msg = f"DIBUJA: {zone_names[current_idx]}"
            txt = font_big.render(msg, True, (255, 255, 0))
            screen.blit(txt, (20, 10))
            
            instr = font.render("Arrastra mouse | Espacio: Guardar | R: Reintentar | ESC: Salir", True, (255, 255, 255))
            screen.blit(instr, (ANCHO_JUEGO - instr.get_width() - 20, 15))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    run()