from lib import actors
from lib.stories import Story, storybook
from random import random

class Shepherd(Story):
      story_title = "Gentle Shepherd"
      storybook_path = "campaign"
      def __init__(self, *args):
          Story.__init__(self, *args)

          self.default_scenery()
          world = self.world

          # paint the destination
          world.new_actor(actors.Post, 50)
          world.new_actor(actors.Post, 100)

          # add some rabbits to guide
          self.totalrabbits = 15
          for i in xrange(self.totalrabbits):
            rabbit = world.new_actor(actors.ScaredRabbit, -25.0 + 50 * random())
            rabbit.controller.set_waypoint(0.0)

          # player-controlled object
          self.dude = world.new_actor(actors.Dude, 75.0)

          world.camera.goto(-50.0)
          world.camera.follow(self.dude, pan = True)

      def get_player(self):
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
              (4.0,  "This is awful, I ruined everything..."),
              ))

          elif self.state == "dudedeath":
            self.batch_narrate((
              (0.0,  "Ah..."),
              (2.0,  "I managed to kill myself!"),
              (4.0,  "This is not good at all, who will take care of the rabbits now?"),
              ))

          elif self.state == "rabbitshome":
            self.batch_narrate((
              (0.0,  "Finally!"),
              (2.0,  "All my rabbits are back home!"),
              (4.0,  "Now I must look out. Hopefully those rumours about dragons are not true..."),
              ))

          elif self.state == "begin":
            self.batch_narrate((
              (4.0, "My rabbits have gone wandering!"),
              (4.0, "They are supposed to stay between these two posts."),
              (4.0, "Evidently, they prefer to eat over there..."),
              (2.0, "Well, we'll see about that!"),
              (2.0, "I've got some tricks up my sleeve..."),
              (2.0, "Wind magic is going to help me out!"),
              (2.0, "Now, how did that work exactly..."),
              (2.0, "Right!"),
              (5.0, "I should cast a Wind Magic Ball [press 'x'].", 10.0),
              ))

            ballcast = False
            for particle in self.dude.magic.affects.keys():
              if isinstance(particle, actors.WindBall):
                ballcast = True
                break
            if ballcast:
              self.set_state("particle_control")

            if self.narrated() and self.time_passed(15) and not ballcast:
              self.narrate("I need to cast a Wind Magic Ball [press 'x'].", duration = 10.0)

          elif self.state == "particle_control":
            self.batch_narrate((
              (0.0, "A Magic Ball! It worked!"),
              (2.0, "Of course - I have to be cautious now..."),
              (4.0, "This is magic after all, it can be dangerous too."),
              (4.0, "If me or my rabbits are exposed to this field for too long, we may even die!", 10.0),
              (5.0, "But I'll be careful."),
              (2.0, "I'm sure I can handle it."),
              (3.0, "Should try it on myself first though."),
              (5.0, "Just have to move this ball a bit closer to myself ['a' and 'd' keys]."),
              ))

            for particle in self.dude.magic.affects.keys():
              if isinstance(particle, actors.WindBall):
                if abs(particle.pos - self.dude.pos) < 1.0:
                  self.set_state("particle_power")
                  break

            if self.narrated() and self.time_passed(15):
              self.narrate("I need to get this ball closer to myself ['a' and 'd' keys].", duration = 10.0)

          elif self.state == "particle_power":
            self.batch_narrate((
              (0.0, "Haha, this feels like the wind is blowing!"),
              (3.0, "Quite strong wind."),
              (4.0, "OK, since the magic field is positive, the wind blows right..."),
              (3.0, "And if I make it even more positive ['w' key], it will blow stronger.", 15.0),
              (5.0, "However, I wonder if I can change it's direction...", 6.0),
              (5.0, "Should happen if I make the field negative ['s' key]!", 10.0),
              ))

            ballcast = False
            close    = False
            negative = False
            for particle in self.dude.magic.affects.keys():
              if isinstance(particle, actors.WindBall):
                ballcast = True
                if abs(particle.pos - self.dude.pos) < 1.0:
                  close = True
                if self.dude.magic.affects[particle][1] < 0.0:
                  negative = True
            if ballcast and close and negative:
              self.set_state("find_rabbits")
            
            if self.narrated() and self.time_passed(15):
              if not ballcast:
                self.narrate("I need to have a Wind Magic Ball [press 'x'].", duration = 10.0)
              if not negative:
                self.narrate("The Wind Magic Ball needs to have a negative energy ['s' key].", duration = 10.0)
              if not close:
                self.narrate("The Wind Magic Ball needs to be close to me ['a' and 'd' keys].", duration = 10.0)

          elif self.state == "find_rabbits":
            self.batch_narrate((
              (0.0, "Wonderful, I can make the wind blow in both directions."),
              (4.0, "This will be quite useful to guide those disobedient rabbits!"),
              (6.0, "Now, I wonder how far they have wandered..."),
              (4.0, "I should go and find the last rabbit [left and right arrows]."),
              ))

            leftmost_rabbit = 100.0
            for rabbit in self.world.get_actors(include = [actors.Rabbit]):
              if rabbit.pos < leftmost_rabbit:
                leftmost_rabbit = rabbit.pos
            if self.dude.pos < leftmost_rabbit:
              self.set_state("gather_rabbits")

            if self.narrated() and self.time_passed(15):
              self.narrate("I should move left [left arrow] to find the last rabbit.", duration = 10.0)

          elif self.state == "gather_rabbits":
            self.batch_narrate((
              (0.0, "...13, 14, 15!"),
              (2.0, "That's the last one!"),
              (6.0, "So, if I can make a Wind Magic Ball [press 'x']..."),
              (2.0, "I can change the speed and direction of the wind ['w' and 's' keys]..."),
              (2.0, "And move it close to my rabbits ['a' and 'd' keys]..."),
              (3.0, "I should have them gathered between the posts in no time!"),
              (5.0, "Of course, I must be careful not to hurt them."),
              ))

            if self.narrated() and self.time_passed(30):
              self.narrate("I should use a Wind Magic Ball [press 'x']...", duration = 10.0)
              self.narrate("...change it's wind direction ['w' and 's' keys]...", duration = 10.0)
              self.narrate("...and move it close to rabbits ['a' and 'd' keys]...", duration = 10.0)
              self.narrate("...to guide them between the posts [to the right].", duration = 10.0)
