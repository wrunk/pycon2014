'''

TODO

- add sound effects


'''
import os
import sys
import random
import marshal
import webbrowser
import platform

import pygame

# Import the android module. If we can't import it, set it to None - this
# lets us test it, and check to see if we want android-specific behavior.
try:
    import android
    # from android import mixer
except ImportError:
    android = None
    # from pygame import mixer

SHAPES = set('point star box circle spiral diamond triangle'.split())
ACTIONS = '''1_navigation_accept 1_navigation_cancel 1_navigation_refresh
    2_action_about 2_action_help'''.split()
IMAGES = {}

# define where we can find the data files - this might change depending on the
# application bundling used
DATADIR = 'data/'
if getattr(sys, '_MEIPASS', None):
    print 'Running frozen, using _MEIPASS', sys._MEIPASS
    # frozen (pyInstaller style) data files are in a special directory
    DATADIR = os.path.join(sys._MEIPASS, 'data', '')

class ColumnGroup(pygame.sprite.LayeredDirty):
    # special group that retains a list of the order that sprites are added
    def __init__(self, *args, **kw):
        super(ColumnGroup, self).__init__(*args, **kw)
        self._column_order = []
    def add_internal(self, sprite, layer=None):
        super(ColumnGroup, self).add_internal(sprite, layer=layer)
        self._column_order.append(sprite)
        for n, sprite in enumerate(self._column_order):
            sprite.column_order = n
            sprite.target_y = sprite.y_offset + (7-n) * sprite.size
    def remove_internal(self, sprite):
        super(ColumnGroup, self).remove_internal(sprite)
        self._column_order.remove(sprite)
        for n, sprite in enumerate(self._column_order):
            sprite.column_order = n
            sprite.target_y = sprite.y_offset + (7-n) * sprite.size

class Block(pygame.sprite.DirtySprite):
    def __init__(self, y_offset, column, prevent_shapes=set(), shape=None,
            y_pos=None):
        self.y_offset = y_offset
        if shape is None:
            self.shape = random.choice(list(SHAPES - prevent_shapes))
        else:
            self.shape = shape
        self.image = IMAGES[self.shape]
        self.size = self.image.get_size()[0]
        if y_pos is None:
            self.target_y = 0
            y_pos = -10
        else:
            self.target_y = y_pos
        self.rect = pygame.rect.Rect((column.x, y_pos), (self.size, self.size))
        self.speed = 0
        super(Block, self).__init__(column)

    def at_rest(self):
        return self.rect.y == self.target_y

    def update(self, dt):
        column = self.groups()[0]

        old_y = self.rect.y

        if self.column_order == 0:
            # the bottom row (first in the list) rests on the bottom of the
            # play area
            target_bottom = self.target_y
        else:
            # otherwise the rows will rest on the row below them (the row
            # precering them in the sprite list)
            target_bottom = column._spritelist[self.column_order-1].rect.y - self.size

        # accelerate at 10 pixels per second ^ 2
        self.speed += 20 * dt

        # move down if we can until we hit target_bottom
        self.rect.y += self.speed
        if self.rect.y >= target_bottom:
            self.rect.y = target_bottom
            self.speed = 0

        # if the sprite moved then it's dirty
        if old_y != self.rect.y:
            self.dirty = 1

def find_match(sprite, grid, visited=None):
    x, y = sprite.rect.topleft
    if visited is None:
        visited = set()
    elif (x,y) in visited:
        return []
    visited.add((x, y))
    r = [sprite]
    mod = sprite.size
    for xm, ym in (mod, 0), (-mod, 0), (0, mod), (0, -mod):
        test = grid.get((x+xm, y+ym))
        if test is not None and test.shape == sprite.shape:
            r.extend(find_match(test, grid, visited))
    return r

def thousands(number):
    s = '%d' % number
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + ','.join(reversed(groups))

class ActionSprite(pygame.sprite.Sprite):
    def __init__(self, pos, image, action, group):
        super(ActionSprite, self).__init__(group)
        self.image = image
        self.rect = pygame.rect.Rect(pos, image.get_size())
        self.action = action

