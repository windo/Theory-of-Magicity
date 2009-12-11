#!/usr/bin/python

import time, os, sys, math
from random import random
from operator import attrgetter

import pygame
from pygame.locals import *

import actors, fields

class SpriteLoader:
      """
      Load images and divide them to separate surfaces
      """
      class NoImage(Exception):
            def __init__(self, name):
                self.name = name
            def __str__(self):
                return "No Image %s" % (self.name) 

      def __init__(self):
          self.lists  = {}
          self.images = {}

      def load(self, filename, listname = False, width = False, start = 0, to = False, flip = False, resize = False):
          # load the file, if not already loaded
          if not self.images.has_key(filename):
            self.images[filename] = pygame.image.load("img/" + filename)
          img = self.images[filename]

          # make an image list as well?
          if listname:
            if not width:
              if flip:
                img = pygame.transform.flip(img, True, False)
              if resize:
                img = pygame.transform.scale(img, resize)
              self.lists[listname] = [img]
            else:
              # use all subsurfaces?
              if not to:
                to = int(img.get_width() / width)
              self.lists[listname] = []
              for i in xrange(start, to):
                rect = [ i * width, 0, width, img.get_height() ]
                subimg = img.subsurface(rect)
                if flip:
                  subimg = pygame.transform.flip(subimg, True, False)
                if resize:
                  subimg = pygame.transform.scale(subimg, resize)
                self.lists[listname].append(subimg)

      def get(self, name):
          if name in self.images.keys():
            return self.images[name]
          elif name in self.lists.keys():
            return self.lists[name]
          else:
            raise self.NoImage(name)

class View:
      """
      Viewport/scale to use for translating in-game coordinates to screen coordinates
      """
      def __init__(self, view, plane):
          """
          view is (width, height) - input/output scale
          plane is (x1, y1, x2, y2) - the MagicField area to fit in the view
          """
          self.view  = list(view)
          self.plane = list(plane)
          self.recalculate()
      def recalculate(self):
          view_w, view_h = self.view
          plane_x1, plane_y1, plane_x2, plane_y2 = self.plane
          plane_w = plane_x2 - plane_x1
          plane_h = plane_y2 - plane_y1
          # multiplier to get plane coordinates from view coordinates
          self.mult_x = float(plane_w) / float(view_w)
          self.mult_y = float(plane_h) / float(view_h)
          # offset to apply to plane coordinates
          self.offset_x = plane_x1
          self.offset_y = plane_y2

      def pl_x1(self): return self.plane[0]
      def pl_x2(self): return self.plane[2]
      def pl_y1(self): return self.plane[1]
      def pl_y2(self): return self.plane[3]
      def sc_w(self): return self.view[0]
      def sc_h(self): return self.view[1]

      def get_center_x(self):
          return self.plane[0] + float(self.plane[2] - self.plane[0]) / 2.0
      def move_x(self, x):
          self.offset_x += x
          self.plane[0] += x
          self.plane[2] += x

      def sc2pl_x(self, x):
          return x * self.mult_x + self.offset_x
      def sc2pl_y(self, y):
          return self.offset_y - y * self.mult_y
      def pl2sc_x(self, x):
          return (x - self.offset_x) / self.mult_x
      def pl2sc_y(self, y):
          return (self.offset_y - y) / self.mult_y

