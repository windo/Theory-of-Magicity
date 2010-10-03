import pygame, time, math

import actors
from camera import Camera
from inputs import *
from fields import all as fieldtypes
from resources import Resources
import debug
dbg = debug.dbg

import pygame
from pygame.locals import *

class TimeKeeper:
      # during heavy processing, how much lag (in event processing) to accept
      max_lag = 0.5

      def __init__(self):
          # game/real time are modified in steps by wait() function
          # this can be slowed down or sped up
          self.game_time = 0.0
          self.game_time_speed = 1.0
          # used to restore after unpausing
          self.saved_game_time_speed = 1.0
          # last real time we wait()ed to
          self.last_real_time = time.time()

          # upcoming schedule
          self.real_queue = []
          self.game_queue = []

      # game/real time management
      def get_game_time(self):
          return self.game_time
      def get_real_time(self):
          return self.last_real_time
      def game_to_real(self, t):
          game_ofs = t - self.game_time
          return self.last_real_time + game_ofs / self.game_time_speed

      def set_game_speed(self, speed):
          self.game_time_speed = speed
      def get_game_speed(self):
          return self.game_time_speed
      def pause(self):
          if self.paused():
            self.set_game_speed(self.saved_game_time_speed)
          else:
            self.saved_game_time_speed = self.get_game_speed()
            self.set_game_speed(0.0)
      def paused(self):
          return self.get_game_speed() == 0.0

      # schedule management
      class Event:
            def __init__(self, name, t, interval, game):
                self.name = name
                self.time = t
                self.interval = interval
                self.game = game
            def __repr__(self):
                return "%s %.3f/%.3f game=%s" % (self.name, self.time, self.interval, self.game)
            def __str__(self):
                return self.__repr__()

      def schedule(self, name, interval = None, game = False):
          if game:
            queue = self.game_queue
            t = self.get_game_time() + (interval or 0)
          else:
            queue = self.real_queue
            t = self.get_real_time() + (interval or 0)
          queue.append(self.Event(name, t, interval, game))
          queue.sort(lambda x, y: cmp(x.time, y.time))

      # scheduling itself
      def get_next_event(self):
          if self.paused():
            return self.real_queue.pop(0)
          else:
            real_event_time = self.real_queue[0].time
            game_event_time = self.game_to_real(self.game_queue[0].time)
            if real_event_time < game_event_time:
              return self.real_queue.pop(0)
            else:
              return self.game_queue.pop(0)
      def event_time(self, event):
          if event.game:
            return self.game_to_real(event.time)
          else:
            return event.time

      def wait_for_event(self):
          """
          Sleep until the next scheduled event and return it's name
          Reschedule the event
          """
          e = self.get_next_event()
          self.sleep_until(self.event_time(e))
          if e.interval is not None:
            self.schedule(e.name, e.interval, e.game)
          return e.name
      def sleep_until(self, wakeup_time):
          """
          Sleep until specified time, updating game and real time as needed
          """
          real_time_step = game_time_step = wakeup_time - self.last_real_time
          sleep_time = wakeup_time - time.time()
          if sleep_time > 0:
            time.sleep(sleep_time)
          elif sleep_time < -self.max_lag:
            # lagging too much, step faster
            dbg("Event processing lagging %.3fs, lowering real time frequencies" % (-sleep_time))
            real_time_step *= (-sleep_time / self.max_lag) ** 2
          else:
            # accept some lag
            pass
          # update time
          self.last_real_time += real_time_step
          self.game_time += game_time_step * self.game_time_speed

