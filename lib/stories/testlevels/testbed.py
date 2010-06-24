from lib.stories import Story
from lib import actors

class TestBed(Story):
      menuname = "Testbed"

      def __init__(self, *args):
          Story.__init__(self, *args)

          self.default_scenery()
          world = self.world
          world.new_actor(actors.BehavingDragon, 125.0)
          self.dude = world.new_actor(actors.Dude, 25.0)
      def player(self):
          return self.dude