class World:
      def __init__(self, sprites, fieldtypes, view):
          self.sprites     = sprites
          self.view        = view
          self.time_offset = 0.0
          self.pause_start = False

          # world objects
          self.fields  = {}
          for fieldtype in fieldtypes:
            field = fieldtype()
            self.fields[fieldtype] = field
          self.actors  = []

          # for convenience
          self.font    = pygame.font.SysFont("any", 14)
          self.bigfont = pygame.font.SysFont("any", 32)

      def get_time(self):
          if self.pause_start:
            return self.pause_start
          return time.time() - self.time_offset

      def pause(self):
          if self.pause_start:
            self.time_offset += time.time() - self.pause_start
            self.pause_start = False
          else:
            self.pause_start = time.time()
      def paused(self):
          if self.pause_start:
            return True
          else:
            return False

      # actor management
      def new_actor(self, actor_class, pos):
          actor = actor_class(self, pos)
          self.actors.append(actor)
          return actor
      def del_actor(self, actor):
          self.actors.pop(self.actors.index(actor))
      def all_actors(self):
          return self.actors
      def get_actors(self, x1 = False, x2 = False, filter = False, include = False, exclude = False):
          """
          Get actors with position in range [x1 : x2] and matching filter
          """
          ret = []
          for actor in self.actors:
            if x1 and actor.pos < x1:
              continue
            if x2 and actor.pos > x2:
              continue
            if filter and not filter(actor):
              continue
            if include:
              decision = False
              for klass in include:
                if isinstance(actor, klass):
                  decision = True
                  break
              if not decision:
                continue
            if exclude:
              decision = True
              for klass in exclude:
                if isinstance(actor, klass):
                  decision = False
                  break
              if not decision:
                continue

            ret.append(actor)
          return ret
      def sort_actors(self):
          self.actors.sort(key = attrgetter("pos"))

      # field management
      def get_field(self, fieldtype):
          return self.fields[fieldtype]
      def all_fields(self):
          return self.fields.values()

class Story:
      def __init__(self, world):
          self.world = world
          # story state
          self.state        = "begin"
          self.gameover     = False
          self.gameover_img = self.world.bigfont.render("Game Over!", False, (0, 0, 64))
          self.state_time   = self.world.get_time()
          self.story_time   = self.world.get_time()
          # stories need narrations
          self.narrations   = {}

      def narrate(self, text, duration = 5.0, id = False):
          if not id: id = text
          if self.narrations.has_key(id):
            return
          # render and put to narration list
          img = self.world.bigfont.render(text, False, (255, 255, 255))
          self.narrations[id] = (self.world.get_time(), duration, img)

      def set_state(self, state):
          self.state = state
          self.state_time = self.world.get_time()
      
      def times(self):
          now = self.world.get_time()
          return now - self.story_time, now - self.state_time

      # must overload this
      def update(self):
          pass

      def draw(self, screen, draw_debug = False):
          # draw game over
          if self.gameover:
            screen.blit(self.gameover_img, (self.world.view.sc_w() / 2 - self.gameover_img.get_width() / 2,
                                            self.world.view.sc_h() / 2 - self.gameover_img.get_height() / 2))

          # proccess narratives
          draw_list = []
          for id in self.narrations.keys():
            show_time, duration, img = self.narrations[id]
            if show_time + duration < self.world.get_time():
              del self.narrations[id]
            else:
              draw_list.append((int(show_time), img))
          draw_list.sort(lambda x, y: x[0] - y[0])

          # draw them
          line_y = 10
          for show_time, img in draw_list:
            screen.blit(img, (10, line_y))
            line_y += img.get_height() + 5