class BlockEffect(pygame.sprite.Sprite):
    def __init__(self, image, rect, column, group):
        super(BlockEffect, self).__init__(group)
        self.image = image.copy()
        self.rect = rect
        self.column = column
        self.life = .5

    def update(self, dt):
        self.life -= dt
        r = self.rect
        if self.life <= 0:
            self.kill()
        self.column.repaint_rect(r)

class Game(object):
    MODE_EASY = 'easy'
    MODE_HARD = 'hard'
    mode = MODE_HARD

    def __init__(self, screen, density, dp, icon_size):
        self.screen = screen
        self.screen_width, self.screen_height = screen.get_size()
        self.density = density
        self.dp = dp
        self.action_icon_size = dict(ldpi=18, mdpi=32, hdpi=36,
            xhdpi=48)[density]
        print 'action_icon_size=%r' % self.action_icon_size
        self.icon_size = icon_size
        self.columns = []
        self.score = 0
        self.score_changed = True
        self.score_multiplier = 1
        self.all_dirty = True
        self.should_quit = False
        self.high_score = None
        self.game_over = False
        self.grid_complete_and_settled = False
        self.splash_shown = False
        self.need_match_search = False
        self.bad_swap_text_life = 0
        self.not_adjacent_text_life = 0

        if android:
            self.save_fn = 'save.state'
        else:
            self.save_fn = os.path.expanduser('~/.match3.save')

        # find a good size for the font to render in icon_size-ish pixels
        # height
        size = 8
        target_font_size = self.action_icon_size
        while True:
            self.font = pygame.font.Font(DATADIR + 'Roboto-Regular.ttf', size)
            if self.font.get_linesize() >= target_font_size:
                print 'font size=%r' % size
                break
            size += 1
        self.small_font = pygame.font.Font(DATADIR + 'Roboto-Regular.ttf',
            int(size * .75))
        self.bold_font = pygame.font.Font(DATADIR + 'Roboto-Bold.ttf', size)

    def reset(self):
        for column in self.columns:
            column.empty()
        self.grid_complete_and_settled = False
        self.score = 0
        self.score_multiplier = 1
        self.score_changed = True
        self.game_over = False
        self.all_dirty = True

    def load_state(self):
        import os
        print 'attempt to load state from %s' % os.path.abspath(self.save_fn)
        if not os.path.exists(self.save_fn):
            return
        self.grid_complete_and_settled = True
        with open(self.save_fn, 'rb') as f:
            state = marshal.load(f)
        self.high_score = state.get('high_score', 0)
        self.score = state.get('score', 0)
        self.splash_shown = state.get('splash_shown', False)
        self.all_dirty = True
        if 'columns' not in state:
            return

        for n, column in enumerate(self.columns):
            for block in state['columns'][n]:
                shape = block['shape']
                # backwards compatibility (1.1.1 -> 1.2.0)
                if shape == 'cross':
                    shape = 'spiral'
                Block(self.play_y_offset, column, shape=shape,
                    y_pos=block['y_pos'])

    def save_state(self):
        state = dict(high_score=self.high_score, score=self.score,
            splash_shown=self.splash_shown, columns=[[] for n in '.'*8])
        for n, column in enumerate(self.columns):
            for sprite in column._column_order:
                state['columns'][n].append(dict(shape=sprite.shape,
                    y_pos=sprite.target_y))

        with open(self.save_fn + '.new', 'wb') as f:
            marshal.dump(state, f)
        # oh, Windows :-(
        if platform.system() == 'Windows' and os.path.exists(self.save_fn):
            os.remove(self.save_fn)
        os.rename(self.save_fn + '.new', self.save_fn)
        print 'STATE SAVED', os.path.abspath(self.save_fn)

    def update(self, dt):
        self.effects_group.update(dt)

        if self.mode is self.MODE_HARD:
            grid = {}
            for column in self.columns:
                for sprite in column._spritelist:
                    x, y = sprite.rect.topleft
                    grid[x, y] = sprite

            for n, column in enumerate(self.columns):
                h = len(column)
                if h == 8:
                    continue

                # figure the shapes around the missing cell
                shapes = set()
                if random.random() < .8:
                    if h:
                        shapes.add(column._column_order[h-1].shape)
                    if n:
                        left = self.columns[n-1]._column_order
                        if len(left) > h:
                            shapes.add(left[h].shape)
                    if n < 7:
                        right = self.columns[n+1]._column_order
                        if len(right) > h:
                            shapes.add(right[h].shape)
                Block(self.play_y_offset, column, prevent_shapes=shapes)

        else:
            for column in self.columns:
                if len(column) < 8:
                    Block(self.play_y_offset, column)

        # now update
        for column in self.columns:
            column.update(dt)

        # see if the grid is complete and settled
        if not self.grid_complete_and_settled:
            n = sum(s.at_rest() for c in self.columns for s in c._spritelist)
            self.grid_complete_and_settled = n == 8*8
            self.need_match_search = True

        if self.game_over:
            return

        if self.grid_complete_and_settled:
            if self.need_match_search:
                self.find_matches(remove=True)
                self.need_match_search = False

        # the find_matches invocation above might reset grid_complete_and_settled
        if self.grid_complete_and_settled and self.is_game_over():
            self.game_over = True

    def find_matches(self, remove=False, sprites=[]):
        # create grid
        grid = {}
        for column in self.columns:
            for sprite in column._spritelist:
                if sprite.at_rest():
                    x, y = sprite.rect.topleft
                    grid[x, y] = sprite
                else:
                    self.grid_complete_and_settled = False

        if sprites:
            # only test specific sprites
            for sprite in sprites:
                n = find_match(sprite, grid)
                if len(n) > 2:
                    return True
            return False

        # test grid
        matches = False
        score = 0
        for x in range(9):
            for y in range(9):
                sprite = grid.get((x*self.icon_size + self.play_x_offset,
                    y*self.icon_size + self.play_y_offset))
                if sprite is None:
                    continue
                n = find_match(sprite, grid)
                N = len(n)
                if N < 3:
                    continue
                if not remove:
                    return True

                # any alteration to the grid clears the current selection
                self._swap_start_sprite = None

                # add some score
                score += self.score_multiplier * (2 ** (N-3))

                # and remove the matched sprites
                for s in n:
                    x, y = s.rect.topleft
                    del grid[x, y]
                    s.kill()
                self.grid_complete_and_settled = False
                matches = True
                self.score_multiplier += 1

