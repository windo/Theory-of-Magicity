#!/usr/bin/python

import time, sys, math
from random import random
from operator import attrgetter

import pygame
from pygame.locals import *

import actors, fields

class ResourceLoader:
      """
      Load images and divide them to separate surfaces
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
      def __init__(self, loader, fieldtypes, view):
          self.loader   = loader
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

class Story:
      def __init__(self, world):
          self.world = world
          # story state
          self.state        = "begin"
          self.game_over    = False
          self.game_result  = None
          self.state_time   = self.world.get_time()
          self.story_time   = self.world.get_time()
          # stories need narrations
          self.narrations   = {}

      def narrate(self, text, duration = 5.0, id = False):
          if not id: id = text
          if self.narrations.has_key(id):
            return
          # render and put to narration list
          img = self.world.loader.textfont.render(text, True, (255, 255, 255))
          self.narrations[id] = (self.world.get_time(), duration, img)

      def set_state(self, state):
          self.state = state
          self.state_time = self.world.get_time()
      def set_result(self, result):
          self.game_over     = True
          self.game_result   = result
          if result:
            self.game_over_img = self.world.loader.smallgoth.render("Game Won!", True, (0, 0, 64))
          else:
            self.game_over_img = self.world.loader.smallgoth.render("Game Over!", True, (0, 0, 64))
      
      def times(self):
          now = self.world.get_time()
          return now - self.story_time, now - self.state_time

      # must overload this
      def update(self):
          pass

      def draw(self, screen, draw_debug = False):
          # draw game over
          if self.game_over:
            screen.blit(self.game_over_img,
                        (self.world.view.sc_w() / 2 - self.game_over_img.get_width() / 2,
                         self.world.view.sc_h() / 2 - self.game_over_img.get_height() / 2 - 100))

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
          for i in xrange(3):
            world.new_actor(actors.Sun, -250 + (500 / 3) * i + random() * 25)

          # enemies
          world.new_actor(actors.ControlledDragon, 70)
          world.new_actor(actors.ControlledDragon, 75)
          world.new_actor(actors.ControlledDragon, 80)

          # and sweet rabbits to protect
          for i in xrange(50):
            world.new_actor(actors.ControlledRabbit, -250 + 500 * random())

          # player-controlled object
          self.dude = world.new_actor(actors.Dude, 10)

      def player(self):
          return self.dude

      def update(self):
          story_time, state_time = self.times()

          # ending conditions
          if not self.game_over:
            if self.dude.dead:
              self.set_state("dudedeath")
              self.set_result(False)
            elif len(self.world.get_actors(include = [ actors.Rabbit ])) == 0:
              self.set_state("rabbitdeath")
              self.set_result(False)
            elif len(self.world.get_actors(include = [ actors.Dragon ])) == 0:
              self.set_state("dragondeath")
              self.set_result(True)

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
                  self.narrate("Turn on Earth magic field view [press 'c'].", duration = 10.0)
                if ballcast:
                  self.narrate("Good, you have cast an Earth magic ball for practice. Nice.")
                else:
                  self.narrate("And also cast an Earth magic ball [hold shift, press 'C'].", duration = 10.0)

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
                self.narrate("Try to make an Earth magic ball [shift, press 'C'].", duration = 15.0)
              elif state_time % 30 < 3.0:
                self.narrate("Make it's power negative ['s' key].", duration = 15.0)
              elif state_time % 30 < 5.0:
                self.narrate("And move it close to yourself ['a' and 'd' keys].", duration = 15.0)
              # check for the healing ball
              for particle in self.dude.magic.affects.keys():
                if isinstance(particle, fields.EarthBall):
                  if self.dude.magic.affects[particle][1] < 0.0:
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
                self.narrate("Try all three types of magic balls ['Z', 'X' and 'C' keys].", duration = 15.0)
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
              self.narrate("For example those, that the dragons throw at you [ctrl, right arrow].", duration = 15.0)
            elif state_time < 15.0:
              self.narrate("But it works on all magic balls [ctrl, left/right arrow or a number].", duration = 15.0)
            elif state_time < 25.0:
              self.narrate("Now go, slay the dragons! Good luck!")
              self.set_state("tutorial6")

          elif self.state == "tutorial6":
            if state_time % 30 > 29:
              rabbits = len(self.world.get_actors(include = [ actors.Rabbit ]))
              self.narrate("Fight the dragons! There are still %u rabbits left to save!" % (rabbits))

class Blockade(Story):
      def __init__(self, *args):
          Story.__init__(self, *args)

          world = self.world
          # paint some scenery
          for i in xrange(10):
            world.new_actor(actors.Tree, -250 + (500 / 10) * i + random() * 25)
          for i in xrange(3):
            world.new_actor(actors.Sun, -250 + (500 / 3) * i + random() * 25)

          # enemies
          world.new_actor(actors.ControlledGuardian, 50)
          world.new_actor(actors.ControlledGuardian, 100)

          # player-controlled object
          self.dude = world.new_actor(actors.Dude, 0)

      def player(self):
          return self.dude

      def update(self):
          story_time, state_time = self.times()
          
          if not self.game_over:
            if self.dude.pos > 100.0:
               self.set_state("passed")
               self.set_result(True)
            elif self.dude.dead:
               self.set_state("dudedead")
               self.set_result(False)

          if self.state == "passed":
             if state_time < 2.0:
               self.narrate("Aha!")
             elif state_time < 4.0:
               self.narrate("The guardians can be passed after all!")
             elif state_time < 8.0:
               self.narrate("Well done, I can now continue the journey.")

          elif self.state == "dudedead":
             if state_time < 2.0:
               self.narrate("Ah...")
             elif state_time < 4.0:
               self.narrate("Defeated by the dragons, what a sad fate.")

          elif self.state == "begin":
             if state_time < 2.0:
               self.narrate("I've been fleeing hordes of dragons for several days now.")
             elif state_time < 5.0:
               self.narrate("But now these guardians seem to block my path.")
             elif state_time < 10.0:
               self.narrate("The guardians don't seem violent, but they do not seem to want to let me through.")
             elif state_time < 14.0:
               self.narrate("I must find a way through - otherways the dragons are going to get me.")
               self.set_state("onslaught")

          if self.state == "onslaught":
            if state_time % 15.0 < 1.0:
              dragons = len(self.world.get_actors(include = [actors.Dragon]))
              for i in xrange(2 - dragons):
                dragon = self.world.new_actor(actors.ControlledDragon, self.dude.pos - 75 + random() * 10)
                dragon.waypoint = 200.0

class Game:
      def __init__(self):
          # initialize pygame
          pygame.init()
          pygame.mixer.init()
          pygame.display.set_caption('Magic')
          self.clock  = pygame.time.Clock()

          # screen params
          screensize  = (1024, 768)
          self.screen = pygame.display.set_mode(screensize, pygame.FULLSCREEN)
          self.view   = View(screensize, (0, 0, 100, 2))

          # loading sprites
          self.loader = loader = ResourceLoader()
          loader.sprite("fire", "fireball", 25, resize = (50, 50))
          loader.sprite("ice", "iceball", 25, resize = (50, 50))
          loader.sprite("ashes", "ashes", 100, resize = (50, 50))
          
          loader.sprite("dude_svg", "dude-right", 100, resize = (50, 200))
          loader.sprite("dude_svg", "dude-left", 100, flip = True, resize = (50, 200))
          loader.sprite("rabbit_svg", "rabbit-right", 100, resize = (50, 50))
          loader.sprite("rabbit_svg", "rabbit-left", 100, flip = True, resize = (50, 50))
          loader.sprite("dragon_svg", "dragon-right", 100, resize = (50, 100))
          loader.sprite("dragon_svg", "dragon-left", 100, flip = True, resize = (50, 100))
          loader.sprite("guardian_svg", "guardian-right", 100, resize = (50, 200))
          loader.sprite("guardian_svg", "guardian-left", 100, flip = True, resize = (50, 200))

          loader.sprite("tree", "tree", resize = (600, 400))
          loader.sprite("sun", "sun", resize = (400, 400))
          loader.sprite("title-bg", resize = screensize)

          loader.sounds(["cry", "cape1", "cape2", "step"])
          loader.sounds(["beep1", "beep2", "jump"])
          loader.sounds(["moan1", "moan2", "crackle1", "crackle2"])

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
          gamename    = "Theory of Magicity"
          title       = self.loader.biggoth.render(gamename, True, (192, 64, 32))
          titleshadow = self.loader.biggoth.render(gamename, True, (48, 48, 48))

          menu = [
                  { "id":  "tutorial", "txt": "Save the Rabbits" },
                  { "id":  "blockade", "txt": "Face the Blockade" },
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
                  elif action == "tutorial":
                    self.set_music("warmarch2")
                    self.run_story(Tutorial)
                  elif action == "blockade":
                    self.set_music("warmarch2")
                    self.run_story(Blockade)
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
