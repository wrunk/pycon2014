'''Basic side-scolling shooter game.

Developed for the Intro to Game Programming tutorial at US PyCon 2012.

Copyright 2012 Richard Jones <richard@mechanicalcat.net>
This code is placed in the Public Domain.
'''
import pygame
import tmx

#
# Our enemies appear on the right-hand side of the screen when their triggers
# become exposed. They move slowly left until they are no longer on the or die.
#
class Enemy(pygame.sprite.Sprite):
    image = pygame.image.load('enemy.png')
    def __init__(self, location, *groups):
        super(Enemy, self).__init__(*groups)
        self.rect = pygame.rect.Rect(location, self.image.get_size())

    def update(self, dt, game):
        # move the enemy by 50 pixels per second
        self.rect.x += -50 * dt

        # check for collision with the player; on collision mark the flag on the
        # player to indicate game over (a health level could be decremented here
        # instead)
        if self.rect.colliderect(game.player.rect):
            game.player.is_dead = True

#
# Bullets fired by the player move in one direction until their lifespan runs
# out or they hit an enemy. This could be extended to allow for enemy bullets.
#
class Bullet(pygame.sprite.Sprite):
    image = pygame.image.load('bullet.png')
    def __init__(self, location, *groups):
        super(Bullet, self).__init__(*groups)
        self.rect = pygame.rect.Rect(location, self.image.get_size())
        # time this bullet will live for in seconds
        self.lifespan = 1

    def update(self, dt, game):
        # decrement the lifespan of the bullet by the amount of time passed and
        # remove it from the game if its time runs out
        self.lifespan -= dt
        if self.lifespan < 0:
            self.kill()
            return

        # move the enemy by 400 pixels per second
        self.rect.x += 400 * dt

        # check for collision with any of the enemy sprites; we pass the "kill
        # if collided" flag as True so any collided enemies are removed from the
        # game
        if pygame.sprite.spritecollide(self, game.enemies, True):
            game.explosion.play()
            # we also remove the bullet from the game or it will continue on
            # until its lifespan expires
            self.kill()

#
# Our player of the game represented as a sprite with many attributes and user
# control.
#
class Player(pygame.sprite.Sprite):
    image = pygame.image.load('ship.png')
    def __init__(self, location, *groups):
        super(Player, self).__init__(*groups)
        self.rect = pygame.rect.Rect(location, self.image.get_size())
        # is the player dead?
        self.is_dead = False
        # time since the player last shot
        self.gun_cooldown = 0

    def update(self, dt, game):
        # handle the player movement keys
        key = pygame.key.get_pressed()
        dx = 100
        dy = 0
        if key[pygame.K_LEFT]: dx -= 200
        if key[pygame.K_RIGHT]: dx += 200
        if key[pygame.K_UP]: dy -= 200
        if key[pygame.K_DOWN]: dy += 200
        self.rect.x += int(dx * dt)
        self.rect.y += int(dy * dt)

        # keep the player from moving off-screen
        viewport = game.tilemap.viewport
        if self.rect.bottom > viewport.bottom:
            self.rect.bottom = viewport.bottom
        elif self.rect.top < viewport.top:
            self.rect.top = viewport.top
        if self.rect.left < viewport.left:
            self.rect.left = viewport.left
        elif self.rect.right > viewport.right:
            self.rect.right = viewport.right

        # handle the player shooting key
        if key[pygame.K_LSHIFT] and not self.gun_cooldown:
            Bullet(self.rect.midright, game.sprites)
            # set the amount of time until the player can shoot again
            self.gun_cooldown = .2
            game.shoot.play()

        # decrement the time since the player last shot to a minimum of 0 (so
        # boolean checks work)
        self.gun_cooldown = max(0, self.gun_cooldown - dt)

        # if the player touches any of the map blockers they die
        if game.tilemap.layers['triggers'].collide(self.rect, 'blockers'):
            self.is_dead = True

        if game.tilemap.layers['triggers'].collide(self.rect, 'exit'):
            game.won = True

#
# Our game class represents one loaded level of the game and stores all the
# actors and other game-level state.
#
class Game(object):
    def main(self, screen):
        self.screen = screen

        # grab a clock so we can limit and measure the passing of time
        clock = pygame.time.Clock()

        # we draw the background as a static image so we can just load it in the
        # main loop
        background = pygame.image.load('background.png')

        # load our tilemap and set the viewport for rendering to the screen's
        # size
        self.tilemap = tmx.load('scroller.tmx', screen.get_size())

        # add a layer for our sprites controlled by the tilemap scrolling
        self.sprites = tmx.SpriteLayer()
        self.tilemap.layers.append(self.sprites)
        # fine the player start cell in the triggers layer
        start_cell = self.tilemap.layers['triggers'].find('player')[0]
        # use the "pixel" x and y coordinates for the player start
        self.player = Player((start_cell.px, start_cell.py), self.sprites)

        # add a separate layer for enemies so we can find them more easily later
        self.enemies = tmx.SpriteLayer()
        self.tilemap.layers.append(self.enemies)

        # load the sound effects used in playing a level of the game
        self.jump = pygame.mixer.Sound('jump.wav')
        self.shoot = pygame.mixer.Sound('shoot.wav')
        self.explosion = pygame.mixer.Sound('explosion.wav')

        # flag to allow us to detect when the player completes the level
        self.won = False

        # start the view focus at the player spawn point
        view_x = start_cell.px
        while 1:
            # limit updates to 30 times per second and determine how much time
            # passed since the last update; convert the milliseconds value to
            # seconds
            dt = clock.tick(30)/1000.

            # handle basic game events; terminate this main loop if the window
            # is closed or the escape key is pressed
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return

            # move the view at a fixed rate; round to int so we don't introduce
            # any floating-point accumulation problems
            view_x += int(100 * dt)
            self.tilemap.set_focus(view_x, start_cell.py)

            # update the tilemap and everything in it passing the elapsed time
            # since the last update (in seconds) and this Game object
            self.tilemap.update(dt, self)

            # add an enemy for each "enemy" trigger that has been exposed
            for cell in self.tilemap.layers['triggers'].collide(self.tilemap.viewport, 'enemy'):
                # delete the enemy trigger so we don't make another one
                del cell['enemy']
                Enemy((cell.px+32, cell.py), self.enemies)

            # construct the scene by drawing the background and then the rest of
            # the game imagery over the top
            screen.blit(background, (0, 0))
            self.tilemap.draw(screen)
            pygame.display.flip()

            # terminate this main loop if the player dies; a simple change here
            # could be to replace the "print" with the invocation of a simple
            # "game over" scene
            if self.player.is_dead:
                print 'YOU DIED'
                return

            # terminate this main loop if the player wins
            if self.won:
                print 'YOU WIN'
                return

if __name__ == '__main__':
    # if we're invoked as a program then initialise pygame, create a window and
    # run the game
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    Game().main(screen)