storybook.add(Shepherd)

class Massacre(Story):
      story_title  = "Fiery Massacre"
      storybook_path = "campaign"
      themesong = "warmarch2"
      def __init__(self, *args):
          Story.__init__(self, *args)

          world = self.world
          self.default_scenery()

          # paint the destination
          world.new_actor(actors.Post, 0.0)
          world.new_actor(actors.Post, 50.0)

          # enemies
          world.new_actor(actors.HuntingDragon, 75)
          world.new_actor(actors.HuntingDragon, 80)
          for dragon in world.get_actors(include = [actors.Dragon]):
            dragon.controller.set_waypoint(75.0)

          # sweet rabbits to protect
          for i in xrange(25):
            rabbit = world.new_actor(actors.ScaredRabbit, 0 + 100 * random())
            rabbit.controller.set_waypoint(50.0)

          # player-controlled object
          self.dude = world.new_actor(actors.Dude, 10)

          world.camera.goto(150.0)
          world.camera.follow(self.dude, pan = True)

      def get_player(self):
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
              (4.0, "However, the are probably more on their way, I must go and get help..."),
              ))

          # lose :(
          elif self.state == "dudedeath":
            self.batch_narrate((
              (0.0, "Ah..."),
              (2.0, "I've been vanquished."),
              (4.0, "This is terrbile, who will protect the rabbits now?"),
              ))

          elif self.state == "rabbitdeath":
            self.batch_narrate((
              (0.0,  "Whoops!"),
              (2.0,  "All the rabbits have been killed!"),
              (4.0,  "What a cold and sad world it is now. So sad..."),
              ))

          # intro
          elif self.state == "begin":
            self.batch_narrate((
              (2.0, "My rabbits are being slaughtered by the dragons!"),
              (3.0, "I have to protect them!"),
              (3.0, "But first, I must get away from the dragons [left and right arrow]."),
              ))
            if self.narrated() and self.time_passed(15):
              self.narrate("Move left, away from the dragons [left arrow].", duration = 10.0)
            if self.dude.pos < -50.0:
              self.set_state("lifemagic")

          elif self.state == "lifemagic":
            self.batch_narrate((
              (0.0, "This is far enough, should be safe."),
              (6.0, "Those dragons can be pretty dangerous."),
              (2.0, "They were using Life Magic to kill my poor rabbits."),
              (2.0, "To fight them, I must also use Life Magic."),
              (4.0, "I should cast an Life Magic Ball [press 'c']."),
              ))

            ballcast = False
            for particle in self.dude.magic.affects.keys():
              if isinstance(particle, actors.LifeBall):
                ballcast = True
            if ballcast:
              self.set_state("particle_control")
            if self.narrated() and self.time_passed(15):
              if ballcast:
                self.narrate("Good, you have cast a Life Magic Ball for practice.")
              else:
                self.narrate("And also cast a Life Magic Ball [press 'c'].", duration = 10.0)

          elif self.state == "particle_control":
            self.batch_narrate((
              (0.0, "Very good!"),
              (4.0, "The relationship between the field and the ball can be seen now."),
              (4.0, "I can move the magic ball ['a' and 'd' keys].", 10.0),
              (4.0, "And I can set it's power ['w' and 's' keys].", 10.0),
              (4.0, "And when I'm done with a ball, I can release it ['r' key].", 10.0),
              ))

            if self.narrated() and self.time_passed(30):
              self.batch_narrate((
                (0.0, "Try to make a Life magic ball [press 'c'].", 15.0),
                (5.0, "Make it's power negative ['s' key].", 15.0),
                (5.0, "And move it close to yourself ['a' and 'd' keys].", 15.0)
                ), "instructions")
              self.clear_queue("instructions")

            # check for the healing ball
            for particle in self.dude.magic.affects.keys():
              if isinstance(particle, actors.LifeBall):
                if self.dude.magic.affects[particle][1] < 0.0:
                  if abs(particle.pos - self.dude.pos) < 1.0:
                    self.set_state("healing_explanation")

          elif self.state == "healing_explanation":
            self.batch_narrate((
              (0.0, "Well done!"),
              (2.0, "Negative Life magic has a restoring effect on health."),
              (4.0, "It's the opposite of the damaging magic balls the dragons were using."),
              (4.0, "Two such opposite balls will even cancel each other out!"),
              (4.0, "I think I'm about ready to fight the dragons now."),
              (2.0, "Let's get a bit closer."),
              ))

            if self.narrated() and self.time_passed(15):
              self.narrate("Move right, closer to the dragons [right arrow].")
            
            close = False
            for dragon in self.world.get_actors(include = [actors.Dragon]):
              if abs(dragon.pos - self.dude.pos) < 75.0:
                self.set_state("capture_ball")
              
          elif self.state == "capture_ball":
            self.batch_narrate((
              (0.0, "Wait!"),
              (2.0, "A few last words of before we fight..."),
              (4.0, "Aside from making the magic balls myself, I can also capture them."),
              (4.0, "For example those, that the dragons throw at me [hold ctrl, press 'd'].", 10.0),
              (5.0, "But it works on all magic balls [hold ctrl, press 'a' or 'd' key or a number].", 10.0),
              (5.0, "Try to catch one of the dragons' magic balls!"),
              ))

            for particle in self.dude.magic.affects.keys():
              for caster in particle.affects:
                if isinstance(caster.actor, actors.Dragon):
                  self.set_state("fight")

          elif self.state == "fight":
            self.batch_narrate((
              (0.0, "Great!"),
              (2.0, "We caught a ball!"),
              (2.0, "Now use it to slay the dragon!"),
              ))

            if self.narrated() and state_time % 15 < 1.0:
              rabbits = len(self.world.get_actors(include = [ actors.Rabbit ]))
              self.narrate("Slay the dragons! There are still %u rabbits left to save!" % (rabbits))
