import math
import random
import cocos
import pyglet
from cocos.director import director
from cocos.tiles import Tile, RectCell, RectMapLayer

pyglet.resource.path.append('data')
pyglet.resource.reindex()

# make up some solid color images
wall = pyglet.image.SolidColorImagePattern((100, 100, 100, 255)).create_image(16, 16)
blank = pyglet.image.SolidColorImagePattern((200, 200, 200, 255)).create_image(16, 16)
select = pyglet.image.SolidColorImagePattern((0, 255, 0, 128)).create_image(16, 16)
invalid = pyglet.image.SolidColorImagePattern((255, 0, 0, 128)).create_image(16, 16)

# now make up my tile types for mapping
wall = Tile('wall', {'blocks': True}, wall)
floor = Tile('floor', {}, blank)
entrance = Tile('entrance', {'entrance': True}, blank)
exit = Tile('exit', {'exit': True}, blank)
tower = Tile('tower', {'blocks': True, 'tower': True}, pyglet.resource.image('tower.png'))

# size of the game window (30x20 16-pixel cells)
WIDTH, HEIGHT = (30*16, 20*16)

def distance(ax, ay, bx, by):
    '''Determine the distance between two points.'''
    return math.sqrt((ax-bx)**2 + (ay-by)**2)

def collide(a, b):
    '''Determine whether two objects with a center point and width
    (diameter) are colliding.'''
    return distance(a.x, a.y, b.x, b.y) < (a.width/2 + b.width/2)

def heading(ax, ay, bx, by):
    '''Determin the heading, in degrees, from point a to b.'''
    return math.degrees(math.atan2(ay-by, bx-ax))


class MoveCreep(cocos.actions.Action):
    '''Creep movement action.

    The creep (Sprite) has a target cell (called .target) and we attempt
    to move it to that cell at 50 pixels per second.
    '''
    def step(self, dt):
        creep = self.target

        # the target cell may be None (the creep has just reached the exit)
        # or it may have been turned into a blocker (a tower was built)
        if not creep.target or creep.target.get('blocks'):
            # ask for a new target cell from the map
            creep.target = creep.map.next_move(creep.cell)
            if not creep.target:
                # the creep is at the exit
                creep.kill()
                return

        # figure distance to the target
        # the creep's anchor is centered so we line that up with the center
        # of the cell
        tx, ty = creep.target.center
        px, py = creep.position
        d = distance(px, py, tx, ty)

        # figure the distance moved this step (50 pixels per second)
        move = 50*dt

        if d <= move:
            # the creep's move takes it to the destination so clean
            # things up and ask for a new target from the map
            creep.position = creep.target.center
            creep.cell = creep.target
            creep.target = creep.map.next_move(creep.cell)
        else:
            # move the 50 pixels per second along the line from the current
            # position to the target
            n = move / d
            px += n * (tx - px)
            py += n * (ty - py)
            creep.position = (px, py)


class Shoot(cocos.actions.Action):
    '''Have a turret aim at a creep and shoot.
    '''
    def init(self, creep):
        # this is the creep to aim at
        self.creep = creep
    def step(self, dt):
        # figure the angle to the creep and adjust the turret rotation to
        # that angle
        # TODO: adjust slowly
        angle = heading(*(self.target.position + self.creep.position))
        self.target.rotation = angle

        if distance(*(self.creep.position + self.target.position)) > 50:
            # the creep is too far away; cancel this action to allow the
            # turret to re-aim
            self._done = True

        if angle == self.target.rotation and self.creep.target:
            # we're pointing at the creep so shoot at it
            director.scene.shoot(self.target.position,
                self.creep.target.center)
            self.target.gun_cooldown = 1.5
            self._done = True

    def __deepcopy__(self, foo):
        # the presence of the creep attribute (which has pyglet magic
        # attached) means we can't deepcopy this object - we don't need to
        # anyway
        return self


