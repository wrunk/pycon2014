import pygame
import tmx

class Enemy(pygame.sprite.Sprite):
    image = pygame.image.load('enemy.png')
    def __init__(self, location, *groups):
        super(Enemy, self).__init__(*groups)
        self.rect = pygame.rect.Rect(location, self.image.get_size())
        self.direction = 1

    def update(self, dt, game):
        self.rect.x += self.direction * 100 * dt
        for cell in game.tilemap.layers['triggers'].collide(self.rect, 'reverse'):
            if self.direction > 0:
                self.rect.right = cell.left
            else:
                self.rect.left = cell.right
            self.direction *= -1
            break
        if self.rect.colliderect(game.player.rect):
            game.player.is_dead = True

class Player(pygame.sprite.Sprite):
    def __init__(self, location, *groups):
        super(Player, self).__init__(*groups)
        self.image = pygame.image.load('player.png')
        self.rect = pygame.rect.Rect(location, self.image.get_size())
        self.resting = False
        self.dy = 0
        self.is_dead = False

    def update(self, dt, game):
        last = self.rect.copy()

        key = pygame.key.get_pressed()
        if key[pygame.K_LEFT]:
            self.rect.x -= 300 * dt
        if key[pygame.K_RIGHT]:
            self.rect.x += 300 * dt

        if self.resting and key[pygame.K_SPACE]:
            self.dy = -500
        self.dy = min(400, self.dy + 40)

        self.rect.y += self.dy * dt

        new = self.rect
        self.resting = False
        for cell in game.tilemap.layers['triggers'].collide(new, 'blockers'):
            blockers = cell['blockers']
            if 'l' in blockers and last.right <= cell.left and new.right > cell.left:
                new.right = cell.left
            if 'r' in blockers and last.left >= cell.right and new.left < cell.right:
                new.left = cell.right
            if 't' in blockers and last.bottom <= cell.top and new.bottom > cell.top:
                self.resting = True
                new.bottom = cell.top
                self.dy = 0
            if 'b' in blockers and last.top >= cell.bottom and new.top < cell.bottom:
                new.top = cell.bottom
                self.dy = 0

        game.tilemap.set_focus(new.x, new.y)

class Game(object):
    def main(self, screen):
        clock = pygame.time.Clock()

        background = pygame.image.load('background.png')

        self.tilemap = tmx.load('map-enemies.tmx', screen.get_size())

        self.sprites = tmx.SpriteLayer()
        start_cell = self.tilemap.layers['triggers'].find('player')[0]
        self.player = Player((start_cell.px, start_cell.py), self.sprites)
        self.tilemap.layers.append(self.sprites)

        self.enemies = tmx.SpriteLayer()
        for enemy in self.tilemap.layers['triggers'].find('enemy'):
            Enemy((enemy.px, enemy.py), self.enemies)
        self.tilemap.layers.append(self.enemies)

        while 1:
            dt = clock.tick(30)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return

            self.tilemap.update(dt / 1000., self)
            screen.blit(background, (0, 0))
            self.tilemap.draw(screen)
            pygame.display.flip()

            if self.player.is_dead:
                print 'YOU DIED'
                return

if __name__ == '__main__':
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    Game().main(screen)

