import fields, actors
import pygame
from random import random

class Story:
      def __init__(self, world):
          self.world = world
          # story state
          self.state       = "begin"
          self.game_over   = False
          self.game_result = None
          self.state_time  = self.world.get_time()
          self.story_time  = self.world.get_time()
          # stories need narrations
          self.narrations  = []
          self.queue       = []

      def narrate(self, text, showtime = 0.0, duration = 5.0, id = False):
          if id:
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
            for narr in narrations:
              narr = (narr[1], narr[0]) + narr[2:]
              self.narrate(*narr)
            self.queue.append(id)
          else:
            pass
      def clear_queue(self, id):
          if id in self.queue:
            self.queue.pop(self.queue.index(id))

      def set_state(self, state):
          self.state      = state
          self.narrations = []
          self.queue      = []
          self.state_time = self.world.get_time()
      def set_result(self, result):
          self.game_over     = True
          self.game_result   = result
          if result:
            self.game_over_img = self.world.loader.smallgoth.render("You Win!", True, (0, 0, 64))
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

          # draw them
          line_y = 10 + extra_offset
          for img in draw_list:
            screen.blit(img, (10, line_y))
            line_y += img.get_height() + 5

class Shepherd(Story):
      def __init__(self, *args):
          Story.__init__(self, *args)

          world = self.world
          # paint some scenery
          for i in xrange(10):
            world.new_actor(actors.Tree, -250 + (500 / 10) * i + random() * 25)
          for i in xrange(3):
            world.new_actor(actors.Sun, -250 + (500 / 3) * i + random() * 25)

          # paint the destination
          world.new_actor(actors.Post, 50)
          world.new_actor(actors.Post, 100)

          # add some rabbits to guide
          self.totalrabbits = 15
          for i in xrange(self.totalrabbits):
            rabbit = world.new_actor(actors.ControlledRabbit, -25.0 + 50 * random())
            rabbit.controller.set_waypoint(10.0)

          # player-controlled object
          self.dude = world.new_actor(actors.Dude, 75.0)

          world.view.set_x(-100.0)

      def player(self):
          return self.dude

      def update(self):
          story_time, state_time = self.times()

          if not self.game_over:
            rabbits = self.world.get_actors(include = [actors.Rabbit])
            in_area = 0
            for rabbit in rabbits:
              if 50.0 < rabbit.pos < 100.0:
                in_area += 1
                rabbit.controller.set_waypoint(75.0)

            if self.dude.dead:
              self.set_state("dudedeath")
              self.set_result(False)
            if len(rabbits) < self.totalrabbits:
              self.set_state("rabbitdead")
              self.set_result(False)
            if in_area == self.totalrabbits:
              self.set_state("rabbitshome")
              self.set_result(True)

          if self.state == "rabbitdead":
            self.batch_narrate((
              (0.0,  "Whoops!"),
              (2.0,  "Seems like I killed one of my rabbits by accident!"),
              (6.0,  "This is awful, I ruined everything..."),
              ))

          elif self.state == "dudedeath":
            self.batch_narrate((
              (0.0,  "Ah..."),
              (2.0,  "I managed to kill myself!"),
              (6.0,  "This is not good at all, who will take care of the rabbits now?"),
              ))

          elif self.state == "rabbitshome":
            self.batch_narrate((
              (0.0,  "Finally!"),
              (2.0,  "All my rabbits are back home!"),
              (6.0,  "Now I must look out. Hopefully those rumours about dragons are not true..."),
              ))

          elif self.state == "begin":
            self.batch_narrate((
              (0.0,  "My rabbits have gone wandering!"),
              (4.0,  "They are supposed to stay between these two posts."),
              (8.0,  "Evidently, they prefer to eat over there..."),
              (10.0, "Well, we'll see about that!"),
              (12.0, "I've got some tricks up my sleeve..."),
              (14.0, "Energy magic is going to help me out!"),
              ))
            if state_time > 20:
              self.set_state("learn_energy")

          elif self.state == "learn_energy":
            self.batch_narrate((
              (0.0,  "Now, how did that work exactly..."),
              (2.0,  "Right!"),
              (5.0,  "First we need to look at the Energy Magic Field [press 'x'].", 15.0),
              (10.0, "And then cast an Energy Magic Ball [hold shift, press 'X'].", 10.0),
              ))

            field_visible = self.world.get_field(fields.EnergyField).visibility
            ballcast      = False
            for particle in self.dude.magic.affects.keys():
              if isinstance(particle, fields.EnergyBall):
                ballcast = True
                break
            if field_visible and ballcast:
              self.set_state("particle_control")

            if state_time > 20 and state_time % 15.0 < 1:
              if not field_visible:
                self.narrate("I need to see the Energy Magic Field [press 'x'].", duration = 10.0, id = "field")
              if not ballcast:
                self.narrate("I need to cast an Energy Magic Ball [hold shift, press 'X'].", duration = 10.0, id = "ball")

          elif self.state == "particle_control":
            self.batch_narrate((
              (0.0,  "A Magic Ball! It worked!"),
              (2.0,  "Of course - I have to be cautious now..."),
              (6.0,  "This is magic after all, it can be dangerous too."),
              (10.0, "If me or my rabbits are exposed to this field for too long, we may even die!", 10.0),
              (15.0, "But I'll be careful."),
              (17.0, "I'm sure I can handle it."),
              (20.0, "Should try it on myself first though."),
              (25.0, "Just have to move this ball a bit closer to myself ['a' and 'd' keys]."),
              ))

            for particle in self.dude.magic.affects.keys():
              if isinstance(particle, fields.EnergyBall):
                if abs(particle.pos - self.dude.pos) < 1.0:
                  self.set_state("particle_power")
                  break

            if state_time > 30 and state_time % 15.0 < 1:
              self.narrate("I need to get this ball closer to myself ['a' and 'd' keys].", duration = 10.0, id = "closer")

          elif self.state == "particle_power":
            self.batch_narrate((
              (0.0,  "Haha, this feels like the wind is blowing!"),
              (3.0,  "Quite strong wind."),
              (7.0,  "OK, since the magic field is positive, the wind blows right..."),
              (10.0, "And if I make it even more positive ['w' key], it will blow stronger.", 15.0),
              (15.0, "However, I wonder if I can change it's direction...", 6.0),
              (20.0, "Should happen if I make the field negative ['s' key]!", 10.0),
              ))

            ballcast = False
            close    = False
            negative = False
            for particle in self.dude.magic.affects.keys():
              if isinstance(particle, fields.EnergyBall):
                ballcast = True
                if abs(particle.pos - self.dude.pos) < 1.0:
                  close = True
                if self.dude.magic.affects[particle][1] < 0.0:
                  negative = True
            if ballcast and close and negative:
              self.set_state("find_rabbits")
            
            if state_time > 20.0 and state_time % 15 < 1.0:
              if not ballcast:
                self.narrate("I need to have an Energy Magic Ball [hold shift, press 'X'].", duration = 10.0, id = "ball")
              if not negative:
                self.narrate("The Energy Magic Ball needs to have a negative energy ['s' key].", duration = 10.0, id = "energy")
              if not close:
                self.narrate("The Energy Magic Ball needs to be close to me ['a' and 'd' keys].", duration = 10.0, id = "close")

          elif self.state == "find_rabbits":
            self.batch_narrate((
              (0.0,  "Wonderful, I can make the wind blow in both directions."),
              (4.0,  "This will be quite useful to guide those disobedient rabbits!"),
              (10.0, "Now, I wonder how far they have wandered..."),
              (14.0, "I should go and find the last rabbit [left and right arrows]."),
              ))

            leftmost_rabbit = 100.0
            for rabbit in self.world.get_actors(include = [actors.Rabbit]):
              if rabbit.pos < leftmost_rabbit:
                leftmost_rabbit = rabbit.pos
            if self.dude.pos < leftmost_rabbit:
              self.set_state("gather_rabbits")

            if state_time > 20.0 and state_time % 15.0 < 1.0:
              self.narrate("I should move left [left arrow] to find the last rabbit.", duration = 10.0, id = "move")

          elif self.state == "gather_rabbits":
            self.batch_narrate((
              (0.0, "...13, 14, 15!"),
              (2.0, "That's the last one!"),
              (8.0, "So, if I can make an Energy Magic Ball [hold shift, press 'X']..."),
              (10.0, "I can change the speed and direction of the wind ['w' and 's' keys]..."),
              (12.0, "And move it close to my rabbits ['a' and 'd' keys]..."),
              (15.0, "I should have them gathered between the posts in no time!"),
              (20.0, "Of course, I must be careful not to hurt them."),
              ))

            if state_time > 30.0 and state_time % 30.0 < 1.0:
              self.narrate("I should use an Energy Magic Ball [hold shift, press 'X']...", duration = 10.0, id = "ball")
              self.narrate("...change it's wind direction ['w' and 's' keys]...", duration = 10.0, id = "power")
              self.narrate("...and move it close to rabbits ['a' and 'd' keys]...", duration = 10.0, id = "move")
              self.narrate("...to guide them between the posts [to the right].", duration = 10.0, id = "yard")

