from lib.stories import Story, storybook
from lib import actors, effects
from random import random

class MassBattle(Story):
      storybook_path = "demos"
      def __init__(self, *args):
          Story.__init__(self, *args)

          self.default_scenery()
          world = self.world
          for i in xrange(50):
            d = world.new_actor(self.dragon,   200.0 + random() * 400.0)
            v = world.new_actor(self.villager, 800.0 - random() * 400.0)
            d.controller.set_waypoint(800.0)
            v.controller.set_waypoint(200.0)
          world.camera.goto(400.0)
          
      def get_player(self):
          return None
      def update(self):
          pass

class MassHunting(MassBattle):
      story_title = "Massive FSM Battle"
      dragon = actors.HuntingDragon
      villager = actors.HuntingVillager
storybook.add(MassHunting)
class MassBehaving(MassBattle):
      story_title = "Massive Planner Battle"
      dragon = actors.BehavingDragon
      villager = actors.BehavingVillager
storybook.add(MassBehaving)
