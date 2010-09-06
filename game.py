#!/usr/bin/python

import time, sys, math, types
from random import random

# pygame
import pygame
from pygame.locals import *

# game libraries
from lib import *
from lib.stories import campaign, testlevels

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
          screensize    = (1024, 768)
          self.graphics = graphics.default_provider(*screensize)
          self.view     = game.View(self.graphics, (0, 100, 0, 50))

          # loading resources
          self.loader = game.ResourceLoader(self.graphics)
          # for title screen
          self.loader.sprite("title-bg", "title-bg", resize = screensize)

      def center_blit(self, img, x, y):
          self.graphics.blit(img, (self.view.sc_w() / 2 - img.get_width() / 2 + x, y))

      story_menu = [
                    stories.campaign.Shepherd.gen_menuitem(),
                    stories.campaign.Massacre.gen_menuitem(),
                    stories.campaign.Blockade.gen_menuitem(),
                    stories.campaign.Siege.gen_menuitem(),
                   { "action": "exit", "txt": "Return" },
                   ]
      test_menu = [
                   stories.testlevels.TestBed.gen_menuitem(),
                   stories.testlevels.MassHunting.gen_menuitem(),
                   stories.testlevels.MassBehaving.gen_menuitem(),
                   { "action": "exit", "txt": "Return" },
                  ]
      title_menu = [
                    { "action": story_menu, "txt": "Campaign" },
                    { "action": test_menu, "txt": "Test levels" },
                    { "action": "exit", "txt": "Exit Game" },
                   ]
      def title_screen(self):
          self.run_menu(self.title_menu)

      def run_menu_item(self, item):
          if item["action"] == "exit":
            return False
          elif type(item["action"]) == types.ClassType and issubclass(item["action"], stories.Story):
            self.run_story(item["action"])
          else:
            self.run_menu(item["action"])
          self.loader.set_music("happytheme")
          return True
      def run_menu(self, menu):
          # loop variables
          forever    = True
          select     = 0

          # interesting music
          self.loader.set_music("happytheme")

          # text
          title       = self.loader.biggoth.render(self.gamename, True, (192, 64, 32))
          titleshadow = self.loader.biggoth.render(self.gamename, True, (48, 48, 48))

          i = 0
          for item in menu:
            item["seq"]  = i
            item["low"]  = self.loader.smallgoth.render(item["txt"], True, (64, 64, 64))
            item["high"] = self.loader.smallgoth.render(item["txt"], True, (192, 192, 192))
            item["pos"]  = 150 + 72 * i
            i += 1

          # bg
          background = self.loader.get_spritelist("title-bg")[0]

          while forever:
            # graphics
            self.graphics.blit(background, (0, 0))
            self.center_blit(titleshadow, 5, 25)
            self.center_blit(title, 0, 20)
            # menu
            for item in menu:
              self.center_blit(item[item["seq"] == select and "high" or "low"], 0, item["pos"])
            # set on screen
            self.graphics.update()

            # events
            for event in pygame.event.get():
              if event.type == QUIT:
                forever = False

              if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                  forever = False
                elif event.key == K_RETURN or event.key == K_SPACE:
                  forever = self.run_menu_item(menu[select])
                elif event.key == K_UP:
                  select -= 1
                elif event.key == K_DOWN:
                  select += 1

              elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                  forever = self.run_menu_item(menu[select])

              elif event.type == MOUSEMOTION:
                # selection with mouse
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

      def run_test(self, Story):
          world = game.World(self.loader, fields.all, self.view)
          story = Story(world)

          forever = True
          while forever:
            for actor in world.get_actors():
              actor.update()
            story.update()
            self.view.update()
            for fieldtype in world.fields.keys():
              world.fields[fieldtype].update()

            if story.game_over: forever = False
            for event in pygame.event.get():
              if event.type == QUIT:
                forever = False
              if event.type == KEYDOWN and event.key == K_ESCAPE:
                forever = False

          return story.game_result

      def run_story(self, Story):
          # set the game up, convenience references (without self.)
          view   = self.view
          screen = self.graphics.screen
          world  = game.World(self.loader, fields.all, view)
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
              for actor in world.get_actors(exclude = [actors.MagicParticle]):
                actor.update()
            update_actors_time = time.time() - actors_stime

            magic_stime = time.time()
            # magic moving
            if not world.paused():
              for actor in world.get_actors(include = [actors.MagicParticle]):
                actor.update()
            update_magic_time = time.time() - magic_stime

            # storyline evolving
            story_stime = time.time()
            story.update()
            update_story_time = time.time() - story_stime
          
            # center view on player
            view.update()
            # update fields
            for fieldtype in world.fields.keys():
              world.fields[fieldtype].update()
            update_time = time.time() - update_stime
          
            ## draw
            self.graphics.clear()
            draw_stime = bg_stime = time.time()
            total_actor_count = total_magic_count = draw_actor_count = draw_magic_count = 0
            # background changes slightly in color
            if world.paused():
              day = -1.0
              self.graphics.fill([16, 32, 96])
            else:
              day = math.sin(time.time()) + 1
              self.graphics.fill([day * 32, 32 + day * 32, 128 + day * 32])

            # draw actors
            sort_stime = time.time()
            world.sort_actors()
            sort_time = time.time() - sort_stime

            actors_stime = time.time()
            for actor in world.get_actors(exclude = [actors.MagicParticle]):
              total_actor_count += 1
              if actor.draw(draw_debug):
                draw_actor_count += 1
            draw_actors_time = time.time() - actors_stime
            # magic particles
            magic_stime = time.time()
            for actor in world.get_actors(include = [actors.MagicParticle]):
              total_magic_count += 1
              if actor.draw(draw_debug):
                draw_magic_count += 1
            draw_magic_time = time.time() - magic_stime

            # draw fields
            fields_stime = time.time()
            for field in world.all_fields():
              field.draw(view, draw_debug = draw_debug)
            draw_fields_time = time.time() - fields_stime

            misc_stime = time.time()
            # draw storyline elements
            story.draw(draw_debug = draw_debug)

            # draw performance stats
            if draw_debug:
              if int(time.time()) != lasttime or not fps_img:
                fps_txt        = "FPS: %.1f" % (fps)
                draw_times_txt = "DRAW=%.3f (fields=%.3f sort=%.3f actors=%.3f magic=%.3f misc=%.3f) actors=%u/%u balls=%u/%u" % \
                                 (draw_time * 1000, draw_fields_time * 1000, sort_time * 1000,
                                 draw_actors_time * 1000, draw_magic_time * 1000, draw_misc_time * 1000,
                                 draw_actor_count, total_actor_count, draw_magic_count, total_magic_count)
                update_times_txt = "UPDATE=%.3f (actors=%.3f magic=%.3f story=%.3f) display.update=%.3f actors=%u, cch=%u, ccm=%u" % \
                                   (update_time * 1000, update_actors_time * 1000, update_magic_time * 1000,
                                    update_story_time * 1000, update_display_time * 1000,
                                    len(world.all_actors()), effects.circle_cache_hit, effects.circle_cache_miss)
                font         = world.loader.debugfont
                color        = (255, 255, 255)
                fps_img      = font.render(fps_txt, True, color)
                draw_times   = font.render(draw_times_txt, True, color)
                update_times = font.render(update_times_txt, True, color)
              self.graphics.fill((0,0,0), (10, 10, fps_img.get_width(), fps_img.get_height()))
              self.graphics.fill((0,0,0), (10, 30, draw_times.get_width(), draw_times.get_height()))
              self.graphics.fill((0,0,0), (10, 50, update_times.get_width(), update_times.get_height()))
              self.graphics.blit(fps_img, (10, 10))
              self.graphics.blit(draw_times, (10, 30))
              self.graphics.blit(update_times, (10, 50))
            
            # draw magic selection
            if get_magic:
              i = 1
              local_balls = world.get_actors(player.pos - 100, player.pos + 100, include = [ actors.MagicParticle ])
              for ball in local_balls:
                ball_txt = world.loader.textfont.render("%u: %s" % (i, str(ball.__class__).split(".")[1]), True, ball.field.color)
                ball_nr  = world.loader.textfont.render("%u" % (i), True, ball.field.color)
                self.graphics.blit(ball_txt, (10, 40 + i * 20))
                self.graphics.blit(ball_nr, (view.pl2sc_x(ball.pos), view.sc_h() - 80))
                i += 1
            draw_misc_time = time.time() - misc_stime
            draw_time = time.time() - draw_stime
            
            # drawing done!
            display_stime = time.time()
            self.graphics.update()
            update_display_time = time.time() - display_stime
          
            ## handle events
            for event in pygame.event.get():
              if event.type == QUIT: forever = False
              
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
                  sel_magic = player.magic.new(actors.TimeBall)
                  sel_magic.selected = True
                  casting = False
                elif event.key == K_x:
                  if sel_magic:
                    sel_magic.selected = False
                  sel_magic = player.magic.new(actors.WindBall)
                  sel_magic.selected = True
                  casting = False
                elif event.key == K_c:
                  if sel_magic:
                    sel_magic.selected = False
                  sel_magic = player.magic.new(actors.LifeBall)
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
                  particles = world.get_actors(pos - 5, pos + 5, include = [actors.MagicParticle])
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
                    sel_magic = new_particle
                    player.magic.capture(sel_magic)
                    sel_magic.selected = True
                    mouse_control      = True
                    pygame.mouse.set_visible(False)

                elif event.button == 3:
                  pos = view.sc2pl_x(event.pos[0])
                  candidates = world.get_actors(pos - 5, pos + 5)
                  if candidates:
                    # find the closest particle
                    closest = 5
                    select  = False
                    for actor in candidates:
                      dist = abs(actor.pos - pos)
                      if dist < closest:
                        closest = dist
                        select = actor
                    if select:
                      select.debug_me ^= 1

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

          return story.game_result
          
if __name__ == "__main__":
   g = Game()
   if len(sys.argv) >= 2:
     if sys.argv[1] == "--profile":
       import cProfile
       cProfile.run("g.title_screen()", "game.stats")
     elif sys.argv[1] == "--test":
       testname = sys.argv[2]
       test = [item['action'] for item in g.test_menu if item['txt'] == testname][0]
       g.run_test(test)

   else:
     g.title_screen()
