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

      def load(self, filename, listname = False, width = False, start = 0, to = False, flip = False):
          # load the file, if not already loaded
          if not self.images.has_key(filename):
            self.images[filename] = pygame.image.load("img/" + filename)
          img = self.images[filename]

          # make an image list as well?
          if listname:
            if not width:
              if flip:
                img = pygame.transform.flip(img, True, False)
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
          self.bigfont = pygame.font.SysFont("any", 20)

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
      def get_actors(self, x1 = False, x2 = False, filter = False):
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
            ret.append(actor)
          return ret
      def sort_actors(self):
          self.actors.sort(key = attrgetter("pos"))

      # field management
      def get_field(self, fieldtype):
          return self.fields[fieldtype]
      def all_fields(self):
          return self.fields.values()

class Game:
      def __init__(self):
          # initialize pygame
          pygame.init()
          pygame.mixer.init()
          #pygame.mixer.music.load("music/happytheme.ogg")
          #pygame.mixer.music.load("music/warmarch2.ogg")
          #pygame.mixer.music.play(-1)
          pygame.display.set_caption('Magic')
          screensize  = (1200, 300)
          self.screen = pygame.display.set_mode(screensize)
          self.clock  = pygame.time.Clock()

          # loading sprites
          self.sprites = sprites = SpriteLoader()
          sprites.load("fire.png", "fireball", 25)
          sprites.load("ice.png", "iceball", 25)
          sprites.load("death.png", "deathball", 25)
          sprites.load("life.png", "lifeball", 25)
          sprites.load("quick.png", "quickball", 25)
          sprites.load("dude.png", "dude-right", 25)
          sprites.load("dude.png", "dude-left", 25, flip = True)
          sprites.load("rabbit.png", "rabbit-right", 25)
          sprites.load("rabbit.png", "rabbit-left", 25, flip = True)
          sprites.load("dragon.png", "dragon-right", 25)
          sprites.load("dragon.png", "dragon-left", 25, flip = True)
          sprites.load("tree.png", "tree")

          # set up game objects
          self.view   = view   = View(screensize, (0, 0, 100, 2))
          self.world  = world  = World(sprites, fields.all, view)

          for i in xrange(10):
            world.new_actor(actors.Tree, -250 + 100 * i)
          world.new_actor(actors.ControlledDragon, 70)
          world.new_actor(actors.ControlledDragon, 75)
          world.new_actor(actors.ControlledDragon, 80)
          for i in xrange(25):
            world.new_actor(actors.ControlledRabbit, 300 * random())

          # player-controlled object
          self.dude = world.new_actor(actors.Dude, 10)

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
          draw_hp     = False
          draw_debug  = False
          free_camera = False

          # input states
          get_magic  = False
          cast_magic = False
          sel_magic  = False

          # omit self.
          dude   = self.dude
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
          
            # center view to dude
            if not free_camera:
              diff = dude.pos - view.get_center_x()
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
              field.draw(view, screen)
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
              local_balls = self.world.get_actors(dude.pos - 100, dude.pos + 100, lambda x: isinstance(x, fields.MagicParticle))
              for ball in local_balls:
                ball_txt = world.font.render("%u: %s" % (i, str(ball)), False, ball.field.poscolor)
                ball_nr  = world.bigfont.render("%u" % (i), False, ball.field.poscolor)
                screen.blit(ball_txt, (10, 40 + i * 10))
                screen.blit(ball_nr, (view.pl2sc_x(ball.pos), view.sc_h() - 80))
                i += 1
            # draw dude's magic (magic selection)
            if sel_magic:
              pygame.draw.circle(screen, (255, 255, 255), (view.pl2sc_x(sel_magic.pos), view.sc_h() - 40), 25, 1)
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
          
                # dude moving
                elif event.key == pygame.K_LEFT:
                  dude.move_left()
                elif event.key == pygame.K_RIGHT:
                  dude.move_right()

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
                  dude.magic.move_left(sel_magic)
                elif sel_magic and event.key == pygame.K_d:
                  dude.magic.move_right(sel_magic)
                elif sel_magic and event.key == pygame.K_w:
                  dude.magic.power_up(sel_magic)
                elif sel_magic and event.key == pygame.K_s:
                  dude.magic.power_down(sel_magic)
                elif sel_magic and event.key == pygame.K_r:
                  dude.magic.release(sel_magic)
                  sel_magic == False
                elif event.key == pygame.K_r:
                  dude.magic.release_all()
                  sel_magic == False

                # mode switching
                elif event.key == pygame.K_TAB:
                  draw_hp    = not draw_hp
                  draw_debug = not draw_debug
                elif event.key == pygame.K_LSHIFT:
                  cast_magic = True
                  sel_magic  = False
                elif event.key == pygame.K_LCTRL:
                  get_magic  = True
                  sel_magic  = False
                
                # cast_magic & fields
                elif cast_magic and event.key == pygame.K_z:
                  sel_magic = dude.magic.new(fields.LightBall)
                  casting = False
                elif cast_magic and event.key == pygame.K_x:
                  sel_magic = dude.magic.new(fields.EnergyBall)
                  casting = False
                elif cast_magic and event.key == pygame.K_c:
                  sel_magic = dude.magic.new(fields.EarthBall)
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
                    dude.magic.capture(sel_magic)
                elif get_magic and not cast_magic and event.key == pygame.K_a:
                  capture_ball = False
                  for ball in local_balls:
                    if ball.pos < dude.pos:
                      capture_ball = ball
                  if capture_ball:
                    sel_magic = capture_ball
                    dude.magic.capture(sel_magic)
                elif get_magic and not cast_magic and event.key == pygame.K_d:
                  capture_ball = False
                  for ball in local_balls:
                    if ball.pos > dude.pos:
                      capture_ball = ball
                      break
                  if capture_ball:
                    sel_magic = capture_ball
                    dude.magic.capture(sel_magic)
          
              # key releases
              if event.type == pygame.KEYUP:
                # movement
                if event.key == pygame.K_LEFT:
                  dude.stop()
                elif event.key == pygame.K_RIGHT:
                  dude.stop()

                # magic movement
                elif event.key == pygame.K_a and sel_magic:
                  dude.magic.stop(sel_magic)
                elif event.key == pygame.K_d and sel_magic:
                  dude.magic.stop(sel_magic)

                # input modes
                elif event.key == pygame.K_LSHIFT:
                  cast_magic = False
                elif event.key == pygame.K_LCTRL:
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