class Field(RectMapLayer):
    '''This is a playing field.

    It is a map of cells and also contains layers for the towers, creeps
    and bullets.
    '''
    is_event_handler = True

    def __init__(self):
        cells = []
        self.entrances = []
        # create a basic field with an entrance on one side and exit on the
        # other
        for i in range(30):
            column = []
            for j in range(20):
                if i == 0 and 7 < j < 12:
                    tile = entrance
                elif i == 29 and 7 < j < 12:
                    tile = exit
                elif i in (0, 29) or j in (0, 19):
                    tile = wall
                else:
                    tile = floor
                cell = RectCell(i, j, 16, 16, {}, tile)
                column.append(cell)
                if tile is entrance:
                    self.entrances.append(cell)
            cells.append(column)
        super(Field, self).__init__('map', 16, 16, cells)

        # center the field on the display
        self.origin_x = WIDTH//2 - self.px_width//2
        self.origin_y = HEIGHT//2 - self.px_height//2
        self.set_view(0, 0, WIDTH, HEIGHT)

        # set up creep generation in 1 second
        self.next_creep = 1

        # register the gameplay update function to be called every frame
        self.schedule(self.update)

        # a layer to manage the towers
        self.towers = cocos.layer.Layer()
        self.add(self.towers)

        # a layer to manage the bullets
        self.bullets = cocos.layer.Layer()
        self.add(self.bullets)

        # a layer to manage the creeps
        self.creeps = cocos.layer.Layer()
        self.add(self.creeps)

        # a layer to give user feedback on tower placement
        self.select = cocos.sprite.Sprite(select)
        self.add(self.select)
        self.select.visible = False

    def on_mouse_motion(self, x, y, dx, dy):
        # figure the cell the player has the mouse over and give visual
        # feedback on its suitability for building a tower
        cell = self.get_at_pixel(x, y)
        if cell:
            if cell.get('blocks'):
                self.select.image = invalid
            else:
                self.select.image = select
            self.select.position = cell.center
            self.select.visible = True
        else:
            # ... or just hide the highlight box if the mouse is outside
            # the field
            self.select.visible = False

    def on_mouse_release(self, x, y, button, modifiers):
        # the player has clicked the mouse - build a tower
        cell = self.get_at_pixel(x, y)
        tower = cocos.sprite.Sprite('tower.png', cell.center)
        tower.cell = cell
        tower.gun_cooldown = 0
        self.towers.add(tower)
        # make sure the player can't build here again (and that creeps
        # can't traverse this cell)
        cell['blocks'] = True

    def update(self, dt):
        '''Update the field.

        - create creeps if necessary.
        - target creeps if guns are idle
        - detect bullet hits
        '''
        self.next_creep -= dt
        if self.next_creep < 0:
            # send in a creep!
            self.next_creep = 5
            c = cocos.sprite.Sprite('creep.png')
            c.cell = random.choice(self.entrances)
            c.position = c.cell.center
            c.map = self
            c.health = 2
            c.target = None
            self.creeps.add(c)
            c.do(MoveCreep(self))

        # see if any of the towers should shoot
        for z, tower in self.towers.children:
            if tower.gun_cooldown:
                tower.gun_cooldown = max(0, tower.gun_cooldown - dt)
            elif not tower.actions:
                for z, creep in self.creeps.children:
                    if distance(*(creep.position + tower.position)) < 50:
                        tower.do(Shoot(creep))

        # see if any of the bullets have hit a creep
        for z, bullet in self.bullets.children:
            for z, creep in self.creeps.children:
                if collide(bullet, creep):
                    creep.health -= 1
                    if creep.health <= 0:
                        creep.kill()
                    bullet.kill()

    def next_move(self, start):
        '''Determine the next move for a creep from the start position to
        get to the exit.

        Raises ValueError if the map is not solvable.

        This implements a standard non-recursive flood fill until we hit
        our target condition (determining the move cost for the start
        cell).
        '''
        cost = {}
        for column in self.cells:
            for cell in column:
                if cell.get('exit'):
                    cost[cell.i, cell.j] = 0
        while True:
            changed = False
            for here in list(cost):
                i, j = here
                for attempt in (i, j+1), (i, j-1), (i-1, j), (i+1, j):
                    if attempt in cost: continue
                    cell = self.get_cell(*attempt)
                    if cell is not None and not cell.get('blocks'):
                        cost[attempt] = cost[here] + 1
                        changed = True
                    if cell is start:
                        return self.get_cell(*here)
            if not changed:
                raise ValueError("Can't solve map")

class CreepsGame(cocos.scene.Scene):
    '''This scene manages a single game.

    It mostly exists as a method for other parts of the game to access the
    field through director.scene.field.
    '''
    def __init__(self):
        super(CreepsGame, self).__init__()
        self.field = Field()
        self.add(self.field)

    def shoot(self, start, target):
        # shoot at a creep; we implement this method here so it is easy to
        # access (on the scene) and so it has easy access to the scene
        # parts
        x, y = start
        tx, ty = target
        bullet = cocos.sprite.Sprite('bullet.png', start)
        dx, dy = tx-x, ty-y
        d = math.sqrt(dx**2 +  dy**2)
        x += dx * 50/d
        y += dy * 50/d
        bullet.do(cocos.actions.MoveTo((x+dx, y+dy), .5) +
            cocos.actions.CallFunc(bullet.kill))
        self.field.bullets.add(bullet)


# no scaling so our tile mapping isn't affected
director.init(width=WIDTH, height=HEIGHT, do_not_scale=True)
director.run(CreepsGame())
