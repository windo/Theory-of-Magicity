from random import random
from base import Actor, Controller

# swarming demo
class FlyingController(Controller):
      """
      A controller for the birds flying around in background.
      The different birds just need to implement the decision where to fly.
      """
      control_interval = 0.2
      def __init__(self, *args):
          Controller.__init__(self, *args)
          self.xdiff = self.ydiff = 0.0

      def debug_info(self):
          return "%s dir=[%.1f,%.1f]" % \
                 (Controller.debug_info(self), self.xdiff, self.ydiff)
      def normalize_xy(self, x, y, sum, scale_up = True, scale_down = True):
          """
          ensure that the cumulative vector of x,y is not smaller/larger than sum
          """
          # the vector length
          real_sum = (x ** 2 + y ** 2) ** 0.5
          if real_sum == 0:
            return x, y
          # scale up/down
          mult = sum / real_sum
          if real_sum < sum and scale_up or real_sum > sum and scale_down:
            x *= mult
            y *= mult
          return x, y

      def find_offset(self):
          """
          Must be overloaded to set up self.xdiff and self.ydiff
          to direct towards the destination where to fly
          """
          pass

      def update(self):
          self.find_offset()

          # face left/right
          if self.puppet.speed > 0:
            self.puppet.direction = 1
          else:
            self.puppet.direction = -1

          # accelerate
          x, y = self.normalize_xy(self.xdiff, self.ydiff, self.puppet.const_accel)
          self.puppet.accel  = x
          self.puppet.yaccel = y
          # limit speed
          x, y = self.normalize_xy(self.puppet.speed, self.puppet.yspeed, self.puppet.const_speed)
          self.puppet.speed  = x
          self.puppet.yspeed = y

class BirdFlocker(FlyingController):
      """
      A controller that attempts to fly around randomly prefering to keep
      together in flocks.
      
      When a predator brid approaches, the primary goal is to escape it.
      """
      def __init__(self, *args):
          FlyingController.__init__(self, *args)
          ## flocking params
          # grand scheme
          self.weight_waypoint = 4.5
          self.weight_flock    = 5.0
          self.weight_predator = 10.0
          self.weight_bounds   = 15.0
          # in flock
          self.weight_repel = 10.0
          self.weight_group = 5.0
          self.weight_speed = 1.0
          # flock shape
          self.prefer_dist  = 5.0
          self.group_size   = 20.0
          self.visible_dist = 30.0
          # random flying around points
          self.ypos_upper_bound = 90.0
          self.pos_max_spread   = 1000
          self.random_waypoint()

      def debug_info(self):
          return "%s way=[%.1f,%.1f]" % \
                 (FlyingController.debug_info(self), self.xwaypoint, self.ywaypoint)

      def random_waypoint(self):
          self.xwaypoint = random() * self.pos_max_spread - (self.pos_max_spread / 2)
          self.ywaypoint = random() * self.ypos_upper_bound

      def find_offset(self):
          # calculate destination, prefer waypoint
          x, y = self.normalize_xy(self.xwaypoint - self.puppet.pos,
                                   self.ywaypoint - self.puppet.ypos,
                                   self.weight_waypoint)
          self.xdiff, self.ydiff = x, y

          # bounds
          if self.puppet.ypos > self.ypos_upper_bound:
            self.ydiff -= self.weight_bounds

          vis_start = self.puppet.pos - self.visible_dist
          vis_end   = self.puppet.pos + self.visible_dist
          # predators
          preds = self.puppet.world.get_actors(vis_start, vis_end, include = [BigBird])
          pred_xdiff = pred_ydiff = 0.0
          for pred in preds:
            xdiff = pred.pos - self.puppet.pos
            ydiff = pred.ypos - self.puppet.ypos
            dist  = (xdiff ** 2 + ydiff ** 2) ** (0.5)
            if dist < self.visible_dist:
              pred_xdiff += -xdiff * (1 - dist / self.visible_dist)
              pred_ydiff += -ydiff * (1 - dist / self.visible_dist)
          if preds:
            x, y = self.normalize_xy(pred_xdiff, pred_ydiff, self.weight_predator)
            self.xdiff += x
            self.ydiff += y

          # find other birds
          neighs = self.puppet.world.get_actors(vis_start, vis_end, include = [SmallBird])
          # flocking
          flock_xdiff  = flock_ydiff  = 0.0
          flock_xspeed = flock_yspeed = 0.0
          for neigh in neighs:
            if neigh == self.puppet:
              continue
            xdiff = neigh.pos - self.puppet.pos
            ydiff = neigh.ypos - self.puppet.ypos
            dist  = (xdiff ** 2 + ydiff ** 2) ** (0.5)
            # repel if too close
            if dist < self.prefer_dist :
              const = (-1.0 + dist / self.prefer_dist) * self.weight_repel
            # group locally
            elif dist < self.group_size:
              const = self.weight_group * (dist - self.prefer_dist) / (self.group_size - self.prefer_dist)
            elif dist < self.visible_dist:
              const = self.weight_group - (dist - self.group_size) / (self.visible_dist - self.group_size)
            # ignore beyond sight
            else:
              const = 0.0
            # synchronize speeds
            if dist < self.prefer_dist * 2:
              flock_xspeed += neigh.speed
              flock_yspeed += neigh.yspeed
            flock_xdiff  += const * xdiff
            flock_ydiff  += const * ydiff
          if neighs:
            x, y = self.normalize_xy(flock_xdiff, flock_ydiff, self.weight_flock)
            self.xdiff += x
            self.ydiff += y
            x, y = self.normalize_xy(flock_xspeed, flock_yspeed, self.weight_speed)
            self.xdiff += x
            self.ydiff += y

      def update(self):
          FlyingController.update(self)
          # choose a next waypoint 
          if abs(self.xwaypoint - self.puppet.pos) < 1.0 and abs(self.ywaypoint - self.puppet.ypos) < 1.0:
            self.random_waypoint()

class BirdPredator(FlyingController):
      """
      Pick a random small bird and fly towards it
      """
      def __init__(self, *args):
          FlyingController.__init__(self, *args)
          self.random_target()
      def debug_info(self):
          return "%s target=[%.1f,%.1f]" % \
                 (FlyingController.debug_info(self), self.target.pos, self.target.ypos)
      def random_target(self):
          birds = self.puppet.world.get_actors(include = [SmallBird])
          self.target = birds[int(random() * len(birds))]
      def find_offset(self):
          self.xdiff = self.target.pos  - self.puppet.pos
          self.ydiff = self.target.ypos - self.puppet.ypos
      def update(self):
          FlyingController.update(self)
          if abs(self.target.pos - self.puppet.pos) < 1.0 and abs(self.target.ypos - self.puppet.ypos) < 1.0:
            self.random_target()

class Bird(Actor):
      animate_stop = True
      stacking     = 3
      base_height  = 0
      from_ceiling = True
      distance     = 3.0

      feel_magic   = False
      initial_hp   = 0
class SmallBird(Bird):
      sprite_names = ["smallbird-left", "smallbird-right"]
      const_speed  = 5
      const_accel  = 25
class BigBird(Bird):
      sprite_names = ["bigbird-left", "bigbird-right"]
      const_speed  = 10
      const_accel  = 15

class FlockingBird(SmallBird):
      control = BirdFlocker
class PredatorBird(BigBird):
      control = BirdPredator
