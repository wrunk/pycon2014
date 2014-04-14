#!/usr/bin/python

import math
import tmx
import pygame

class CarSprite(pygame.sprite.Sprite):
    TOP_SPEED = 10
    REVERSE_TOP_SPEED = 10
    ACCELERATION = 20
    TURN_SPEED = 200

    def __init__(self, *groups):
        super(CarSprite, self).__init__(*groups)
        self.src_image = pygame.image.load('car.png')
        self.rect = self.src_image.get_rect()

        self.position = (64, 64)
        self.speed = 0
        self.direction = -90
        self.acc = 0
        self.turn = 0

    def update(self, dt):
        pressed = pygame.key.get_pressed()
        self.turn = 0
        if pressed[pygame.K_RIGHT]:
            self.turn -= self.TURN_SPEED
        if pressed[pygame.K_LEFT]:
            self.turn += self.TURN_SPEED
        if pressed[pygame.K_UP]:
            self.acc += self.ACCELERATION
        if pressed[pygame.K_DOWN]:
            self.acc -= self.ACCELERATION

        self.speed += self.acc * dt
        if self.speed > self.TOP_SPEED:
            self.speed = self.TOP_SPEED
        if self.speed < -self.REVERSE_TOP_SPEED:
            self.speed = -self.REVERSE_TOP_SPEED
        self.direction += self.turn * dt
        x, y = self.position
        rad = self.direction * math.pi / 180
        x += -self.speed * math.sin(rad)# * dt
        y += -self.speed * math.cos(rad)# * dt
        self.position = (x, y)

        self.image = pygame.transform.rotate(self.src_image, self.direction)
        self.rect.size = self.image.get_size()
        self.rect.center = map(int, self.position)

def main():
    screen = pygame.display.set_mode((800, 600))

    map = tmx.load('driving-map.tmx', screen.get_size())
    sprites = tmx.SpriteLayer()
    map.layers.append(sprites)
    car = CarSprite(sprites)

    clock = pygame.time.Clock()
    while True:
        dt = clock.tick(30) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return

        screen.fill((50,50,50))
        map.update(dt)
        map.set_focus(*car.rect.center)
        map.draw(screen)
        pygame.display.flip()

if __name__ == '__main__':
    pygame.init()
    main()

