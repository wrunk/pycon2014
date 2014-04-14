from __future__ import division

import os
import random

import pygame

from lepton import ParticleGroup, Particle
from lepton import controller, domain, emitter
from lepton.domain import Sphere, Point, Disc, Line, AABox

class Effect(object):
    t = 0
    def update(self, dt):
        self.t += dt
        self.group.update(dt)

class Render(object):
    def __init__(self, filename):
        self.image = pygame.image.load(filename)
    def draw(self, group):
        for particle in group:
            if particle.color[-1] != 1:
                im = self.image.copy()
                alpha = pygame.surfarray.pixels_alpha(im)
                alpha *= particle.color[-1]
                # have to delete the surfarray to make it release its lock(!)
                del alpha
            else:
                im = self.image
            screen.blit(im, (particle.position.x, particle.position.y))

class SmokePuff(Effect):
    def __init__(self, x, y, size):
        self.emitter = emitter.StaticEmitter(
            template = Particle(
                position=(x, y, 0),
                color=(1, 1, 1, .01),
                velocity=(0, 0, 0),
                size=(64, 64, 0),
            ),
            velocity=Disc((0,0,0), (0,0,1), 400),
        )
        self.group = ParticleGroup(
            controllers=[
                self.emitter,
                controller.Growth(50),
                controller.Movement(),
                controller.Fader(start_alpha=1,fade_out_start=0,fade_out_end=.7,end_alpha=0),
                controller.Lifetime(.7),
            ],
            renderer = Render('point64.png'),
        )
        self.emitter.emit(50, self.group)

    def stop(self):
        self.emitter.rate = 0

class Zap(Effect):
    duration = .5
    def __init__(self, x, y, direction):
        self.x, self.y = (x, y)
        self.direction = direction
        if direction < 0: self.speed = -800
        else: self.speed = 800

        self.emitter = emitter.StaticEmitter(
          rate=300,
          template=Particle(
              position=(x, y, 0),
              velocity=(0, 0, 0),
              color=(1, 1, 0, 0.5),
              size=(8, 8, 0),
              # rotation?
              # up?
          ),
          velocity=Disc((0,0,0), (0,0,1), 200),
          time_to_live=self.duration,
        )
        self.fader = controller.Fader(start_alpha=1,fade_out_start=0,fade_out_end=.5,end_alpha=0)

        self.group = ParticleGroup(
            controllers=[
                self.emitter,
                controller.Gravity((0, -100, 0)),
                controller.Movement(),
                self.fader,
                controller.Lifetime(1),
            ],
            renderer=Render('zap-star.png'),
        )
        self.emitter.emit(1, self.group)

    def update(self, dt):
        super(Zap, self).update(dt)
        self.x += dt * self.speed
        self.emitter.template.position = (self.x, self.y, 0)

    def stop(self):
        self.emitter.rate = 0

class Sparkle(Effect):
    filename = 'pickup-star.png'
    def __init__(self, rect, scale=1):
        x, y = rect.center
        self.emitter = emitter.StaticEmitter(
            rate = 20,
            template = Particle(
                position=(x, y, 0),
                color=(1, 1, 1, .5),
                velocity=(0, 0, 0),
                size=(8, 8, 0),
            ),
            velocity=Disc((0,0,0), (0,0,1), rect.width*.75*scale),
        )
        self.group = ParticleGroup(
            controllers=[
                self.emitter,
                controller.Movement(),
                controller.Clumper(50),
                controller.Fader(start_alpha=1,fade_out_start=0,fade_out_end=1,end_alpha=0),
                controller.Lifetime(1),
            ],
            renderer = Render(self.filename),
        )
        self.emitter.emit(1, self.group)

    def stop(self):
        self.emitter.rate = 0

class YuckPool(Effect):
    def __init__(self, x1, y1, x2, y2):
        self.emitter = emitter.StaticEmitter(
            rate = (x2-x1) // 5,
            template = Particle(
                position=(x1, y1, 0),
                color=(1, 1, 1, .5),
                velocity=(0, 0, 0),
                size=(32, 32, 0),
            ),
            position=Line((x1, y1, 0), (x2, y1, 0)),
            velocity=AABox((-100, -50, 0), (100, -200, 1)),
        )
        self.group = ParticleGroup(
            controllers=[
                self.emitter,
                controller.Movement(),
                controller.Growth(100),
                controller.Gravity((0, -50, 0)),
                controller.Fader(start_alpha=1,fade_out_start=0,fade_out_end=1,end_alpha=0),
                controller.Lifetime(2),
            ],
            renderer = Render('black-bubble.png'),
        )
        self.emitter.emit(1, self.group)

    def stop(self):
        self.emitter.rate = 0

if __name__ == '__main__':
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    clock = pygame.time.Clock()
    running = True
    o = SmokePuff(320, 240, 50)
    n = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                n += 1
                if n == 1:
                    o = YuckPool(270, 250, 370, 200)
                elif n == 2:
                    o = Sparkle(pygame.rect.Rect(100, 100, 150, 150))
                elif n == 3:
                    o = Zap(100, 240, 1)
                else:
                    o = SmokePuff(320, 240, 50)
                    n = 0

        dt = clock.tick(30) / 1000.
        o.update(dt)
        screen.fill((100, 100, 100))
        o.group.draw()
        pygame.display.flip()

