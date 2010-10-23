from lib.stories import Story, storybook
from lib import actors

class PlannerSkirmish(Story):
      storybook_path = "demos"
      def __init__(self, *args):
          Story.__init__(self, *args)

          world = self.world
          for i in xrange(2):
            d = world.new_actor(actors.BehavingDragon, 75.0)
            d = world.new_actor(actors.BehavingVillager, 100.0)
            #d.controller.set_waypoint(-100.0)
          world.camera.follow(d)

      def get_player(self):
          return None
      def update(self):
          pass
storybook.add(PlannerSkirmish)