class Tutorial(Story):
      def __init__(self, *args):
          Story.__init__(self, *args)

          world = self.world
          # paint some scenery
          for i in xrange(10):
            world.new_actor(actors.Tree, -250 + (500 / 10) * i + random() * 25)
          for i in xrange(5):
            world.new_actor(actors.Explosion, -250 + (500 / 5) * i + random() * 25)

          # enemies
          world.new_actor(actors.ControlledDragon, 70)
          world.new_actor(actors.ControlledDragon, 75)
          world.new_actor(actors.ControlledDragon, 80)

          # and sweet rabbits to protect
          for i in xrange(25):
            world.new_actor(actors.ControlledRabbit, 300 * random())

          # player-controlled object
          self.dude = world.new_actor(actors.Dude, 10)

      def player(self):
          return self.dude

      def update(self):
          story_time, state_time = self.times()

          # ending conditions
          if not self.gameover:
            if self.dude.dead:
              self.set_state("dudedeath")
              self.gameover = True
            elif len(self.world.get_actors(include = [ actors.Rabbit ])) == 0:
              self.set_state("rabbitdeath")
              self.gameover = True
            elif len(self.world.get_actors(include = [ actors.Dragon ])) == 0:
              self.set_state("dragondeath")
              self.gameover = True

          # win!
          if self.state == "dragondeath":
            if state_time < 2.0:
              self.narrate("Awesome job!")
            elif state_time < 4.0:
              self.narrate("You defeated all the dragons!")
            elif state_time < 10.0:
              self.narrate("I guess there is nothing else to do than to mingle with the rabbits now...")

          # lose :(
          elif self.state == "dudedeath":
            if state_time < 2.0:
              self.narrate("Ah...")
            elif state_time < 4.0:
              self.narrate("You were vanquished.")
            elif state_time < 10.0:
              self.narrate("You really should be more careful, who will protect the rabbits now?")

          elif self.state == "rabbitdeath":
            if state_time < 2.0:
              self.narrate("Whoops!")
            elif state_time < 4.0:
              self.narrate("All the rabbits have been killed!")
            elif state_time < 10.0:
              self.narrate("What a cold and sad world it is now. Not blaming anyone, just stating the fact...")

          # intro
          elif self.state == "begin":
            if state_time < 2.0:
              pass
            elif state_time < 5.0:
              self.narrate("These rabbits are being slaughtered by the dragons...")
            elif state_time < 6.0:
              self.narrate("We must protect them.")
              self.set_state("tutorial1")

          # explain the controls
          elif self.state == "tutorial1":
            if state_time < 5.0:
              pass
            elif state_time < 8.0:
              self.narrate("But first, let's get away from the dragons [use the arrow keys].")
            elif state_time < 10.0:
              self.narrate("The left direction seems safer [move left, away from the dragons].")
            else:
              if state_time % 15 < 1.0:
                self.narrate("Please move further to the left so I can explain our world to you.")
              if self.dude.pos < -25.0:
                self.set_state("tutorial2")

          elif self.state == "tutorial2":
            if state_time < 2.0:
              self.narrate("This is far enough, should be safe.")
            if state_time < 6.0:
              self.narrate("Those dragons you saw over there can be pretty dangerous.")
            elif state_time < 8.0:
              self.narrate("You saw them using Earth magic to kill the rabbits.")
            elif state_time < 10.0:
              self.narrate("The Earth magic will kill you, too.")
            elif state_time < 14.0:
              self.narrate("Unless you understand it, that is.")
            elif state_time < 18.0:
              self.narrate("Take a look at the Earth magic field [press 'c'].")
            elif state_time < 20.0:
              self.narrate("And cast an Earth magic ball [hold shift, press 'C'].")
            else:
              field_visible = self.world.get_field(fields.EarthField).visibility
              ballcast      = False
              for particle in self.dude.magic.affects.keys():
                if isinstance(particle, fields.EarthBall):
                  ballcast = True
              if field_visible and ballcast:
                self.set_state("tutorial3")
              if state_time % 15 < 1.0:
                if field_visible:
                  self.narrate("Good, you can see the effects of you Earth magic balls on the field.")
                else:
                  self.narrate("Turn on Earth magic field view [press 'c'].")
                if ballcast:
                  self.narrate("Good, you have cast an Earth magic ball for practice. Nice.")
                else:
                  self.narrate("And also cast an Earth magic ball [hold shift, press 'C'].")

          elif self.state == "tutorial3":
            if state_time < 2.0:
              self.narrate("Very good!")
            elif state_time < 4.0:
              self.narrate("You can see the Earth magic field and the way the Earth magic ball affects it.")
            elif state_time < 10.0:
              self.narrate("You can move the magic ball, too ['a' and 'd' keys].", duration = 10.0)
            elif state_time < 15.0:
              self.narrate("And you can set it's power ['w' and 's' keys].", duration = 10.0)
            elif state_time < 20.0:
              self.narrate("When you are done with a ball, you can release it ['r' key].", duration = 10.0)
            else:
              if state_time % 30 < 1.0:
                self.narrate("Try to make an Earth magic ball [shift, press 'C'] with negative strength and move it close to yourself.", duration = 15.0)
              if state_time % 30 < 5.0:
                self.narrate("You have to turn it's strength down ['w' and 's' keys] and move it ['a' and 'd' keys].", duration = 15.0)
              # check for the healing ball
              for particle in self.dude.magic.affects.keys():
                if isinstance(particle, fields.EarthBall):
                  if self.dude.magic.affects[particle][0] < 0.0:
                    if abs(particle.pos - self.dude.pos) < 1.0:
                      print self.dude.magic.affects[particle]
                      self.set_state("tutorial4")

          elif self.state == "tutorial4":
            if state_time < 2.0:
              self.narrate("Well done!")
            elif state_time < 6.0:
              self.narrate("Negative Earth magic has a restoring effect on health.")
            elif state_time < 10.0:
              self.narrate("It's the opposite of the damaging magic balls the dragons were using.")
            elif state_time < 14.0:
              self.narrate("Two such opposite balls will even cancel each other out!")
            elif state_time < 20.0:
              self.narrate("There are two other types of magic: Light [press 'z'] and Energy [press 'x'].")
            elif state_time < 24.0:
              self.narrate("They operate in a similar way, but have rather different effects.")
            elif state_time < 28.0:
              self.narrate("You should try all three types of magic to get familiar with their use.")
            elif state_time < 35.0:
              self.narrate("When ready, move back toward the dragons.")
            else:
              if state_time % 30 < 2.0:
                self.narrate("Try to use all three types of magic balls ['Z', 'X' and 'C' keys].")
              elif state_time % 30 < 4.0:
                self.narrate("Move closer to the dragons [right arrow] when you feel familiar with the magic.")
              if self.dude.pos > -10.0:
                self.set_state("tutorial5")

          elif self.state == "tutorial5":
            if state_time < 2.0:
              self.narrate("A few last words of advice before you go and fight the dragons.")
            elif state_time < 6.0:
              self.narrate("Aside from making magic balls yourself, you can also capture them.")
            elif state_time < 10.0:
              self.narrate("For example those, that the dragons throw at you [ctrl, right arrow].")
            elif state_time < 15.0:
              self.narrate("But it works on all magic balls [ctrl, left/right arrow or a number].", duration = 10.0)
            elif state_time < 25.0:
              self.narrate("Now go, slay the dragons! Good luck!")
              self.set_state("tutorial6")

          elif self.state == "tutorial6":
            if state_time % 30 > 29:
              rabbits = len(self.world.get_actors(include = [ actors.Rabbit ]))
              self.narrate("Fight the dragons! There are still %u rabbits left to save!" % (rabbits))

