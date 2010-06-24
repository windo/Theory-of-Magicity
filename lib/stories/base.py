from lib import fields, actors
from random import random

class Story:
      menuname  = "Blank Story Name"
      themesong = "happytheme"

      def __init__(self, world):
          self.world = world
          # story state
          self.game_over   = False
          self.game_result = None
          self.set_state("begin")
          self.story_time  = self.world.get_time()
          self.last_narrative = 0
          # stories need narrations
          self.narrations  = []
          self.queue       = []

      def gen_menuitem(klass):
          return { "action": klass, "txt": klass.menuname }
      gen_menuitem = classmethod(gen_menuitem)

      def default_scenery(self):
          """
          Reused a lot of times
          """
          world = self.world
          world.new_actor(actors.BackgroundHills, 0)
          world.new_actor(actors.ForegroundGrass, 0)
          world.new_actor(actors.ForegroundOldGrass, 0)
          # paint some scenery
          for i in xrange(10):
            world.new_actor(actors.Tree, -250 + (500 / 10) * i + random() * 25)
          for i in xrange(3):
            world.new_actor(actors.Sun, -1200 + (2500 / 3) * i)
          for i in xrange(6):
            world.new_actor(actors.Cloud, -1200 + (2500 / 6) * i)

          # some ambient lifeforms
          for i in xrange(25):
            bird = world.new_actor(actors.FlockingBird, random() * 1000 - 500)
            bird.ypos = random() * bird.controller.ypos_upper_bound
          for i in xrange(2):
            bird = world.new_actor(actors.PredatorBird, random() * 1000 - 500)
            bird.ypos = random() * 10.0

          # set music
          world.loader.set_music(self.themesong)

      # all narrations done!
      def narrated(self, delay = 5.0):
          return len(self.narrations) == 0 and self.last_narrative + delay < self.world.get_time()
      def narrate(self, text, showtime = 0.0, duration = 5.0, id = False):
          if not id: id = text
          # make sure this id is unique
          if id in self.queue:
            return
          else:
            self.queue.append(id)
          now = self.world.get_time()
          # render
          img = self.world.loader.textfont.render(text, True, (255, 255, 255))
          # add to narrations list
          self.narrations.append({ "showtime": now + showtime,
                                   "cleartime": now + showtime + duration,
                                   "img": img,
                                   "id": id,
                                 })

      def batch_narrate(self, narrations, id = "narrative"):
          """
          proccess a tuple of tuples containing narrations
          """
          if not id in self.queue:
            showtime = 0
            for narr in narrations:
              showtime += narr[0]
              narr = (narr[1], showtime) + narr[2:]
              self.narrate(*narr)
            self.queue.append(id)
          else:
            pass
      def clear_queue(self, id):
          if id in self.queue:
            self.queue.pop(self.queue.index(id))

      def set_state(self, state):
          self.state      = state
          self.state_time = self.world.get_time()
          self.action_times = {}
          self.narrations = []
          self.queue      = []
      def set_result(self, result):
          self.game_over     = True
          self.game_result   = result
          if result:
            self.game_over_img = self.world.loader.smallgoth.render("You Win!", True, (0, 0, 64))
          else:
            self.game_over_img = self.world.loader.smallgoth.render("Game Over!", True, (0, 0, 64))
      def time_passed(self, delay, action = "wait"):
          if not self.action_times.has_key(action):
            self.action_times[action] = self.world.get_time()
            return True
          else:
            if self.action_times[action] + delay < self.world.get_time():
              self.action_times[action] = self.world.get_time()
              return True
          return False
      
      def times(self):
          now = self.world.get_time()
          return now - self.story_time, now - self.state_time

      # must overload this
      def update(self):
          pass

      def draw(self, draw_debug = False):
          view = self.world.view
          # draw game over
          if self.game_over:
            view.blit(self.game_over_img,
                      (self.world.view.sc_w() / 2 - self.game_over_img.get_width() / 2,
                       self.world.view.sc_h() / 2 - self.game_over_img.get_height() / 2 - 100))

          # proccess narratives
          draw_list    = []
          extra_offset = 0
          i            = 0
          now = self.world.get_time()
          while i < len(self.narrations):
            narr = self.narrations[i]
            showtime  = narr["showtime"]
            cleartime = narr["cleartime"]
            if showtime < now:
              if cleartime < now:
                if cleartime + 1.0 < now:
                  if narr["id"]:
                    self.queue.pop(self.queue.index(narr["id"]))
                  self.narrations.pop(i)
                else:
                  part = (cleartime + 1.0 - now)
                  extra_offset += int(part * (narr["img"].get_height() + 5))
                  i += 1
              else:
                draw_list.append(narr["img"])
                i += 1
            else:
              i += 1

          if draw_list:
            self.last_narrative = self.world.get_time()

          # draw them
          line_y = 10 + extra_offset
          for img in draw_list:
            view.blit(img, (10, line_y))
            line_y += img.get_height() + 5
