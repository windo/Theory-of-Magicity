import time
import core, particles, fields
from random import random

class Tree(core.Actor):
      sprite_names = ["tree"]
      directed     = False
      initial_hp   = 0

class Dude(core.Actor):
      const_speed  = 4.0
      initial_hp   = 100
      sprite_names = ["dude-left", "dude-right"]

class Rabbit(core.Actor):
      const_speed  = 9.0
      anim_speed   = 2.0
      initial_hp   = 15
      regeneration = 5.0
      sprite_names = ["rabbit-left", "rabbit-right"]

class Dragon(core.Actor):
      const_speed  = 2.0
      sprite_names = ["dragon-left", "dragon-right"]
      def __init__(self, world, pos):
          core.Actor.__init__(self, world, pos)
          self.dev   = 1.0
          self.mult  = 2.0
          self.world.fields.get(fields.FireField).add_particle(self)
      def destroy(self):
          core.Actor.destroy(self)
          self.world.fields.get(fields.FireField).del_particle(self)

      # particle params (normal distribution)
      def get_params(self):
          return self.pos, self.dev, self.mult

      def damage(self):
          #return self.world.fields.get(fields.IceField).v(self.pos) * 25.0
          return 0

class FSMController:
      states = [ "idle" ]
      start_state = "idle"

      class InvalidState(Exception):
            def __init__(self, state):
                self.state = state
            def __str__(self):
                return "Invalid state change to: %s" % (self.state)

      def __init__(self, puppet):
          self.puppet  = puppet
          self.last_hp = puppet.hp
          self.state   = False
          self.switch(self.start_state)
      def __str__(self):
          return "%s" % (str(self.__class__).split(".")[1])
      def debug_info(self):
          return "%s: [%s]" % (str(self), self.state)

      def switch(self, newstate):
          if not newstate in self.states:
            raise self.InvalidState(newstate)
          if newstate != self.state:
            self.state       = newstate
            self.switch_time = time.time()

      def state_time(self):
          return time.time() - self.switch_time

      def update(self):
          self.state_change()
          self.last_hp = self.puppet.hp
          self.state_action()
      def state_change(self):
          pass
      def state_action(self):
          pass

class RabbitController(FSMController):
      states = [ "idle", "jolt", "flee" ]
      def state_change(self):
          if self.state == "jolt":
            self.switch("flee")
          if self.last_hp * 0.999 > self.puppet.hp and not self.state == "flee":
            self.switch("jolt")
          elif self.state_time() > 2.0:
            self.switch("idle")

      def state_action(self):
          if self.state == "idle":
            # move around randomly
            if random() < 0.05:
              decision = int(random() * 3) % 3
              if decision == 0:
                self.puppet.move_left()
              elif decision == 1:
                self.puppet.move_right()
              else:
                self.puppet.stop()
          elif self.state == "jolt":
            # reverse direction and start moving away from danger
            if self.puppet.direction > 0:
              self.puppet.move_left()
            else:
              self.puppet.move_right()
          elif self.state == "flee":
            # continue the jolting direction
            pass

class DragonController(FSMController):
      states = [ "idle", "follow", "shoot" ]
      def __init__(self, puppet):
          FSMController.__init__(self, puppet)
          self.target = False
          self.shot   = False
      def debug_info(self):
          return "%s target=%s" % (FSMController.debug_info(self), self.target)

      def valid_target(self, actor):
          """
          Decide if an Actor is worth targeting
          """
          if actor == self.puppet:
            return False
          if isinstance(actor, particles.MagicParticle):
            return False
          if isinstance(actor, Tree):
            return False
          if isinstance(actor, Dragon):
            return False
          return True
      def state_change(self):
          closest = 75
          target = False
          if self.state_time() > 1.0:
            for actor in self.puppet.world.get_actors(self.puppet.pos - closest,
                                                      self.puppet.pos + closest,
                                                      lambda x: self.valid_target(x)):
              distance = abs(actor.pos - self.puppet.pos)
              if distance < closest:
                closest = distance
                target  = actor
            if target:
              self.target = target
            else:
              self.switch("idle")
              self.target = False

          # target_distance
          if self.target:
            target_distance = abs(self.target.pos - self.puppet.pos)

          # shoot will end by itself
          if self.state != "shoot":
            # if no target and or target far away, idly walk around
            if not self.target or target_distance > 75:
              self.switch("idle")
              self.target = False
            # only follow or shoot if we have a target
            elif self.target:
              # pause between shots
              if self.state_time() > 1.5:
                self.switch("shoot")
              # only follow if not close enough
              elif target_distance > 5:
                self.switch("follow")
              # walk around near the target
              else:
                self.switch("idle")

      def state_action(self):
          if self.state == "idle":
            if random() < 0.05:
              decision = int(random() * 3) % 3
              if decision == 0:
                self.puppet.move_left()
              elif decision == 1:
                self.puppet.move_right()
              elif decision == 2:
                self.puppet.stop()
          elif self.state == "follow":
            if self.target.pos > self.puppet.pos:
              self.puppet.move_right()
            else:
              self.puppet.move_left()
          elif self.state == "shoot":
            if not self.shot:
              self.shot = self.puppet.magic.new(particles.FireBall)
              if self.target.pos > self.puppet.pos:
                self.puppet.magic.move_right(self.shot)
              else:
                self.puppet.magic.move_left(self.shot)
            target_dist = self.target.pos - self.puppet.pos
            magic_dist  = self.shot.pos - self.puppet.pos
            if abs(magic_dist) > abs(target_dist) / 2:
              self.puppet.magic.stop(self.shot)
              #self.puppet.magic.release(self.shot)
              self.shot = False
              self.switch("idle")

class ControlledDragon(Dragon):
      control = DragonController
class ControlledRabbit(Rabbit):
      control = RabbitController
