#!/usr/bin/python

import cProfile

import time, sys, math
from random import random
from operator import attrgetter

# pygame
import pygame
from pygame.locals import *

# game libraries
import actors, fields, stories, effects

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

      def __init__(self, screen):
          self.spritelists = {}
          self.imagelist   = {}
          self.soundlist   = {}
          self.screen      = screen

          # load fonts
          self.biggoth   = pygame.font.Font("font/Deutsch.ttf", 104)
          self.smallgoth = pygame.font.Font("font/Deutsch.ttf", 56)
          self.textfont  = pygame.font.Font("font/angltrr.ttf", 20)
          self.debugfont = pygame.font.Font("font/freesansbold.ttf", 16)

          # scaling function
          if hasattr(pygame.transform, "smoothscale"):
            self.scale = pygame.transform.smoothscale
          else:
            self.scale = pygame.transform.scale

          # load sprites
          self.sprite("dude_svg", "dude-right", 100, resize = (50, 200))
          self.sprite("dude_svg", "dude-left", 100, flip = True, resize = (50, 200))
          self.sprite("villager", "villager-right", 100, resize = (50, 200))
          self.sprite("villager", "villager-left", 100, flip = True, resize = (50, 200))
          self.sprite("rabbit_svg", "rabbit-right", 100, resize = (50, 50))
          self.sprite("rabbit_svg", "rabbit-left", 100, flip = True, resize = (50, 50))
          self.sprite("dragon_svg", "dragon-right", 100, resize = (50, 100))
          self.sprite("dragon_svg", "dragon-left", 100, flip = True, resize = (50, 100))
          self.sprite("guardian_svg", "guardian-right", 100, resize = (50, 200))
          self.sprite("guardian_svg", "guardian-left", 100, flip = True, resize = (50, 200))

          self.sprite("smallbird", "smallbird-left", 50, resize = (12, 6))
          self.sprite("smallbird", "smallbird-right", 50, flip = True, resize = (12, 6))
          self.sprite("bigbird", "bigbird-left", 100, resize = (25, 12))
          self.sprite("bigbird", "bigbird-right", 100, flip = True, resize = (25, 12))

          self.sprite("tree_svg", "tree", resize = (400, 400))
          self.sprite("sun", "sun", resize = (400, 400))
          self.sprite("cloud", "cloud")
          self.sprite("post", "post", 25)
          self.sprite("hut", "hut")

          self.sprite("hills", "hills")
          self.sprite("grass", "grass")
          self.sprite("oldbiggrass", "oldbiggrass")

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
                img = self.scale(img, resize)
              img = img.convert_alpha(self.screen)
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
                  subimg = self.scale(subimg, resize)
                # TODO: does this help at all?
                subimg = subimg.convert_alpha(self.screen)
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
          # screen / plane
          self.view   = list(view)
          self.plane  = list(plane)
          self.recalculate()
          # camera
          self.anchor    = 0.0
          self.pan       = False # smooth scroll
          self.find_time = 0.5   # seconds
          self.pan_speed = 50.0  # pos/sec
          self.last_time = time.time()

      def recalculate(self):
          view_w, view_h = self.view
          plane_x1, plane_x2, plane_y1, plane_y2 = self.plane
          plane_w = plane_x2 - plane_x1
          plane_h = plane_y2 - plane_y1
          # multiplier to get plane coordinates from view coordinates
          self.mult_x = float(plane_w) / float(view_w)
          self.mult_y = float(plane_h) / float(view_h)
          # offset to apply to plane coordinates
          self.offset_x = plane_x1
          self.offset_y = plane_y1

      def pl_x1(self): return self.plane[0]
      def pl_x2(self): return self.plane[1]
      def pl_y1(self): return self.plane[2]
      def pl_y2(self): return self.plane[3]
      def pl_w(self): return self.plane[1] - self.plane[0]
      def sc_w(self): return self.view[0]
      def sc_h(self): return self.view[1]

      def sc2pl_x(self, x):
          return x * self.mult_x + self.offset_x
      def sc2pl_y(self, y):
          return y * self.mult_y + self.offset_y
      def pl2sc_x(self, x):
          return (x - self.offset_x) / self.mult_x
      def pl2sc_y(self, y):
          return (y - self.offset_y) / self.mult_y

      # camera stuff
      def get_center_x(self):
          return self.plane[0] + float(self.plane[1] - self.plane[0]) / 2.0
      def move_x(self, x):
          self.offset_x += x
          self.plane[0] += x
          self.plane[1] += x
      def set_x(self, x):
          diff = x - self.get_center_x()
          self.move_x(diff)

      def goto(self, anchor):
          if isinstance(anchor, actors.Actor):
            self.set_x(anchor.pos)
          else:
            self.set_x(anchor)
      def follow(self, anchor, immediate = False, pan = False):
          self.anchor = anchor
          self.pan    = pan
          if immediate:
            self.goto(anchor)
      def update(self):
          # passed time
          timediff = min(time.time() - self.last_time, 0.1)
          self.last_time = time.time()
          # noone to follow?
          if not self.anchor:
            return
          # follow
          if isinstance(self.anchor, actors.Actor):
            dst  = self.anchor.pos
            # TODO: should use real movement speed
            speeddiff = self.anchor.speed * 5.0
            diff = speeddiff
            # not too far away
            maxdiff = self.pl_w() / 3
            # focus on magic balls
            if self.anchor.magic and self.anchor.magic.affects:
              balldiff = 0.0
              for ball in self.anchor.magic.affects.keys():
                d = (ball.pos - self.anchor.pos) / 2
                if d > maxdiff: d = maxdiff
                elif d < -maxdiff: d = -maxdiff
                balldiff += d
              balldiff /= len(self.anchor.magic.affects)
              diff += balldiff
            if diff > maxdiff: diff = maxdiff
            elif diff < -maxdiff: diff = -maxdiff
            dst += diff
          else:
            dst = self.anchor
          diff = dst - self.get_center_x()

          # movement
          if self.pan:
            # move with constant speed
            if diff > 0: dir = +1
            else:        dir = -1
            movement = dir * self.pan_speed * timediff
            # end the pan
            if abs(diff) < 10.0:
              self.pan = False
            else:
              self.move_x(movement)
          else:
            if abs(diff) < 5.0:
              const = 0.0
            elif abs(diff) < 10.0:
              const = (abs(diff) - 5.0) / 5.0
            else:
              const = 1.0
            self.move_x(diff * const * timediff / self.find_time)


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
          self.actors   = []
          self.actor_id = 0

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
      def next_actor_id(self):
          id = self.actor_id
          self.actor_id += 1
          return id
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
          self.actors.sort(lambda x, y: cmp(x.stacking, y.stacking) or cmp(x.pos, y.pos))

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
          pygame.key.set_repeat(300, 150)
          self.clock  = pygame.time.Clock()

          # screen params
          screensize  = (1024, 768)
          flags       = FULLSCREEN
          #flags       = FULLSCREEN | HWSURFACE | DOUBLEBUF
          self.screen = pygame.display.set_mode(screensize, flags)
          #screensize  = (800, 600)
          #self.screen = pygame.display.set_mode(screensize)
          self.view   = View(screensize, (0, 100, 0, 50))

          # loading resources
          self.loader = ResourceLoader(self.screen)
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
                  { "action":  stories.Shepherd, "music": "happytheme", "txt": "Gentle Shepherd" },
                  { "action":  stories.Massacre, "music": "warmarch2",  "txt": "Fiery Massacre" },
                  { "action":  stories.Blockade, "music": "warmarch2",  "txt": "Guardian Blockade" },
                  { "action":  stories.Siege,    "music": "warmarch2",  "txt": "Under Siege" },
                  { "action":  "exit", "txt": "Exit Game" },
                 ]
          i = 0
          for item in menu:
            item["seq"]  = i
            item["low"]  = self.loader.smallgoth.render(item["txt"], True, (64, 64, 64))
            item["high"] = self.loader.smallgoth.render(item["txt"], True, (192, 192, 192))
            item["pos"]  = 150 + 72 * i
            i += 1

          # bg
          background = self.loader.get_sprite("title-bg")

          while forever:
            # graphics
            self.screen.blit(background, (0, 0))
            self.center_blit(titleshadow, 5, 25)
            self.center_blit(title, 0, 20)
            # menu
            for item in menu:
              self.center_blit(item[item["seq"] == select and "high" or "low"], 0, item["pos"])
            # set on screen
            pygame.display.update()

            # events
            for event in pygame.event.get():
              if event.type == QUIT:
                forever = False

              if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                  forever = False

                elif event.key == K_UP:
                  select -= 1
                elif event.key == K_DOWN:
                  select += 1

                elif event.key == K_RETURN or event.key == K_SPACE:
                  item = menu[select]
                  if item["action"] == "exit":
                    forever = False
                  else:
                    self.set_music(item["music"])
                    self.run_story(item["action"])
                  self.set_music("happytheme")

              elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                  item = menu[select]
                  if item["action"] == "exit":
                    forever = False
                  else:
                    self.set_music(item["music"])
                    self.run_story(item["action"])
                  self.set_music("happytheme")
              elif event.type == MOUSEMOTION:
                x, y = event.pos
                center = self.view.sc_w() / 2
                for item in menu:
                  ofs = item["low"].get_width() / 2
                  if center - ofs < x < center + ofs:
                    if item["pos"] < y < item["pos"] + item["low"].get_height():
                      select = item["seq"]

            # stay in menu
            if select == len(menu):
              select = 0
            elif select < 0:
              select = len(menu) - 1

            # calibration loop
            self.clock.tick(45)

      def run_story(self, Story):
          # set the game up, convenience references (without self.)
          view   = self.view
          screen = self.screen
          world  = World(self.loader, fields.all, view)
          story  = Story(world)
          player = story.player()

          # loop
          forever = True

          # calibrating game speed
          lasttime   = 0
          frames     = 0
          lastframes = 0
          fps        = 0
          fps_img    = False

          # performance debugging stats
          update_time         = 0
          update_actors_time  = 0
          update_magic_time   = 0
          update_story_time   = 0
          update_display_time = 0
          draw_time        = 0
          draw_fields_time = 0
          sort_time        = 0
          draw_actors_time = 0
          draw_magic_time  = 0
          draw_misc_time   = 0

          # extra debugging(?) output
          draw_debug  = False

          ## input states
          # boolean: capture magic balls
          get_magic = False
          # reference to selected magic ball or False
          sel_magic = False
          # boolean: currently ball selected with mouse
          mouse_control = False
          # boolean: use 'a' and 'd' to control player
          mouse_mode    = False

          while forever:
            ## update
            update_stime = actors_stime = time.time()
            # actors moving
            if not world.paused():
              for actor in world.get_actors(exclude = [fields.MagicParticle]):
                actor.update()
            update_actors_time = time.time() - actors_stime

            magic_stime = time.time()
            # magic moving
            if not world.paused():
              for actor in world.get_actors(include = [fields.MagicParticle]):
                actor.update()
            update_magic_time = time.time() - magic_stime

            # storyline evolving
            story_stime = time.time()
            story.update()
            update_story_time = time.time() - story_stime
          
            # center view on player
            view.update()

            update_time = time.time() - update_stime
          
            ## draw
            draw_stime = bg_stime = time.time()
            # background changes slightly in color
            if world.paused():
              day = -1.0
              screen.fill([16, 32, 96])
            else:
              day = math.sin(time.time()) + 1
              screen.fill([day * 32, 32 + day * 32, 128 + day * 32])

            # draw actors
            sort_stime = time.time()
            world.sort_actors()
            sort_time = time.time() - sort_stime

            actors_stime = time.time()
            debug_offset = 1
            for actor in world.get_actors(exclude = [fields.MagicParticle]):
              actor.draw(screen, int(draw_debug) * debug_offset)
              debug_offset = (debug_offset + 40) % (view.sc_h() - 20 - 100)
            draw_actors_time = time.time() - actors_stime
            # magicparticles
            magic_stime = time.time()
            for actor in world.get_actors(include = [fields.MagicParticle]):
              actor.draw(screen, int(draw_debug) * debug_offset)
              debug_offset = (debug_offset + 40) % (view.sc_h() - 20 - 100)
            draw_magic_time = time.time() - magic_stime

            # draw fields
            fields_stime = time.time()
            for field in world.all_fields():
              field.draw(view, screen, draw_debug = draw_debug)
            draw_fields_time = time.time() - fields_stime

            misc_stime = time.time()
            # draw storyline elements
            story.draw(screen, draw_debug = draw_debug)

            # draw performance stats
            if draw_debug:
              if int(time.time()) != lasttime or not fps_img:
                fps_txt        = "FPS: %.1f" % (fps)
                draw_times_txt = "DRAW=%.3f (fields=%.3f sort=%.3f actors=%.3f magic=%.3f misc=%.3f)" % \
                                 (draw_time * 1000, draw_fields_time * 1000, sort_time * 1000,
                                 draw_actors_time * 1000, draw_magic_time * 1000, draw_misc_time * 1000)
                update_times_txt = "UPDATE=%.3f (actors=%.3f magic=%.3f story=%.3f) display.update=%.3f actors=%u, cch=%u, ccm=%u" % \
                                   (update_time * 1000, update_actors_time * 1000, update_magic_time * 1000,
                                    update_story_time * 1000, update_display_time * 1000,
                                    len(world.all_actors()), effects.circle_cache_hit, effects.circle_cache_miss)
                font         = world.loader.debugfont
                color        = (255, 255, 255)
                fps_img      = font.render(fps_txt, True, color)
                draw_times   = font.render(draw_times_txt, True, color)
                update_times = font.render(update_times_txt, True, color)
              screen.fill((0,0,0), (10, 10, fps_img.get_width(), fps_img.get_height()))
              screen.fill((0,0,0), (10, 30, draw_times.get_width(), draw_times.get_height()))
              screen.fill((0,0,0), (10, 50, update_times.get_width(), update_times.get_height()))
              screen.blit(fps_img, (10, 10))
              screen.blit(draw_times, (10, 30))
              screen.blit(update_times, (10, 50))
            
            # draw magic selection
            if get_magic:
              i = 1
              local_balls = world.get_actors(player.pos - 100, player.pos + 100, include = [ fields.MagicParticle ])
              for ball in local_balls:
                ball_txt = world.loader.textfont.render("%u: %s" % (i, str(ball.__class__).split(".")[1]), True, ball.field.color)
                ball_nr  = world.loader.textfont.render("%u" % (i), True, ball.field.color)
                screen.blit(ball_txt, (10, 40 + i * 20))
                screen.blit(ball_nr, (view.pl2sc_x(ball.pos), view.sc_h() - 80))
                i += 1
            draw_misc_time = time.time() - misc_stime
            draw_time = time.time() - draw_stime
            
            # drawing done!
            display_stime = time.time()
            pygame.display.update()
            update_display_time = time.time() - display_stime
          
            ## handle events
            for event in pygame.event.get():
              if event.type == QUIT:
                forever = False
              
              ## keyboard
              # key events
              if event.type == KEYDOWN:
                # misc
                if event.key == K_ESCAPE:
                  forever = False
                if event.key == K_p:
                  world.pause()
          
                # player moving
                elif event.key == K_LEFT:
                  player.move_left()
                elif event.key == K_RIGHT:
                  player.move_right()
                # mouse_mode player moving
                elif mouse_mode and event.key == K_a:
                  player.move_left()
                elif mouse_mode and event.key == K_d:
                  player.move_right()

                # explicit camera control
                elif event.key == K_j:
                  view.follow(False)
                  view.move_x(-10.0)
                elif event.key == K_k:
                  view.follow(player)
                elif event.key == K_l:
                  view.follow(False)
                  view.move_x(+10.0)
          
                # mode switching
                elif event.key == K_TAB:
                  draw_debug = not draw_debug
                elif event.key == K_LCTRL or event.key == K_RCTRL:
                  get_magic  = True
                  if sel_magic:
                    sel_magic.selected = False
                    sel_magic = False
                elif event.key == K_m:
                  mouse_mode = not mouse_mode
                
                # cast magic balls
                elif event.key == K_z:
                  if sel_magic:
                    sel_magic.selected = False
                  sel_magic = player.magic.new(fields.TimeBall)
                  sel_magic.selected = True
                  casting = False
                elif event.key == K_x:
                  if sel_magic:
                    sel_magic.selected = False
                  sel_magic = player.magic.new(fields.WindBall)
                  sel_magic.selected = True
                  casting = False
                elif event.key == K_c:
                  if sel_magic:
                    sel_magic.selected = False
                  sel_magic = player.magic.new(fields.LifeBall)
                  sel_magic.selected = True
                  casting = False

                # recapture existing particles
                elif get_magic and event.key >= K_1 and event.key <= K_9:
                  idx = event.key - K_1
                  if len(local_balls) > idx:
                    if sel_magic:
                      sel_magic.selected = False
                    sel_magic = local_balls[idx]
                    sel_magic.selected = True
                    player.magic.capture(sel_magic)
                elif get_magic and (event.key == K_a or event.key == K_d):
                  # select ball with arrow keys
                  if sel_magic:
                    refpos = sel_magic.pos
                  else:
                    refpos = player.pos
                  # look for ball in right direction
                  captured_ball = False
                  for ball in local_balls:
                    if event.key == K_a:
                      if ball.pos < refpos:
                        captured_ball = ball
                    elif event.key == K_d:
                      if ball.pos > refpos:
                        captured_ball = ball
                        break
                  if captured_ball:
                    if sel_magic:
                      sel_magic.selected = False
                    sel_magic = captured_ball
                    sel_magic.selected = True
                    player.magic.capture(sel_magic)

                # magic moving
                elif sel_magic and event.key == K_a:
                  player.magic.move(sel_magic, diff = -3.0)
                elif sel_magic and event.key == K_d:
                  player.magic.move(sel_magic, diff = 3.0)
                elif sel_magic and event.key == K_w:
                  player.magic.power(sel_magic, diff = 3.0)
                elif sel_magic and event.key == K_s:
                  player.magic.power(sel_magic, diff = -3.0)

                # release magic
                elif sel_magic and event.key == K_r:
                  if sel_magic:
                    player.magic.release(sel_magic)
                    sel_magic.selected = False
                    sel_magic = False
                elif event.key == K_r:
                  player.magic.release_all()
                  if sel_magic:
                    sel_magic.selected = False
                    sel_magic = False

              # key releases
              elif event.type == KEYUP:
                # movement
                if event.key == K_LEFT:
                  player.stop()
                elif event.key == K_RIGHT:
                  player.stop()
                elif mouse_mode and event.key == K_a:
                  player.stop()
                elif mouse_mode and event.key == K_d:
                  player.stop()

                # magic movement
                elif sel_magic and event.key == K_a:
                  player.magic.move(sel_magic, 0.0)
                elif sel_magic and event.key == K_d:
                  player.magic.move(sel_magic, 0.0)

                # input modes
                elif event.key == K_LCTRL or event.key == K_RCTRL:
                  get_magic = False

              ## mouse
              elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                  pos = view.sc2pl_x(event.pos[0])
                  particles = world.get_actors(pos - 5, pos + 5, include = [fields.MagicParticle])
                  if particles:
                    # find the closest particle
                    closest = 5
                    for particle in particles:
                      dist = abs(particle.pos - pos)
                      if dist < closest:
                        closest = dist
                        new_particle = particle
                    # deselect old
                    if sel_magic:
                      sel_magic.selected = False
                    # capture, select
                    sel_magic          = new_particle
                    player.magic.capture(sel_magic)
                    sel_magic.selected = True
                    mouse_control      = True
                    pygame.mouse.set_visible(False)

                elif event.button == 2:
                  pass

              elif event.type == MOUSEBUTTONUP:
                if event.button == 1:
                  mouse_control = False
                  pygame.mouse.set_visible(True)
                  if sel_magic:
                    player.magic.move(sel_magic, 0)

              elif event.type == MOUSEMOTION and mouse_control and sel_magic:
                x, y = event.rel
                player.magic.move(sel_magic, diff = x / 2)
                player.magic.power(sel_magic, diff = -y / 2)
                
          
            # calibration
            self.clock.tick(50)
            frames += 1
            if int(time.time()) != lasttime:
              fps = (frames - lastframes)
              lasttime   = int(time.time())
              lastframes = frames
          
if __name__ == "__main__":
   g = Game()
   #cProfile.run("g.title_screen()", "game.stats")
   g.title_screen()
