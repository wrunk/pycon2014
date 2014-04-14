import pygame
import random

pygame.init()

screen = pygame.display.set_mode((480, 640))


class MySprite(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super(MySprite, self).__init__()
        self.rect = self.rect.copy()
        self.rect.topleft = (x, y)


class BottomPipe(MySprite):
    image = pygame.image.load('pipe.png')
    rect = image.get_rect()


class TopPipe(MySprite):
    image = pygame.transform.flip(BottomPipe.image, False, True)
    rect = image.get_rect()


class Ground(MySprite):
    image = pygame.image.load('ground.png')
    rect = image.get_rect()


class Bird(MySprite):
    bird = pygame.image.load('bird.png')
    bird_flap = pygame.image.load('bird_flap.png')
    rect = pygame.rect.Rect(0, 5, 32, 18)
    dy = 0

    def draw(self, surface, distance):
        self.rect.x = distance + 210
        if self.dy < 0:
            image = self.bird_flap
        else:
            image = self.bird
        surface.blit(image, (self.rect.x - distance, self.rect.y))


class ScrolledGroup(pygame.sprite.Group):
    def draw(self, surface, distance):
        for sprite in self.sprites():
            surface.blit(sprite.image, (sprite.rect.x - distance,
                sprite.rect.y))


class PipesGroup(ScrolledGroup):
    last_add = None

    def update(self, distance):
        for pipe in self.sprites():
            if pipe.rect.right < distance:
                pipe.kill()
        if self.last_add is None:
            self.last_add = self.sprites()[-1].rect.right
        if distance > self.last_add - 300:
            self.last_add = x = distance + 480
            y = random.randint(-GAP, GAP)
            self.add(BottomPipe(x,
                640 + y - BottomPipe.rect.height + GAP))
            self.add(TopPipe(x, y - GAP))


class GroundGroup(ScrolledGroup):
    def update(self, distance):
        for ground in self.sprites():
            if ground.rect.right < distance:
                ground.kill()
                self.add(Ground(self.sprites()[0].rect.right,
                    640 - Ground.rect.height))

GAP = 64


def play():
    distance = 100
    bird = Bird(210, 320)
    pipes = PipesGroup(BottomPipe(480, 640 - BottomPipe.rect.height + GAP),
        TopPipe(480, -GAP))
    ground = GroundGroup(Ground(0, 640 - Ground.rect.height),
        Ground(Ground.rect.width, 640 - Ground.rect.height))
    while 1:
        bird.dy += 1.5
        distance += 3

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_SPACE:
                    bird.dy = -15

        ground.update(distance)
        pipes.update(distance)
        bird.rect.y += bird.dy

        if (pygame.sprite.spritecollide(bird, ground, False) or
                pygame.sprite.spritecollide(bird, pipes, False)):
            print 'FAIL at distance', distance
            return

        screen.fill((100, 100, 255))
        pipes.draw(screen, distance)
        ground.draw(screen, distance)
        bird.draw(screen, distance)
        pygame.display.flip()

if __name__ == '__main__':
    play()
