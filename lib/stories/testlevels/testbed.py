from lib.stories import Story, storybook
from lib import actors

class TestBed(Story):
      storybook_path = "demos"
      def __init__(self, *args):
          Story.__init__(self, *args)

          world = self.world
          for i in xrange(2):
            d = world.new_actor(actors.BehavingDragon, 75.0)
            d = world.new_actor(actors.BehavingVillager, 100.0)
            #d.controller.set_waypoint(-100.0)
          self.dude = world.new_actor(actors.Dude, 500.0)
          world.camera.follow(d)

      def get_player(self):
          return None
      def update(self):
          pass
storybook.add(TestBed)

class KillTest(Story):
      storybook_path = "tests"
      def __init__(self, *args):
          Story.__init__(self, *args)
          self.subj = self.world.new_actor(actors.BehavingVillager, 100.0)
          self.prey = self.world.new_actor(actors.Dragon, 50.0)
          self.world.camera.follow(self.subj)

      def get_player(self):
          return None
      def update(self):
          story_time, state_time = self.times()
          if not self.game_over:
            if self.prey.dead:
              self.set_state("prey-killed")
              self.set_result(True)
              self.exit_now = True
            elif story_time > 30.0:
              self.set_state("prey-survived")
              self.set_result(False)
              self.exit_now = True
storybook.add(KillTest)