storybook.add(Massacre)

class Blockade(Story):
      story_title  = "Guardian Blockade"
      storybook_path = "campaign"
      themesong = "warmarch2"
      def __init__(self, *args):
          Story.__init__(self, *args)

          world = self.world
          self.default_scenery()

          # enemies
          for i in xrange(2):
            guardian = world.new_actor(actors.ControlledGuardian, 50 + i * 50)
            guardian.controller.danger.append(actors.Dude)

          # player-controlled object
          self.dude = world.new_actor(actors.Dude, 0)

          world.camera.goto(100)
          world.camera.follow(self.dude, pan = True)

      def get_player(self):
          return self.dude

      def update(self):
          story_time, state_time = self.times()
          
          if not self.game_over:
            # see if we are past both the guardians
            past = True
            guardians = self.world.get_actors(include = [ actors.Guardian ])
            for guard in guardians:
              if guard.pos > self.dude.pos - 25.0:
                past = False
            if past:
               self.set_state("passed")
               self.set_result(True)
            elif self.dude.dead:
               self.set_state("dudedead")
               self.set_result(False)

          if self.state == "passed":
            self.batch_narrate((
              (0.0, "Aha!"),
              (2.0, "The guardians can be passed after all!"),
              (4.0, "Well done, I can now continue on to the village."),
              ))

          elif self.state == "dudedead":
            self.batch_narrate((
              (0.0, "Ah..."),
              (2.0, "Defeated by the dragons, what a sad fate."),
              ))

          elif self.state == "begin":
            self.batch_narrate((
               (2.0, "I've been fleeing hordes of dragons for several days now."),
               (4.0, "And now these guardians are blocking my path!"),
               (4.0, "If I can't get through, I'm toast!"),
               (2.0, "Literally!"),
               (5.0, "Seems as if they're using Time Magic to block me [press 'z']."),
               (5.0, "Oh no, the dragons are here!"),
               ))
            if self.narrated(0):
              self.set_state("onslaught")

          if self.state == "onslaught":
            if self.time_passed(60):
              dragons = len(self.world.get_actors(include = [actors.Dragon]))
              if dragons < 2:
                dragon = self.world.new_actor(actors.HuntingDragon, self.dude.pos - 75 + random() * 10)
                dragon.controller.set_waypoint(200.0)