class Game:
      def __init__(self):
          # initialize pygame
          pygame.init()
          pygame.mixer.init()
          pygame.mixer.music.load("music/happytheme.ogg")
          #pygame.mixer.music.load("music/warmarch2.ogg")
          pygame.mixer.music.play(-1)
          pygame.display.set_caption('Magic')
          screensize  = (1024, 768)
          self.screen = pygame.display.set_mode(screensize, pygame.FULLSCREEN)
          #screensize  = (1000, 400)
          #self.screen = pygame.display.set_mode(screensize)
          self.clock  = pygame.time.Clock()

          # loading sprites
          self.sprites = sprites = SpriteLoader()
          sprites.load("fire.png", "fireball", 25, resize = (50, 50))
          sprites.load("ice.png", "iceball", 25, resize = (50, 50))
          sprites.load("dude.png", "dude-right", 25, resize = (50, 200))
          sprites.load("dude.png", "dude-left", 25, flip = True, resize = (50, 200))
          sprites.load("rabbit.png", "rabbit-right", 25, resize = (50, 50))
          sprites.load("rabbit.png", "rabbit-left", 25, flip = True, resize = (50, 50))
          sprites.load("dragon.png", "dragon-right", 25, resize = (50, 100))
          sprites.load("dragon.png", "dragon-left", 25, flip = True, resize = (50, 100))
          sprites.load("tree.png", "tree", resize = (600, 400))
          sprites.load("explosion.png", "explosion", resize = (400, 400))
          sprites.load("ashes.png", "ashes", 100, resize = (50, 50))

          # set up game objects
          self.view   = View(screensize, (0, 0, 100, 2))
          self.world  = World(sprites, fields.all, self.view)
          self.story  = Tutorial(self.world)
          self.player = self.story.player()

      def run(self):
          # loop
          forever = True

          # calibrating game speed
          lasttime   = int(time.time())
          frames     = 0
          lastframes = 0
          fps        = 0

          # performance debugging stats
          draw_field_time = 0
          draw_actor_time = 0
          update_actor_time = 0

          # extra debugging(?) output
          draw_hp     = True
          draw_debug  = False
          free_camera = False

          # input states
          get_magic  = False
          cast_magic = False
          sel_magic  = False

          # omit self.
          player = self.player
          world  = self.world
          view   = self.view
          screen = self.screen

          while forever:
            # actors moving
            stime = time.time()
            if not world.paused():
              for actor in world.all_actors():
                actor.update()
            update_actor_time = time.time() - stime

            # storyline evolving
            self.story.update()
          
            # center view on player
            if not free_camera:
              diff = player.pos - view.get_center_x()
              if 30.0 > abs(diff) > 5.0:
                view.move_x(diff * 0.005)
              elif 45.0 > abs(diff) >= 30.0:
                view.move_x(diff * 0.01)
              elif abs(diff) >= 45.0:
                view.move_x(diff * 0.05)
          
            # draw
            # background changes slightly in color
            if world.paused():
              day = -1.0
              screen.fill([16, 32, 96])
            else:
              day = math.sin(time.time()) + 1
              screen.fill([day * 32, 32 + day * 32, 128 + day * 32])
            # draw fields
            stime = time.time()
            for field in world.all_fields():
              field.draw(view, screen, draw_debug = draw_debug)
            draw_field_time = time.time() - stime
            # draw actors (with debug data?)
            debug_offset = 1
            stime = time.time()
            self.world.sort_actors()
            for actor in self.world.all_actors():
              actor.draw(view, screen, draw_hp, int(draw_debug) * debug_offset)
              debug_offset = (debug_offset + 20) % (view.sc_h() - 20 - 100)
            draw_actor_time = time.time() - stime
            # draw performance stats
            if draw_debug:
              fps_txt = world.font.render("FPS: %.1f" % (fps), False, (255, 255, 255))
              stats   = world.font.render("Actors: %u, Draw field=%.3f actors=%.3f, update actors=%.3f" % (len(world.all_actors()), draw_field_time, draw_actor_time, update_actor_time), False, (255, 255, 255))
              screen.blit(fps_txt, (10, 10))
              screen.blit(stats, (10, 25))
            # draw magic selection
            if get_magic:
              i = 1
              local_balls = self.world.get_actors(player.pos - 100, player.pos + 100, lambda x: isinstance(x, fields.MagicParticle))
              for ball in local_balls:
                ball_txt = world.font.render("%u: %s" % (i, str(ball)), False, ball.field.poscolor)
                ball_nr  = world.bigfont.render("%u" % (i), False, ball.field.poscolor)
                screen.blit(ball_txt, (10, 40 + i * 10))
                screen.blit(ball_nr, (view.pl2sc_x(ball.pos), view.sc_h() - 80))
                i += 1
            # draw player's magic (magic selection)
            if sel_magic:
              sel_magic.draw_selection(screen)
            # draw storyline elements
            self.story.draw(screen, draw_debug = draw_debug)
            # drawing done!
            pygame.display.update()
          
            # handle events
            for event in pygame.event.get():
              if event.type == pygame.QUIT:
                forever = False
              
              # key events
              if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                  forever = False

                if event.key == pygame.K_p:
                  world.pause()
          
                # player moving
                elif event.key == pygame.K_LEFT:
                  player.move_left()
                elif event.key == pygame.K_RIGHT:
                  player.move_right()

                elif event.key == pygame.K_j:
                  free_camera = True
                  view.move_x(-10.0)
                elif event.key == pygame.K_k:
                  free_camera = False
                elif event.key == pygame.K_l:
                  free_camera = True
                  view.move_x(+10.0)
          
                # magic moving
                elif sel_magic and event.key == pygame.K_a:
                  player.magic.move(sel_magic, -3.0)
                elif sel_magic and event.key == pygame.K_d:
                  player.magic.move(sel_magic, 3.0)
                elif sel_magic and event.key == pygame.K_w:
                  player.magic.power(sel_magic, diff = 3.0)
                elif sel_magic and event.key == pygame.K_s:
                  player.magic.power(sel_magic, diff = -3.0)
                elif sel_magic and event.key == pygame.K_r:
                  player.magic.release(sel_magic)
                  sel_magic = False
                elif event.key == pygame.K_r:
                  player.magic.release_all()
                  sel_magic = False

                # mode switching
                elif event.key == pygame.K_TAB:
                  #draw_hp    = not draw_hp
                  draw_debug = not draw_debug
                elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                  cast_magic = True
                  sel_magic  = False
                elif event.key == pygame.K_LCTRL or event.key == pygame.K_RCTRL:
                  get_magic  = True
                  sel_magic  = False
                
                # cast_magic & fields
                elif cast_magic and event.key == pygame.K_z:
                  sel_magic = player.magic.new(fields.LightBall)
                  casting = False
                elif cast_magic and event.key == pygame.K_x:
                  sel_magic = player.magic.new(fields.EnergyBall)
                  casting = False
                elif cast_magic and event.key == pygame.K_c:
                  sel_magic = player.magic.new(fields.EarthBall)
                  casting = False

                # toggle magic fields
                elif event.key == pygame.K_z:
                  world.get_field(fields.LightField).toggle_visibility()
                elif event.key == pygame.K_x:
                  world.get_field(fields.EnergyField).toggle_visibility()
                elif event.key == pygame.K_c:
                  world.get_field(fields.EarthField).toggle_visibility()

                # recapture existing particles
                elif get_magic and event.key >= pygame.K_1 and event.key <= pygame.K_9:
                  idx = event.key - pygame.K_1
                  if len(local_balls) > idx:
                    sel_magic = local_balls[idx]
                    player.magic.capture(sel_magic)
                elif get_magic and not cast_magic and event.key == pygame.K_a:
                  capture_ball = False
                  for ball in local_balls:
                    if ball.pos < player.pos:
                      capture_ball = ball
                  if capture_ball:
                    sel_magic = capture_ball
                    player.magic.capture(sel_magic)
                elif get_magic and not cast_magic and event.key == pygame.K_d:
                  capture_ball = False
                  for ball in local_balls:
                    if ball.pos > player.pos:
                      capture_ball = ball
                      break
                  if capture_ball:
                    sel_magic = capture_ball
                    player.magic.capture(sel_magic)
          
              # key releases
              if event.type == pygame.KEYUP:
                # movement
                if event.key == pygame.K_LEFT:
                  player.stop()
                elif event.key == pygame.K_RIGHT:
                  player.stop()

                # magic movement
                elif event.key == pygame.K_a and sel_magic:
                  player.magic.move(sel_magic, 0.0)
                elif event.key == pygame.K_d and sel_magic:
                  player.magic.move(sel_magic, 0.0)

                # input modes
                elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                  cast_magic = False
                elif event.key == pygame.K_LCTRL or event.key == pygame.K_RCTRL:
                  get_magic = False
          
            # calibration
            self.clock.tick(45)
            frames += 1
            if int(time.time()) != lasttime:
              fps = (frames - lastframes)
              lasttime   = int(time.time())
              lastframes = frames
          
if __name__ == "__main__":
   g = Game()
   g.run()
