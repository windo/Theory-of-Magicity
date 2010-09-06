from lib.stories import Story
from lib import actors

class TestBed(Story):
      menuname = "Testbed"

      def __init__(self, *args):
          Story.__init__(self, *args)

          self.default_scenery()
          world = self.world
          for i in xrange(2):
            d = world.new_actor(actors.BehavingDragon, 75.0)
            d = world.new_actor(actors.BehavingVillager, 100.0)
            #d.controller.set_waypoint(-100.0)
          self.dude = world.new_actor(actors.Dude, 500.0)
          world.view.follow(d)
      def player(self):
          return self.dude