storybook.add(Blockade)

class Siege(Story):
      story_title  = "Under Siege"
      storybook_path = "campaign"
      themesong = "warmarch2"
      def __init__(self, *args):
          Story.__init__(self, *args)

          world = self.world
          self.default_scenery()

          # enemies
          for i in xrange(5):
            dragon = world.new_actor(actors.HuntingDragon, random() * 75.0)
            dragon.controller.set_waypoint(50)

          # friends
          self.guardpost = []
          for i in xrange(4):
            villager = world.new_actor(actors.HuntingVillager,  150 - random() * 75.0)
            villager.controller.set_waypoint(50)
            self.guardpost.append(villager)

          # the guardmaster
          world.new_actor(actors.Hut, 300)
          self.guardmaster = world.new_actor(actors.Villager, 310)
          self.guardians = []
          for i in xrange(2):
            guardian = world.new_actor(actors.ControlledGuardian, 315 + i * 5)
            guardian.controller.danger = [actors.Dragon]
            self.guardians.append(guardian)

          # player-controlled object
          self.dude = world.new_actor(actors.Dude, -50)

          world.camera.goto(200.0)
          world.camera.follow(self.dude, pan = True)

      def get_player(self):
          return self.dude

      def update(self):
          story_time, state_time = self.times()

          if not self.game_over:
            villagers = len(self.guardpost) - sum([guard.dead and 1 or 0 for guard in self.guardpost])
            dragons   = len(self.world.get_actors(include = [actors.Dragon]))
            if villagers == 0:
              self.set_state("guardpost-lost")
              self.set_result(False)
            elif self.dude.dead:
              self.set_state("dude-death")
              self.set_result(False)
            elif story_time > 120.0 and self.time_passed(30.0, "respawn") and dragons < 5:
              pos = min(self.dude.pos - 75, -50) - random() * 25
              dragon = self.world.new_actor(actors.HuntingDragon, pos)
              dragon.controller.set_waypoint(50)

          if self.state == "guardpost-lost":
            self.batch_narrate((
              (0.0, "All the villagers at the guardpost have been killed!"),
              (2.0, "This is terrible."),
              (4.0, "Damn you, dragons!"),
              ))

          elif self.state == "dude-death":
            self.batch_narrate((
              (0.0, "Goodbye, cruel world!"),
              (2.0, "The dragons have turned me into a heap of ashes..."),
              (4.0, "The wind shall blow me away."),
              ))

          elif self.state == "guardpost-secured":
            self.batch_narrate((
              (0.0, "The guardians got to the guardpost!"),
              (2.0, "The village has been secured!"),
              (4.0, "For now, at least..."),
              ))
            
          elif self.state == "begin":
            self.batch_narrate((
              (2.0, "The villagers are under attack!"),
              (2.0, "They are outnumbered, I must help them!"),
              ))

            dragons = self.world.get_actors(include = [actors.Dragon])
            if len(dragons) == 0:
              self.set_state("get-help")

            if self.narrated() and self.time_passed(15):
              self.narrate("Slay the dragons!")

          elif self.state == "get-help":
            self.batch_narrate((
              (0.0, "The dragons are defeated!"),
              (2.0, "Villager: More dragons are sure to come!"),
              (4.0, "Villager: You, stranger, run to the village and get help - as fast as you can!"),
              (4.0, "Villager: Use positive Time Magic [press 'z'] for extra speed!"),
              (2.0, "Villager: We'll hold the dragons back!"),
              ))

            if self.narrated() and self.time_passed(15):
              self.narrate("I must run to the village [right] to get help.")
              self.narrate("Time magic [press 'z'] ball will increase my speed.", showtime = 2.0, duration = 10.0)

            if self.dude.pos > 290:
              self.set_state("village")
              for i in xrange(len(self.guardians)):
                self.guardians[i].controller.set_waypoint(25.0 - i * 5)

          elif self.state == "village":
            self.batch_narrate((
              (0.0, "The dragons are attacking!"),
              (2.0, "Villager: Damn!"),
              (2.0, "Villager: I'll send out these guardians to block their path."),
              (4.0, "Villager: You go and help keep the guardpost until we have it locked down!"),
              ))
            if self.narrated() and self.time_passed(15):
              self.narrate("I must run back to the guardpost [left] really fast.")

            if self.dude.pos < 100.0:
              self.set_state("block")

          elif self.state == "block":
            self.batch_narrate((
              (0.0, "The guardians are coming."),
              (2.0, "Villager: Great!"),
              (4.0, "Villager: Just have to keep extinguishing these dragons until they get here!"),
              ))

            if self.narrated() and self.time_passed(30):
              self.narrate("Help hold the guardpost until the guardians get here.")

            if sum([guardian.controller.waypoint and 1 or 0 for guardian in self.guardians]) == 0:
              self.set_result(True)
              self.set_state("guardpost-secured")
storybook.add(Siege)