#        if matches:
#            self.get_sound.play()

        self.score += score
        if self.score > self.high_score:
            self.high_score = self.score
        self.score_changed = True
        return matches

    def is_game_over(self):
        # create grid - this is only ever called when the entire grid is
        # created and settled
        grid = {}
        g = []
        for column in self.columns:
            l = []
            g.append(l)
            for sprite in column._spritelist:
                grid[sprite.rect.topleft] = sprite
                l.append(sprite.shape[0])

        mod = self.icon_size
        for (x, y), sprite in grid.items():
            for xm, ym in (mod, 0), (-mod, 0), (0, mod), (0, -mod):
                other = grid.get((x+xm, y+ym))
                if other is None:
                    continue

                # swap for temp, find matches
                sprite.shape, other.shape = other.shape, sprite.shape
                m1 = find_match(sprite, grid)
                m2 = find_match(other, grid)
                sprite.shape, other.shape = other.shape, sprite.shape

                if len(m1) > 2 or len(m2) > 2:
                    return False

        return True

    def do_about(self):
        lines = [line.strip() for line in '''*match 3

        Score with groups of three
        (or more) matching pieces.

        Drag adjacent pieces to swap.

        Can only swap to make groups.


        A Game by Richard Jones
        _http://mechanicalcat.net/richard
        <version 1.2.4


        (tap to continue)'''.splitlines()]

        clock = pygame.time.Clock()

        while 1:
            fh = self.font.get_linesize() #+ int(32 * self.dp)
            x = self.screen_width // 2
            y = self.screen_height // 2 - (len(lines) * fh) // 2

            self.screen.fill((230, 230, 230))
            for line in lines:
                if line.startswith('*'):
                    text = self.bold_font.render(line[1:], True, (50, 50, 50))
                elif line.startswith('<'):
                    text = self.small_font.render(line[1:], True, (150, 150, 150))
                else:
                    if line.startswith('_'):
                        line = line[1:]
                        link_rect = pygame.rect.Rect((x - tw//2, y), (tw, th))
                    text = self.font.render(line, True, (50, 50, 50))
                tw, th = text.get_size()
                self.screen.blit(text, (x - tw//2, y))
                y += fh
            pygame.display.flip()

            clock.tick(10)

            if android and android.check_pause():
                self.save_state()
                android.wait_for_resume()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.should_quit = True
                    self.all_dirty = True
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.all_dirty = True
                    return
                if event.type == pygame.MOUSEBUTTONUP:
                    if link_rect.collidepoint(event.pos):
                        webbrowser.open('http://mechanicalcat.net/richard')
                    self.all_dirty = True
                    return

    _swap_start_sprite = None
    def mouse_down(self, pos):
        # set the swap sprite
        self._swap_start_sprite = None
        for column in self.columns:
            for sprite in column._spritelist:
                if not sprite.at_rest():
                    continue

                if sprite.rect.collidepoint(pos):
                    self._swap_start_sprite = sprite
                    return

    def mouse_up(self, pos):
        self.score_multiplier = 1

        start = self._swap_start_sprite
        end = self._swap_end_sprite
        self._swap_start_sprite = self._swap_end_sprite = None

        if start is not None and end is not None:
            self.need_match_search = True

    _swap_end_sprite = None
    def mouse_motion(self, pos):
        if self._swap_start_sprite is None:
            return

        start = self._swap_start_sprite

        for column in self.columns:
            for end in column._spritelist:
                if not end.at_rest():
                    continue

                if not end.rect.collidepoint(pos):
                    continue

                if self._swap_end_sprite is not None:
                    if end is self._swap_end_sprite:
                        # same end sprite - nothing to do
                        return

                    old = self._swap_end_sprite
                    # new end sprite - undo a previous swap
                    old.shape, start.shape = start.shape, old.shape
                    old.image, start.image = start.image, old.image
                    start.dirty = old.dirty = 1
                    self._swap_end_sprite = None

                if end is start:
                    return

                # figure the distance to make sure our two selections are
                # adjacent
                d = abs(end.rect.x - start.rect.x)
                d += abs(end.rect.y - start.rect.y)
                if d > self.icon_size:
                    # selection is too far away; it's the new swap
                    self.flag_invalid_swap(end, adjacent=True)
                    return

                # do a temporary swap and test these specific sprites for
                # matches
                end.shape, start.shape = start.shape, end.shape
                if not self.find_matches(sprites=[start, end]):
                    self.flag_invalid_swap(end)
                    # swap back the temp swap
                    end.shape, start.shape = start.shape, end.shape
                else:
                    # swap the images as well
                    end.image, start.image = start.image, end.image
                    start.dirty = end.dirty = 1
                    self._swap_end_sprite = end

                # we've handled the hit so we're done
                return

    def flag_invalid_swap(self, sprite, adjacent=False):
        # flag that a swap with the indicated sprite is invalid
        rect = sprite.rect

        if adjacent:
            self.not_adjacent_text_life = 3.0
        else:
            self.bad_swap_text_life = 3.0

        existing = False
        for current in self.effects_group.sprites():
            if current.rect == rect:
                current.life = 0.5
                existing = True

        if existing:
            return

        column = sprite.groups()[0]
        BlockEffect(self.cross, rect, column, self.effects_group)

    def main(self):
        # start us off with a blank slate
        self.screen.fill((230, 230, 230))

        for name in SHAPES:
            IMAGES[name] = pygame.image.load(DATADIR + '%s-%s.png' % (name,
                self.icon_size))

        self.cross = pygame.image.load(DATADIR + 'cross-%s.png' % self.icon_size)

        for name in ACTIONS:
            IMAGES[name] = pygame.image.load(DATADIR + '%s/%s.png' % (self.density,
                name))

        clock = pygame.time.Clock()

        # add 8dp on either side of the action icon/text
        action_icon_pad = int(8 * self.dp)
        action_line_height = self.action_icon_size + action_icon_pad * 2

        # figure the height of the remaining area to work with - balance the
        # bottom action line with another spacing of the same height at the top
        remain = self.screen_height - action_line_height * 2

        play_height = self.icon_size * 8
        score_height = action_line_height

        # this remaining area holds the play area and score (an
        # action_line_height); determine padding to space the two evenly
        pad = remain - play_height - score_height
        pad //= 3

        # determine the play area size and thus the positioning of it
        self.play_y_offset = action_line_height + pad
        score_y = self.play_y_offset + self.icon_size * 8 + pad
        self.play_x_offset = self.screen_width // 2 - (self.icon_size * 8) // 2

        for n in range(8):
            # force using dirty for update 'cos the other method is busted
            g = ColumnGroup(_use_update=True)
            g.set_timing_treshold(1000.)
            g.x = self.play_x_offset + n * self.icon_size
            g.set_clip(self.screen.get_clip())
            self.columns.append(g)

        self.load_state()

        # generate the background image
        background = pygame.surface.Surface((self.screen_width, self.screen_height -
            2 * action_line_height))
        background.fill((230, 230, 230))

        # check we've not loaded a game over game
        if self.grid_complete_and_settled and self.is_game_over():
            self.game_over = True

        if not self.splash_shown:
            self.splash_shown = True
            self.do_about()

        # group for collecting effects being drawn
        self.effects_group = pygame.sprite.Group()

        bad_swap_text = self.small_font.render('Must swap to make a group',
            True, (255, 68, 68))
        not_adjacent_text = self.small_font.render('Must swap adjacent shapes',
            True, (255, 68, 68))

        reset_clickable = None

        while not self.should_quit:
            if android and android.check_pause():
                self.save_state()
                android.wait_for_resume()

            # update, but limit the step just in case we were paused or
            # something
            dt = min(.1, clock.tick(30) / 1000.)
            self.update(dt)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.should_quit = True
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.should_quit = True
                    if __debug__:
                        if event.mod & pygame.KMOD_CTRL and event.key == pygame.K_s:
                            pygame.image.save(self.screen, 'screenshot.png')
                        if event.mod & pygame.KMOD_CTRL and event.key == pygame.K_g:
                            self.game_over = True

                if event.type == pygame.MOUSEBUTTONUP:
                    for sprite in self.action_bar.sprites():
                        if sprite.rect.collidepoint(event.pos):
                            sprite.action()
                    if self.game_over:
                        if reset_clickable is not None and \
                                reset_clickable.collidepoint(event.pos):
                            self.reset()
                    else:
                        self.mouse_up(event.pos)
                if self.game_over:
                    continue

                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse_down(event.pos)
                if event.type == pygame.MOUSEMOTION:
                    self.mouse_motion(event.pos)

            if self.all_dirty:
                self.screen.fill((230, 230, 230))
                for column in self.columns:
                    for sprite in column._spritelist:
                        sprite.dirty = 1

                # action bar background
                action_bar_top = self.screen_height - action_line_height
                self.screen.fill((200, 200, 200), ((0, action_bar_top),
                    (self.screen_width, action_line_height)))

                # add the action icons
                self.action_bar = pygame.sprite.Group()

                # right-align
                w = IMAGES['2_action_about'].get_size()[0]
                x = self.screen_width - action_icon_pad - w
                y = action_bar_top + action_icon_pad
                ActionSprite((x, y), IMAGES['2_action_about'], self.do_about,
                    self.action_bar)
                self.action_bar.draw(self.screen)

            for column in self.columns:
                column.draw(self.screen, background)

            self.effects_group.draw(self.screen)

            # update score
            if self.all_dirty or self.score_changed:
                # render the text and determine its dimensions
                text = thousands(self.score)
                text = self.font.render('Score: ' + text, True, (50, 50, 50))
                tw, th = text.get_size()

                # draw the background to clear previous text
                r = pygame.rect.Rect((0, score_y), (self.screen_width, pad))
                self.screen.fill((230, 230, 230), r)

                # center the text in the middle of that rect
                self.screen.blit(text, (self.screen_width // 2 - tw//2,
                    score_y + score_height//2 - th //2))

                if self.score == self.high_score:
                    text = self.small_font.render('HIGH SCORE', True,
                        (150, 150, 150))
                    tw, th = text.get_size()
                    y = score_y + score_height//2 + th //2
                    self.screen.blit(text, (self.screen_width // 2 - tw//2,
                        y + th))

                self.score_changed = False

            if self.bad_swap_text_life > 0:
                btw, bth = bad_swap_text.get_size()
                r = pygame.rect.Rect((self.screen_width // 2 - btw // 2,
                    pad // 2 - bth // 2), (btw, bth))
                self.screen.fill((230, 230, 230), r)
                # clear block text from display if game over
                if self.game_over:
                    self.bad_swap_text_life = 0
                else:
                    # retain text for 4 seconds
                    self.bad_swap_text_life -= dt
                if self.bad_swap_text_life > 0:
                    self.screen.blit(bad_swap_text, r.topleft)

            if self.not_adjacent_text_life > 0:
                btw, bth = not_adjacent_text.get_size()
                r = pygame.rect.Rect((self.screen_width // 2 - btw // 2,
                    pad // 2 - bth // 2 + bth), (btw, bth))
                self.screen.fill((230, 230, 230), r)
                # clear block text from display if game over
                if self.game_over:
                    self.not_adjacent_text_life = 0
                else:
                    # retain text for 4 seconds
                    self.not_adjacent_text_life -= dt
                if self.not_adjacent_text_life > 0:
                    self.screen.blit(not_adjacent_text, r.topleft)

            if self.game_over:
                self.screen.fill((230, 230, 230), pygame.rect.Rect((0, 0),
                    (self.screen_width, pad)))

                # render text, get dimensions
                game_over_text = self.bold_font.render('Game Over', True,
                    (50, 50, 50))
                tw, th = text.get_size()

                # icon dimensions
                rw, rh = IMAGES['1_navigation_refresh'].get_size()

                # add in a spacer to get width
                space = int(16 * self.dp)
                w = tw + rw + space

                # determine starting X coord which gives clickable rect box
                x = self.screen_width // 2 - w // 2
                reset_clickable = pygame.rect.Rect((x, 0), (w, pad))

                # blit text
                self.screen.blit(game_over_text, (x, pad // 2 - th // 2))

                # blit icon
                x += tw + space + rw // 2
                self.screen.blit(IMAGES['1_navigation_refresh'],
                    (x, pad // 2 - rh // 2))

            pygame.display.flip()

            self.all_dirty = False

        self.save_state()

def main():
    pygame.init()

    if android:
        screen = pygame.display.set_mode()
        width, height = screen.get_size()
        dpi = android.get_dpi()
        if dpi >= 320:
            density = 'xhdpi'
        elif dpi >= 240:
            density = 'hdpi'
        elif dpi >= 160:
            density = 'mdpi'
        else:
            density = 'ldpi'
        dp = dpi / 160.

        android.init()
        # map the back button to the escape key
        android.map_key(android.KEYCODE_BACK, pygame.K_ESCAPE)
    else:
        dpi = 160
        dp = 1
        width = 480
        height = 800
        screen = pygame.display.set_mode((width, height))
        density = 'mdpi'

    # figure the game icon size based on the available real-estate - allow 10
    # rows so there's some whitespace border
    target = width // 10
    for size in [24, 32, 48, 64, 72, 96, 128]:
        if size > target:
            break
        icon_size = size

    print 'dimensions=%r; dpi=%r; density=%r; dp=%r; icon_size=%r' % (
        screen.get_size(), dpi, density, dp, icon_size)

    Game(screen, density, dp, icon_size).main()

if __name__ == '__main__':
    main()
