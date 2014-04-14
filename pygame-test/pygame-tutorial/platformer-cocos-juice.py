'''Basic platforming game.

Developed for the Intro to Game Programming tutorial at US PyCon 2012.

Copyright 2012 Richard Jones <richard@mechanicalcat.net>
This code is placed in the Public Domain.
'''
import pyglet
import cocos
from cocos.director import director
from pyglet.window import key
from cocos.actions import *
from cocos import particle_systems
from cocos import particle
from cocos import euclid

# load the sound effects used in playing a level of the game
jump = pyglet.resource.media('jump.wav', streaming=False)
shoot = pyglet.resource.media('shoot.wav', streaming=False)
explosion = pyglet.resource.media('explosion.wav', streaming=False)

player_right = pyglet.resource.image('player-right.png')
player_left = pyglet.resource.image('player-left.png')


#
# Our enemies are quite dumb, just moving from side to side between "reverse"
# map triggers. It's game over if they hit the player.
#
class EnemyUpdate(cocos.actions.Move):
    def step(self, dt):
        super(EnemyUpdate, self).step(dt)

        enemy = self.target

        # check all reverse triggers in the map to see whether this enemy has
        # touched one
        (dx, dy) = enemy.velocity
        for cell in director.scene.reversers:
            if not cell.contains(enemy.x, enemy.y):
                continue
            # reverse movement direction; make sure to move the enemy out of
            # the collision so it doesn't collide again immediately next update
            if dx > 0:
                enemy.x = cell.left - 1
            else:
                enemy.x = cell.right + 1
            dx *= -1
            enemy.velocity = (dx, dy)
            break

        # check for collision with the player; on collision mark the flag on
        # the player to indicate game over (a health level could be decremented
        # here instead)
        player = director.scene.player
        if enemy.get_rect().intersects(player.get_rect()):
            print("You died!")
            director.pop()
            player.is_dead = True


#
# Bullets fired by the player move in one direction until their lifespan runs
# out or they hit an enemy. This could be extended to allow for enemy bullets.
#
class BulletUpdate(cocos.actions.Move):
    def step(self, dt):
        super(BulletUpdate, self).step(dt)
        # check for collision with any of the enemy sprites; we pass the "kill
        # if collided" flag as True so any collided enemies are removed from
        # the game
        r = self.target.get_rect()
        for z, enemy in director.scene.enemies.children:
            if r.intersects(enemy.get_rect()):
                self.target.kill()
                enemy.do(ScaleBy(2, 1) | RotateBy(720, 1) | FadeOut(.5) +
                    CallFunc(enemy.kill))
                explosion.play()
                enemy.add(EnemyExplosion())
                break


class EnemyExplosion(particle_systems.Explosion):
    life = .2
    life_var = .1


class Trail(particle_systems.Explosion):
    # customise an Explosion particle system to emit sparks
    angle = 180
    angle_var = 5
    speed = 250
    speed_var = 50
    gravity = euclid.Point2(0, 0)
    duration = 1.
    start_color = particle.Color(1, 1, 1, .5)
    start_color_var = particle.Color(0, 0, 0, 0.0)
    end_color = particle.Color(1.0, 1.0, 1.0, 0.0)
    end_color_var = particle.Color(0, 0, 0, 0)
    emission_rate = 20
    size = 10
    size_var = 5


