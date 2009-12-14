#!/usr/bin/python

import time, sys, math
from random import random
from operator import attrgetter

import pygame
from pygame.locals import *

import actors, fields, stories

class ResourceLoader:
      """
      Load images and divide them to separate surfaces
      Load fonts
      Load sounds
      """
      class NoImage(Exception):
            def __init__(self, name):
                self.name = name
            def __str__(self):
                return "No Image %s" % (self.name) 

      def __init__(self):
          self.spritelists = {}
          self.imagelist   = {}
          self.soundlist   = {}

          # load fonts
          self.biggoth   = pygame.font.Font("font/Deutsch.ttf", 104)
          self.smallgoth = pygame.font.Font("font/Deutsch.ttf", 56)
          self.textfont  = pygame.font.Font("font/angltrr.ttf", 20)
          self.debugfont = pygame.font.Font("font/freesansbold.ttf", 16)

          # load sprites
          self.sprite("fire", "fireball", 25, resize = (50, 50))
          self.sprite("ice", "iceball", 25, resize = (50, 50))
          self.sprite("ashes", "ashes", 100, resize = (50, 50))
          
          self.sprite("dude_svg", "dude-right", 100, resize = (50, 200))
          self.sprite("dude_svg", "dude-left", 100, flip = True, resize = (50, 200))
          self.sprite("rabbit_svg", "rabbit-right", 100, resize = (50, 50))
          self.sprite("rabbit_svg", "rabbit-left", 100, flip = True, resize = (50, 50))
          self.sprite("dragon_svg", "dragon-right", 100, resize = (50, 100))
          self.sprite("dragon_svg", "dragon-left", 100, flip = True, resize = (50, 100))
          self.sprite("guardian_svg", "guardian-right", 100, resize = (50, 200))
          self.sprite("guardian_svg", "guardian-left", 100, flip = True, resize = (50, 200))

          self.sprite("tree", "tree", resize = (600, 400))
          self.sprite("sun", "sun", resize = (400, 400))
          self.sprite("post", "post", 25)

          # load sounds
          self.sounds(["cry", "cape1", "cape2", "step"])
          self.sounds(["beep1", "beep2", "jump"])
          self.sounds(["moan1", "moan2", "crackle1", "crackle2"])

      def sprite(self, name, listname = False, width = False, start = 0, to = False, flip = False, resize = False):
          # load the file, if not already loaded
          if not self.imagelist.has_key(name):
            self.imagelist[name] = pygame.image.load("img/%s.png" % (name))
          img = self.imagelist[name]

          # make an image list as well?
          if listname:
            if not width:
              if flip:
                img = pygame.transform.flip(img, True, False)
              if resize:
                # TODO: newer pygame could use smoothscale
                img = pygame.transform.scale(img, resize)
              self.spritelists[listname] = [img]
            else:
              # use all subsurfaces?
              if not to:
                to = int(img.get_width() / width)
              self.spritelists[listname] = []
              for i in xrange(start, to):
                rect = [ i * width, 0, width, img.get_height() ]
                subimg = img.subsurface(rect)
                if flip:
                  subimg = pygame.transform.flip(subimg, True, False)
                if resize:
                  subimg = pygame.transform.scale(subimg, resize)
                self.spritelists[listname].append(subimg)

      def get_sprite(self, name):
          if name in self.imagelist.keys():
            return self.imagelist[name]
          else:
            raise self.NoImage(name)
      def get_spritelist(self, name):
          if name in self.spritelists.keys():
            return self.spritelists[name]
          else:
            raise self.NoImage(name)

      def sounds(self, load_sounds):
          for load_sound in load_sounds:
            self.sound(load_sound)
      def sound(self, name):
          if not self.soundlist.has_key(name):
            snd = pygame.mixer.Sound("sound/%s.ogg" % (name))
            self.soundlist[name] = snd
      def play_sound(self, name):
          self.soundlist[name].play()

