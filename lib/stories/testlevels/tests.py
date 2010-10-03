from lib.stories import Story, storybook
from lib import actors

class TestBase(Story):
      storybook_path = "tests"
      def get_player(self):
          return None

class Kill(TestBase):
      enemies = 1
      max_time = 30.0
      def __init__(self, *args):
          Story.__init__(self, *args)
          self.subj = self.world.new_actor(actors.BehavingVillager, 100.0)
          self.prey = []
          for i in xrange(self.enemies):
            d = self.world.new_actor(actors.Dragon, 25.0 + i * 50.0 / self.enemies)
            self.prey.append(d)
          self.world.camera.follow(self.subj)

      def update(self):
          story_time, state_time = self.times()
          if not self.game_over:
            alldead = True
            for p in self.prey:
              if not p.dead:
                alldead = False
                break
            if alldead:
              self.set_state("prey-killed")
              self.set_result(True, exit_now = True)
            elif story_time > self.max_time:
              self.set_state("prey-survived")
              self.set_result(False, exit_now = True)
storybook.add(Kill)

class TripleKill(Kill):
      enemies = 3
      max_time = 60.0
storybook.add(TripleKill)

class MultiKill(Kill):
      enemies = 10
      max_time = 120.0
storybook.add(MultiKill)

class Evasion(TestBase):
      enemies = 1
      max_time = 60.0
      def __init__(self, *args):
          Story.__init__(self, *args)
          self.subj = self.world.new_actor(actors.BehavingVillager, 100.0)
          self.prey = []
          for i in xrange(self.enemies):
            d = self.world.new_actor(actors.HuntingDragon, 25.0 + i * 50.0 / self.enemies)
            self.prey.append(d)
          self.world.camera.follow(self.subj)

      def update(self):
          story_time, state_time = self.times()
          if not self.game_over:
            # invincible dragons
            for p in self.prey:
              p.hp = p.initial_hp
            if self.subj.dead:
              self.set_state("got-killed")
              self.set_result(False, exit_now = True)
            elif story_time > self.max_time:
              self.set_state("survived")
              self.set_result(True, exit_now = True)
storybook.add(Evasion)

class DualEvasion(Evasion):
      enemies = 2
storybook.add(DualEvasion)

class TripleEvasion(Evasion):
      enemies = 3
storybook.add(TripleEvasion)
