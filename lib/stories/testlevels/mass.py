from lib.stories import Story
from lib import actors
from random import random

class MassBattle(Story):
      def __init__(self, *args):
          Story.__init__(self, *args)

          self.default_scenery()
          world = self.world
          for i in xrange(50):
            d = world.new_actor(self.dragon,   200.0 + random() * 400.0)
            v = world.new_actor(self.villager, 800.0 - random() * 400.0)
            d.controller.set_waypoint(800.0)
            v.controller.set_waypoint(200.0)
          self.dude = world.new_actor(actors.Dude, 25.0)
          world.view.goto(400.0)
      def player(self):
          return self.dude

class MassHunting(MassBattle):
      menuname = "Massive FSM Battle"
      dragon   = actors.HuntingDragon
      villager = actors.HuntingVillager
class MassBehaving(MassBattle):
      menuname = "Massive Planner Battle"
      dragon   = actors.BehavingDragon
      villager = actors.BehavingVillager