class View:
      """
      Viewport/scale to use for translating in-game coordinates to screen coordinates
      and vice versa
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
      def set_x(self, x):
          diff = x - self.get_center_x()
          self.move_x(diff)

      def sc2pl_x(self, x):
          return x * self.mult_x + self.offset_x
      def sc2pl_y(self, y):
          return self.offset_y - y * self.mult_y
      def pl2sc_x(self, x):
          return (x - self.offset_x) / self.mult_x
      def pl2sc_y(self, y):
          return (self.offset_y - y) / self.mult_y

class World:
      """
      A container for all level objects (actors, fields)
      A time source
      Also keeps ResourceLoader instance reference
      """
      def __init__(self, loader, fieldtypes, view):
          self.loader      = loader
          self.view        = view
          self.time_offset = 0.0
          self.pause_start = False

          # world objects
          self.fields  = {}
          for fieldtype in fieldtypes:
            field = fieldtype(loader)
            self.fields[fieldtype] = field
          self.actors  = []

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

class Game:
      """
      Implements title screen, menu
      Runs different levels (stories) - the main game loop
      """
      gamename    = "Theory of Magicity"
      def __init__(self):
          # initialize pygame
          pygame.init()
          pygame.mixer.init()
          pygame.display.set_caption(self.gamename)
          self.clock  = pygame.time.Clock()

          # screen params
          screensize  = (1024, 768)
          self.screen = pygame.display.set_mode(screensize, pygame.FULLSCREEN)
          #screensize  = (800, 600)
          #self.screen = pygame.display.set_mode(screensize)
          self.view   = View(screensize, (0, 0, 100, 2))

          # loading resources
          self.loader = ResourceLoader()
          # for title screen
          self.loader.sprite("title-bg", resize = screensize)

      def center_blit(self, img, x, y):
          self.screen.blit(img, (self.view.sc_w() / 2 - img.get_width() / 2 + x, y))
          
      def set_music(self, track):
          pygame.mixer.music.load("music/%s.ogg" % (track))
          pygame.mixer.music.set_volume(0.1)
          pygame.mixer.music.play(-1)

      def title_screen(self):
          # loop variables
          forever    = True
          select     = 0

          # interesting music
          self.set_music("happytheme")

          # text
          title       = self.loader.biggoth.render(self.gamename, True, (192, 64, 32))
          titleshadow = self.loader.biggoth.render(self.gamename, True, (48, 48, 48))

          menu = [
                  { "id":  "shepherd", "txt": "Gentle Shepherd" },
                  { "id":  "salvation", "txt": "Rabbits` Salvation" },
                  { "id":  "blockade", "txt": "Guardian Blockade" },
                  { "id":  "exit", "txt": "Exit Game" },
                 ]
          for item in menu:
            item["low"]  = self.loader.smallgoth.render(item["txt"], True, (64, 64, 64))
            item["high"] = self.loader.smallgoth.render(item["txt"], True, (192, 192, 192))

          # bg
          background = self.loader.get_sprite("title-bg")

          while forever:
            # graphics
            self.screen.blit(background, (0, 0))
            self.center_blit(titleshadow, 5, 25)
            self.center_blit(title, 0, 20)
            # menu
            i = 0
            for item in menu:
              pos = 150 + 72 * i
              if i == select:
                self.center_blit(item["high"], 0, pos)
              else:
                self.center_blit(item["low"], 0, pos)
              i += 1
            # set on screen
            pygame.display.update()

            # events
            for event in pygame.event.get():
              if event.type == pygame.QUIT:
                forever = False

              if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                  forever = False

                elif event.key == pygame.K_UP:
                  select -= 1
                elif event.key == pygame.K_DOWN:
                  select += 1

                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                  action = menu[select]["id"]
                  print "Running level: %s" % (action)
                  if action == "exit":
                    forever = False
                  elif action == "shepherd":
                    self.set_music("happytheme")
                    self.run_story(stories.Shepherd)
                  elif action == "salvation":
                    self.set_music("warmarch2")
                    self.run_story(stories.Salvation)
                  elif action == "blockade":
                    self.set_music("warmarch2")
                    self.run_story(stories.Blockade)
                  self.set_music("happytheme")

            # stay in menu
            if select == len(menu):
              select = 0
            elif select < 0:
              select = len(menu) - 1

            # calibration loop
            self.clock.tick(45)

      def run_story(self, Story):
          # set the game up
          view   = self.view
          screen = self.screen
          world  = World(self.loader, fields.all, view)
          story  = Story(world)
          player = story.player()

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

          while forever:
            # actors moving
            stime = time.time()
            if not world.paused():
              for actor in world.all_actors():
                actor.update()
            update_actor_time = time.time() - stime

            # storyline evolving
            story.update()
          
            # center view on player
            if not free_camera:
              diff = player.pos - view.get_center_x()
              if 30.0 > abs(diff) > 5.0:
                view.move_x(diff * 0.01)
              elif 45.0 > abs(diff) >= 30.0:
                view.move_x(diff * 0.02)
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
            world.sort_actors()
            for actor in world.all_actors():
              actor.draw(view, screen, draw_hp, int(draw_debug) * debug_offset)
              debug_offset = (debug_offset + 20) % (view.sc_h() - 20 - 100)
            draw_actor_time = time.time() - stime
            # draw performance stats
            if draw_debug:
              fps_txt = world.loader.debugfont.render("FPS: %.1f" % (fps), True, (255, 255, 255))
              stats   = world.loader.debugfont.render("Actors: %u, Draw field=%.3f actors=%.3f, update actors=%.3f" % (len(world.all_actors()), draw_field_time, draw_actor_time, update_actor_time), True, (255, 255, 255))
              screen.blit(fps_txt, (10, 10))
              screen.blit(stats, (10, 25))
            # draw magic selection
            if get_magic:
              i = 1
              local_balls = world.get_actors(player.pos - 100, player.pos + 100, include = [ fields.MagicParticle ])
              for ball in local_balls:
                ball_txt = world.loader.textfont.render("%u: %s" % (i, str(ball.__class__).split(".")[1]), True, ball.field.poscolor)
                ball_nr  = world.loader.textfont.render("%u" % (i), True, ball.field.poscolor)
                screen.blit(ball_txt, (10, 40 + i * 20))
                screen.blit(ball_nr, (view.pl2sc_x(ball.pos), view.sc_h() - 80))
                i += 1
            # draw player's magic (magic selection)
            if sel_magic:
              sel_magic.draw_selection(screen)
            # draw storyline elements
            story.draw(screen, draw_debug = draw_debug)
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
   g.title_screen()