#
# Our player of the game represented as a sprite with many attributes and user
# control.
#
class UpdatePlayer(cocos.actions.Move):
    def start(self):
        self.collider = Collide(self.target)
        # is the player dead?
        self.is_dead = False
        # movement in the X direction; postive is right, negative is left
        self.direction = 1
        # time since the player last shot
        self.gun_cooldown = 0

    def step(self, dt):
        player = self.target

        # first, handle the player's input (left, right, jump)
        dx, dy = player.velocity

        dx = 0
        if keys[key.LEFT]:
            dx = -180
            self.target.image = player_left
            self.direction = -1
        if keys[key.RIGHT]:
            dx = 180
            self.target.image = player_right
            self.direction = 1

        # if the player's allowed to let them jump with the spacebar; note that
        # wall-jumping could be allowed with an additional "touching a wall"
        # flag
        if self.collider.resting and keys[key.SPACE]:
            jump.play()
            # we jump by setting the player's velocity to something large going
            # up (positive Y is down the screen)
            dy = 700

        player.velocity = dx, dy

        # get the current position as pre-movement
        #print player.position
        last = player.get_rect()

        # update movement kinematically
        super(UpdatePlayer, self).step(dt)

        # now figure any collision that's happened
        dx, dy = player.velocity
        now = player.get_rect()
        self.collider.collide_map(director.scene.triggers, last,
            now, dy, dx)

        # move the player to the potentially-modified "now" position
        player.position = now.midbottom

        # handle the player shooting key
        if keys[key.LSHIFT] and not self.gun_cooldown:
            # create a bullet at an appropriate position (the side of the
            # player sprite) and travelling in the correct direction
            bullet = cocos.sprite.Sprite('bullet.png')
            if self.direction > 0:
                bullet.position = now.midright
                bullet.velocity = (400, 0)
            else:
                bullet.position = now.midleft
                bullet.velocity = (-400, 0)
            director.scene.sprites.add(bullet)
            lifespan = 1
            kill = Delay(lifespan) + CallFunc(bullet.kill)
            bullet.do(BulletUpdate() | kill)

            trail = Trail()
            trail.speed *= self.direction
            trail.speed_var *= self.direction
            bullet.add(trail)
            trail.auto_remove_on_finish = True

            # set the amount of time until the player can shoot again
            self.gun_cooldown = 1
            shoot.play()

        # decrement the time since the player last shot to a minimum of 0 (so
        # boolean checks work)
        self.gun_cooldown = max(0, self.gun_cooldown - dt)

        # re-focus the tilemap viewport on the player's new position
        director.scene.scroller.set_focus(*player.position)


# use the standard collider and set the sprite's velocity according to the
# sides it collides with
class Collide(cocos.tiles.TmxObjectMapCollider):
    def __init__(self, sprite):
        self.sprite = sprite

    def collide_bottom(self, dy):
        self.sprite.velocity = (self.sprite.velocity[0], 0)
        self.resting = True

    def collide_left(self, dx):
        self.sprite.velocity = (0, self.sprite.velocity[1])

    def collide_right(self, dx):
        self.sprite.velocity = (0, self.sprite.velocity[1])

    def collide_top(self, dy):
        self.sprite.velocity = (self.sprite.velocity[0], 0)


class Platforming(cocos.scene.Scene):
    def __init__(self):
        super(Platforming, self).__init__()
        self.scroller = cocos.layer.ScrollingManager()

        # load the level and add that to the scene
        tilemap = cocos.tiles.load('map-enemies.tmx')
        self.level = tilemap['set']
        self.scroller.add(self.level)

        self.triggers = tilemap['triggers']
        self.scroller.add(self.triggers)

        # create the "player" sprite
        self.sprites = cocos.layer.ScrollableLayer()
        cell = self.triggers.find_cells(player='yes')[0]
        self.player = cocos.sprite.Sprite(player_right, cell.midbottom,
            anchor=(player_right.width / 2, 0))
        self.player.velocity = (0, 0)
        self.player.gravity = -2000
        self.player.facing = 1
        self.sprites.add(self.player)
        self.player.do(UpdatePlayer())

        self.scroller.add(self.sprites)

        # enemies layer for convenience
        self.enemies = cocos.layer.ScrollableLayer()
        self.scroller.add(self.enemies)
        # add an enemy for each "enemy" trigger in the map
        for cell in self.triggers.find_cells(enemy='yes'):
            enemy = cocos.sprite.Sprite('enemy.png', cell.center)
            enemy.velocity = (100, 0)
            a = RotateBy(180, 1) | (ScaleTo(1.1, .5) + ScaleTo(.9, .5))
            enemy.do(EnemyUpdate() | Repeat(a))
            self.enemies.add(enemy)
        self.reversers = self.triggers.find_cells(reverse='yes')

        self.add(cocos.sprite.Sprite('background.png', anchor=(0, 0)), z=-1)
        self.add(self.scroller, z=0)

if __name__ == '__main__':
    # no scaling so our tile mapping isn't affected
    director.init(do_not_scale=True)
    keys = key.KeyStateHandler()
    director.window.push_handlers(keys)
    director.run(Platforming())