class World:
      """
      A container for all level objects (actors, fields)
      A time source
      """
      def __init__(self, graphics, Story, target_fps = 30.0, game_speed = 1.0):
          self.graphics = graphics
          self.camera = Camera(self.graphics, (0, 100, 0, 50))

          self._timekeeper = TimeKeeper()
          self._timekeeper.schedule('draw', 1.0 / target_fps)
          self._timekeeper.schedule('input', 1.0 / 100.0)
          self._timekeeper.schedule('update', 1.0 / 50.0, game = True)
          self._timekeeper.set_game_speed(game_speed)

          # world objects
          self.fields = {}
          for fieldtype in fieldtypes:
            field = fieldtype()
            self.fields[fieldtype] = field
          self.actors = []
          self.actor_id = 0

          # initiate story
          self.story = Story(self)
          self.run()

      def get_time(self): return self._timekeeper.get_game_time()
      def pause(self): return self._timekeeper.pause()

      def run(self):
          rsc = Resources()
          tm = debug.StatSet('World main loop timers')
          tm.add(debug.Timer, 
                 'update', 'update_actors', 'update_magic', 'update_fields',
                 'draw', 'draw_actors', 'draw_magic', 'draw_fields', 'events', 'calibrate')
          ct = debug.StatSet('World main loop counters')
          ct.add(debug.RateCounter, 'fps', 'update', 'input')
          rate_img = draw_times_img = update_times_img = None
          debug_rl = debug.RateLimit(1.0, exp = 0)
          story = self.story
          player = story.get_player()

          # extra debugging output
          draw_debug  = False

          # input event handlers
          if player is not None:
            c_char = CharacterControl(self, player)
          else:
            c_char = None
          c_game = GameControl(self, player)

          while True:
            # exit condition
            if story.exit_now == True:
              return
            
            # debug stuff
            if debug_rl.check():
              if draw_debug:
                # dump stats to debug log
                tm.dump()
                ct.dump()

              if draw_debug and not self._timekeeper.paused():
                rate_txt = "FPS: %.1f UPDATE: %.1f EVENT: %.1f" % (ct.fps, ct.update, ct.input)

                draw_left = tm.draw - tm.draw_actors - tm.draw_magic - tm.draw_fields
                draw_txt = "DRAW=%.3f" % (tm.draw)
                draw_txt += " (actors=%.3f/%u%% magic=%.3f/%u%% fields=%.3f/%u%% left=%.3f/%u%%)" % \
                            (tm.draw_actors, tm.draw_actors / tm.draw * 100,
                             tm.draw_magic, tm.draw_actors / tm.draw * 100,
                             tm.draw_fields, tm.draw_actors / tm.draw * 100,
                             draw_left, draw_left / tm.draw * 100)
                draw_txt += " actors=%u/%u balls=%u/%u" % \
                            (draw_actor_count, total_actor_count, draw_magic_count, total_magic_count)
                update_left = tm.update - tm.update_actors - tm.update_magic - tm.update_fields
                update_txt = "UPDATE=%.3f" % (tm.update)
                update_txt += " (actors=%.3f/%u%% magic=%.3f/%u%% fields=%.3f/%u%% left=%.3f/%u%%) calibrate=%.3f" % \
                            (tm.update_actors, tm.update_actors / tm.update * 100,
                             tm.update_magic, tm.update_actors / tm.update * 100,
                             tm.update_fields, tm.update_actors / tm.update * 100,
                             update_left, update_left / tm.update * 100,
                             tm.calibrate)
                font = rsc.fonts.debugfont
                color = (255, 255, 255)
                rate_img = font.render(rate_txt, True, color)
                draw_times_img = font.render(draw_txt, True, color)
                update_times_img = font.render(update_txt, True, color)

            # wait for the next scheduler event
            tm.calibrate.start()
            sch_event = self._timekeeper.wait_for_event()
            tm.calibrate.end()

            if sch_event == "update":
              ## update
              tm.update.start()
              # actors moving
              tm.update_actors.start()
              if not self._timekeeper.paused():
                for actor in self.get_actors(exclude = [actors.MagicParticle]):
                  actor.update()
              tm.update_actors.end()
  
              # magic moving
              tm.update_magic.start()
              if not self._timekeeper.paused():
                for actor in self.get_actors(include = [actors.MagicParticle]):
                  actor.update()
              tm.update_magic.end()
  
              # storyline evolving
              story.update()
              # camera movements
              self.camera.update()
  
              # update fields
              tm.update_fields.start()
              for fieldtype in self.fields.keys():
                self.fields[fieldtype].update()
              tm.update_fields.end()
              tm.update.end()
              ct.update.count()

            elif sch_event == "draw":
              ## draw
              tm.draw.start()
              self.graphics.clear()
  
              total_actor_count = total_magic_count = draw_actor_count = draw_magic_count = 0
              # background changes slightly in color
              if self._timekeeper.paused():
                day = -1.0
                self.graphics.fill([16, 32, 96])
              else:
                day = math.sin(time.time()) + 1
                self.graphics.fill([day * 32, 32 + day * 32, 128 + day * 32])
  
              # draw actors
              draw_debug = c_game.draw_debug
              self.sort_actors()
  
              tm.draw_actors.start()
              for actor in self.get_actors(exclude = [actors.MagicParticle]):
                total_actor_count += 1
                if actor.draw(draw_debug):
                  draw_actor_count += 1
              tm.draw_actors.end()
  
              # magic particles
              tm.draw_magic.start()
              for actor in self.get_actors(include = [actors.MagicParticle]):
                total_magic_count += 1
                if actor.draw(draw_debug):
                  draw_magic_count += 1
              tm.draw_magic.end()
  
              # draw fields
              tm.draw_fields.start()
              for field in self.all_fields():
                field.draw(self.camera, draw_debug = draw_debug)
              tm.draw_fields.end()
  
              # draw storyline elements
              story.draw(draw_debug = draw_debug)
  
              # draw performance stats
              if draw_debug and rate_img and draw_times_img and update_times_img:
                self.graphics.fill((0,0,0), (10, 10, rate_img.get_width(), rate_img.get_height()))
                self.graphics.fill((0,0,0), (10, 30, draw_times_img.get_width(), draw_times_img.get_height()))
                self.graphics.fill((0,0,0), (10, 50, update_times_img.get_width(), update_times_img.get_height()))
                self.graphics.blit(rate_img, (10, 10))
                self.graphics.blit(draw_times_img, (10, 30))
                self.graphics.blit(update_times_img, (10, 50))

              # draw ball selector
              if c_char is not None and c_char.get_magic:
                i = 1
                for ball in c_char.local_balls:
                  ball_txt = rsc.fonts.textfont.render("%u: %s" % (i, ball.__class__.__name__), True, ball.field.color)
                  ball_nr  = rsc.fonts.textfont.render("%u" % (i), True, ball.field.color)
                  self.graphics.blit(ball_txt, (10, 40 + i * 20))
                  self.graphics.blit(ball_nr, (self.camera.pl2sc_x(ball.pos), self.camera.sc_h() - 80))
                  i += 1

              self.graphics.update()
              tm.draw.end()
              ct.fps.count()

            elif sch_event == "input":
              ## handle events
              tm.events.start()
              for event in pygame.event.get():
                if event.type == QUIT or event.type == KEYDOWN and event.key == K_ESCAPE:
                  return
                c_game.handle(event)
                if c_char is not None:
                  c_char.handle(event)
              tm.events.end()
              ct.input.count()

      ## actor management
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
