import pygame
pygame.init()

# Carga la imagen (sin convert todavía)
background = pygame.image.load("assets/fondo.jpeg")

# Haz la ventana exactamente del tamaño de la imagen
w, h = background.get_size()
screen = pygame.display.set_mode((w, h))
pygame.display.set_caption("pygame window")
clock = pygame.time.Clock()

# Ahora sí convertimos, ya que la ventana existe
background = background.convert()

done = False
while not done:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True

    screen.blit(background, (0, 0))
    pygame.display.flip()
    clock.tick(60)

pygame.quit()

