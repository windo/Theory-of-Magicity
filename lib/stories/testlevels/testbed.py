from lib.stories import Story, storybook
from lib import actors

class TestBed(Story):
      storybook_path = "demos"
      def __init__(self, *args):
          Story.__init__(self, *args)

          world = self.world
          for i in xrange(2):
            d = world.new_actor(actors.BehavingDragon, 75.0)
          for i in xrange(1):
            d = world.new_actor(actors.BehavingVillager, 125.0)
            #d.controller.set_waypoint(-100.0)
          self.dude = world.new_actor(actors.Dude, 125.0)
          world.camera.follow(self.dude)

      def get_player(self):
          return self.dude
      def update(self):
          pass
storybook.add(TestBed)
