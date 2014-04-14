'''Basic platforming game.

Developed for the Intro to Game Programming tutorial at US PyCon 2012.

Copyright 2012 Richard Jones <richard@mechanicalcat.net>
This code is placed in the Public Domain.
'''
import pygame
import tmx

#
# Our enemies are quite dumb, just moving from side to side between "reverse"
# map triggers. It's game over if they hit the player.
#
class Enemy(pygame.sprite.Sprite):
    image = pygame.image.load('enemy.png')
    def __init__(self, location, *groups):
        super(Enemy, self).__init__(*groups)
        self.rect = pygame.rect.Rect(location, self.image.get_size())
        # movement in the X direction; postive is right, negative is left
        self.direction = 1

    def update(self, dt, game):
        # move the enemy by 100 pixels per second in the movement direction
        self.rect.x += self.direction * 100 * dt

        # check all reverse triggers in the map to see whether this enemy has
        # touched one
        for cell in game.tilemap.layers['triggers'].collide(self.rect, 'reverse'):
            # reverse movement direction; make sure to move the enemy out of the
            # collision so it doesn't collide again immediately next update
            if self.direction > 0:
                self.rect.right = cell.left
            else:
                self.rect.left = cell.right
            self.direction *= -1
            break

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
    def __init__(self, location, direction, *groups):
        super(Bullet, self).__init__(*groups)
        self.rect = pygame.rect.Rect(location, self.image.get_size())
        # movement in the X direction; postive is right, negative is left;
        # inherited from the player (shooter)
        self.direction = direction
        # time this bullet will live for in seconds
        self.lifespan = 1

    def update(self, dt, game):
        # decrement the lifespan of the bullet by the amount of time passed and
        # remove it from the game if its time runs out
        self.lifespan -= dt
        if self.lifespan < 0:
            self.kill()
            return

        # move the enemy by 400 pixels per second in the movement direction
        self.rect.x += self.direction * 400 * dt

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
    def __init__(self, location, *groups):
        super(Player, self).__init__(*groups)
        self.image = pygame.image.load('player-right.png')
        self.right_image = self.image
        self.left_image = pygame.image.load('player-left.png')
        self.rect = pygame.rect.Rect(location, self.image.get_size())
        # is the player resting on a surface and able to jump?
        self.resting = False
        # player's velocity in the Y direction
        self.dy = 0
        # is the player dead?
        self.is_dead = False
        # movement in the X direction; postive is right, negative is left
        self.direction = 1
        # time since the player last shot
        self.gun_cooldown = 0

    def update(self, dt, game):
        # take a copy of the current position of the player before movement for
        # use in movement collision response
        last = self.rect.copy()

        # handle the player movement left/right keys
        key = pygame.key.get_pressed()
        if key[pygame.K_LEFT]:
            self.rect.x -= 300 * dt
            self.image = self.left_image
            self.direction = -1
        if key[pygame.K_RIGHT]:
            self.rect.x += 300 * dt
            self.image = self.right_image
            self.direction = 1

        # handle the player shooting key
        if key[pygame.K_LSHIFT] and not self.gun_cooldown:
            # create a bullet at an appropriate position (the side of the player
            # sprite) and travelling in the correct direction
            if self.direction > 0:
                Bullet(self.rect.midright, 1, game.sprites)
            else:
                Bullet(self.rect.midleft, -1, game.sprites)
            # set the amount of time until the player can shoot again
            self.gun_cooldown = 1
            game.shoot.play()

        # decrement the time since the player last shot to a minimum of 0 (so
        # boolean checks work)
        self.gun_cooldown = max(0, self.gun_cooldown - dt)

        # if the player's allowed to let them jump with the spacebar; note that
        # wall-jumping could be allowed with an additional "touching a wall"
        # flag
        if self.resting and key[pygame.K_SPACE]:
            game.jump.play()
            # we jump by setting the player's velocity to something large going
            # up (positive Y is down the screen)
            self.dy = -500

        # add gravity on to the currect vertical speed
        self.dy = min(400, self.dy + 40)

        # now add the distance travelled for this update to the player position
        self.rect.y += self.dy * dt

        # collide the player with the map's blockers
        new = self.rect
        # reset the resting trigger; if we are at rest it'll be set again in the
        # loop; this prevents the player from being able to jump if they walk
        # off the edge of a platform
        self.resting = False
        # look up the tilemap triggers layer for all cells marked "blockers"
        for cell in game.tilemap.layers['triggers'].collide(new, 'blockers'):
            # find the actual value of the blockers property
            blockers = cell['blockers']
            # now for each side set in the blocker check for collision; only
            # collide if we transition through the blocker side (to avoid
            # false-positives) and align the player with the side collided to
            # make things neater
            if 'l' in blockers and last.right <= cell.left and new.right > cell.left:
                new.right = cell.left
            if 'r' in blockers and last.left >= cell.right and new.left < cell.right:
                new.left = cell.right
            if 't' in blockers and last.bottom <= cell.top and new.bottom > cell.top:
                self.resting = True
                new.bottom = cell.top
                # reset the vertical speed if we land or hit the roof; this
                # avoids strange additional vertical speed if there's a
                # collision and the player then leaves the platform
                self.dy = 0
            if 'b' in blockers and last.top >= cell.bottom and new.top < cell.bottom:
                new.top = cell.bottom
                self.dy = 0

        # re-focus the tilemap viewport on the player's new position
        game.tilemap.set_focus(new.x, new.y)

#
# Our game class represents one loaded level of the game and stores all the
# actors and other game-level state.
#
class Game(object):
    def main(self, screen):
        # grab a clock so we can limit and measure the passing of time
        clock = pygame.time.Clock()

        # we draw the background as a static image so we can just load it in the
        # main loop
        background = pygame.image.load('background.png')

        # load our tilemap and set the viewport for rendering to the screen's
        # size
        self.tilemap = tmx.load('map-enemies.tmx', screen.get_size())

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
        # add an enemy for each "enemy" trigger in the map
        for enemy in self.tilemap.layers['triggers'].find('enemy'):
            Enemy((enemy.px, enemy.py), self.enemies)

        # load the sound effects used in playing a level of the game
        self.jump = pygame.mixer.Sound('jump.wav')
        self.shoot = pygame.mixer.Sound('shoot.wav')
        self.explosion = pygame.mixer.Sound('explosion.wav')

        while 1:
            # limit updates to 30 times per second and determine how much time
            # passed since the last update
            dt = clock.tick(30)

            # handle basic game events; terminate this main loop if the window
            # is closed or the escape key is pressed
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return

            # update the tilemap and everything in it passing the elapsed time
            # since the last update (in seconds) and this Game object
            self.tilemap.update(dt / 1000., self)
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

            if self.tilemap.layers['triggers'].collide(self.player.rect, 'exit'):
                print 'YOU WIN'
                return

if __name__ == '__main__':
    # if we're invoked as a program then initialise pygame, create a window and
    # run the game
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    Game().main(screen)

