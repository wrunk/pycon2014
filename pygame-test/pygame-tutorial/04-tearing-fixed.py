import pygame

pygame.init()
screen = pygame.display.set_mode((640, 480), pygame.HWSURFACE|pygame.FULLSCREEN|pygame.DOUBLEBUF)

RED = (255, 0, 0)
BLUE = (0, 0, 255)
color = RED

clock = pygame.time.Clock()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
    clock.tick(30)
    screen.fill(color)
    if color is BLUE:
        color = RED
    else:
        color = BLUE
    pygame.display.flip()
