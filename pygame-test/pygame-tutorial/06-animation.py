import pygame

class Game(object):
    def main(self, screen):
        clock = pygame.time.Clock()

        image = pygame.image.load('player.png')
        image_x = 320
        image_y = 240

        while 1:
            clock.tick(30)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return

            image_x += 10

            screen.fill((200, 200, 200))
            screen.blit(image, (image_x, image_y))
            pygame.display.flip()

if __name__ == '__main__':
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    Game().main(screen)