class Salvation(Story):
      def __init__(self, *args):
          Story.__init__(self, *args)

          world = self.world
          # paint some scenery
          for i in xrange(10):
            world.new_actor(actors.Tree, -250 + (500 / 10) * i + random() * 25)
          for i in xrange(3):
            world.new_actor(actors.Sun, -250 + (500 / 3) * i + random() * 25)

          # paint the destination
          world.new_actor(actors.Post, 0.0)
          world.new_actor(actors.Post, 50.0)

          # enemies
          world.new_actor(actors.ControlledDragon, 70)
          world.new_actor(actors.ControlledDragon, 75)
          world.new_actor(actors.ControlledDragon, 80)
          for dragon in world.get_actors(include = [actors.Dragon]):
            dragon.controller.set_waypoint(50.0)

          # sweet rabbits to protect
          for i in xrange(50):
            rabbit = world.new_actor(actors.ControlledRabbit, -50.0 + 200 * random())
            rabbit.controller.set_waypoint(25.0)

          # player-controlled object
          self.dude = world.new_actor(actors.Dude, 10)
          world.view.set_x(250.0)

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
            self.batch_narrate((
              (0.0, "Awesome!"),
              (2.0, "All the dragons are defeated!"),
              (6.0, "However, the are probably more on their way, I must go and get help..."),
              ))

          # lose :(
          elif self.state == "dudedeath":
            self.batch_narrate((
              (0.0,  "Ah..."),
              (2.0,  "I've been vanquished."),
              (6.0,  "This is terrbile, who will protect the rabbits now?"),
              ))

          elif self.state == "rabbitdeath":
            self.batch_narrate((
              (0.0,  "Whoops!"),
              (2.0,  "All the rabbits have been killed!"),
              (6.0,  "What a cold and sad world it is now. So sad..."),
              ))

          # intro
          elif self.state == "begin":
            self.batch_narrate((
              (2.0, "My rabbits are being slaughtered by the dragons!"),
              (5.0, "I have to protect them!"),
              (8.0, "But first, I must get away from the dragons [left and right arrow]."),
              ))
            self.set_state("capture_ball")
            if state_time > 10.0 and state_time % 15 < 1.0:
              self.narrate("Move left, away from the dragons [left arrow].", duration = 10.0, id = "move")
            if self.dude.pos < -25.0:
              self.set_state("earthmagic")

          elif self.state == "earthmagic":
            self.batch_narrate((
              (0.0,  "This is far enough, should be safe."),
              (6.0,  "Those dragons can be pretty dangerous."),
              (8.0,  "They were using Earth Magic to kill my poor rabbits."),
              (10.0, "To fight them, I must also use Earth Magic."),
              (14.0, "Take a look at the Earth Magic Field [press 'c']."),
              (14.0, "And cast an Earth Magic Ball [hold shift, press 'C']."),
              ))

            field_visible = self.world.get_field(fields.EarthField).visibility
            ballcast      = False
            for particle in self.dude.magic.affects.keys():
              if isinstance(particle, fields.EarthBall):
                ballcast = True
            if field_visible and ballcast:
              self.set_state("particle_control")
            if state_time > 20.0 and state_time % 15 < 1.0:
              if field_visible:
                self.narrate("Good, the effects of you Earth Magic Balls can be seen on the field.", id = "field")
              else:
                self.narrate("Take a look at the Earth Magic Field [press 'c'].", duration = 10.0, id = "field")
              if ballcast:
                self.narrate("Good, you have cast an Earth Magic Ball for practice.", id = "ball")
              else:
                self.narrate("And also cast an Earth Magic Ball [hold shift, press 'C'].", duration = 10.0, id = "ball")

          elif self.state == "particle_control":
            self.batch_narrate((
              (0.0,  "Very good!"),
              (4.0,  "The relationship between the field and the ball can be seen now."),
              (8.0,  "I can move the magic ball ['a' and 'd' keys].", 10.0),
              (12.0, "And I can set it's power ['w' and 's' keys].", 10.0),
              (16.0, "And when I'm done with a ball, I can release it ['r' key].", 10.0),
              ))

            if state_time > 20:
              if state_time % 15 < 1.0:
                self.batch_narrate((
                  (0.0,  "Try to make an Earth magic ball [hold shift, press 'C'].", 15.0),
                  (5.0,  "Make it's power negative ['s' key].", 15.0),
                  (10.0, "And move it close to yourself ['a' and 'd' keys].", 15.0)
                  ), "instructions")
              elif state_time % 15 < 2.0:
                self.clear_queue("instructions")

            # check for the healing ball
            for particle in self.dude.magic.affects.keys():
              if isinstance(particle, fields.EarthBall):
                if self.dude.magic.affects[particle][1] < 0.0:
                  if abs(particle.pos - self.dude.pos) < 1.0:
                    self.set_state("healing_explanation")

          elif self.state == "healing_explanation":
            self.batch_narrate((
              (0.0,  "Well done!"),
              (2.0,  "Negative Earth magic has a restoring effect on health."),
              (6.0,  "It's the opposite of the damaging magic balls the dragons were using."),
              (10.0, "Two such opposite balls will even cancel each other out!"),
              (14.0, "I think I'm about ready to fight the dragons now."),
              (16.0, "Let's get a bit closer."),
              ))

            if state_time > 20 and state_time % 15 < 1:
              self.narrate("Move right, closer to the dragons [right arrow].", id = "approach")
            
            close = False
            for dragon in self.world.get_actors(include = [actors.Dragon]):
              if abs(dragon.pos - self.dude.pos) < 50.0:
                self.set_state("capture_ball")
              
          elif self.state == "capture_ball":
            self.batch_narrate((
              (0.0,  "Wait!"),
              (2.0,  "A few last words of before we fight..."),
              (6.0,  "Aside from making the magic balls yourself, I can also capture them."),
              (10.0, "For example those, that the dragons throw at me [hold ctrl, press 'd'].", 10.0),
              (15.0, "But it works on all magic balls [hold ctrl, press 'a' or 'd' key or a number].", 10.0),
              (20.0, "Try to catch one of the dragons' magic balls!"),
              ))

            for particle in self.dude.magic.affects.keys():
              for caster in particle.affects:
                if isinstance(caster.actor, actors.Dragon):
                  self.set_state("fight")

          elif self.state == "fight":
            self.batch_narrate((
              (0.0, "Great!"),
              (2.0, "We caught a ball!"),
              (4.0, "Now use it to slay the dragon!"),
              ))

            if state_time > 15 and state_time % 15 < 1.0:
              rabbits = len(self.world.get_actors(include = [ actors.Rabbit ]))
              self.narrate("Slay the dragons! There are still %u rabbits left to save!" % (rabbits))

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
            self.batch_narrate((
              (0.0, "Aha!"),
              (2.0, "The guardians can be passed after all!"),
              (6.0, "Well done, I can now continue the journey."),
              ))

          elif self.state == "dudedead":
            self.batch_narrate((
              (0.0, "Ah..."),
              (2.0, "Defeated by the dragons, what a sad fate."),
              ))

          elif self.state == "begin":
            self.batch_narrate((
               (0.0, "I've been fleeing hordes of dragons for several days now."),
               (2.0, "But now these guardians are blocking my path!"),
               (5.0, "Seems that they are using Light Magic to do that [press 'z']."),
               (10.0, "They don't seem violent, but they do not seem to want to let me pass either."),
               (15.0, "I must find a way though - otherways the dragons are going to get me."),
               ))
            if state_time > 20:
              self.set_state("onslaught")

          if self.state == "onslaught":
            if state_time % 15.0 < 1.0:
              dragons = len(self.world.get_actors(include = [actors.Dragon]))
              for i in xrange(2 - dragons):
                dragon = self.world.new_actor(actors.ControlledDragon, self.dude.pos - 75 + random() * 10)
                dragon.controller.set_waypoint(200.0)
