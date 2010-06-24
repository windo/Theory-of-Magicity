from random import random
from lib import fields
from base import FSMController, Actor
from magicballs import *

# Characters
class Character(Actor):
      stacking = 20

class Dude(Character):
      const_speed  = 6.0
      initial_hp   = 100
      sprite_names = ["dude-left", "dude-right"]
      snd_move     = ["step", "cape1", "cape2"]
      snd_death    = ["cry"]
      stacking     = 25

class Villager(Dude):
      sprite_names = ["villager-left", "villager-right"]
      stacking     = 20

class Rabbit(Character):
      const_speed  = 9.0
      anim_speed   = 2.0
      initial_hp   = 15
      regeneration = 2.0
      sprite_names = ["rabbit-left", "rabbit-right"]
      snd_move     = ["jump"]
      snd_death    = ["beep1", "beep2"]

class Dragon(Character):
      const_speed  = 2.0
      sprite_names = ["dragon-left", "dragon-right"]
      snd_move     = ["crackle1", "crackle2"]
      snd_death    = ["moan1", "moan2"]

class Guardian(Character):
      const_speed    = 1.0
      initial_hp     = 250
      regeneration   = 2.0
      initial_energy = 30.0
      sprite_names = ["guardian-left", "guardian-right"]
      in_dev_mode = False

# Controllers
class GuardianController(FSMController):
      """
      Block the movement of actors in self.danger with Time magic.
      If there is a waypoint, move to it abandoning the blocking action.
      """
      states = [ "idle", "guarding", "walking" ]
      danger = [ Dragon ]
      def __init__(self, puppet):
          FSMController.__init__(self, puppet)
          self.target   = False
          self.shot     = False
          self.waypoint = False
      def set_waypoint(self, waypoint):
          self.waypoint = waypoint

      def debug_info(self):
          return "%s target=%s waypoint=%.3s" % \
                 (FSMController.debug_info(self), self.target, self.waypoint)

      def get_target(self):
          closest    = 75.0
          new_target = False
          dangers = self.puppet.world.get_actors(self.puppet.pos - closest, self.puppet.pos + closest, include = self.danger)
          for danger in dangers:
            dist = abs(danger.pos - self.puppet.pos)
            if dist < closest:
              closest = dist
              new_target = danger

          if new_target:
            self.target = new_target
              
      def state_change(self):
          if self.state == "idle":
            if self.time_passed(2.0):
              self.get_target()
            if self.target:
              self.set_state("guarding")
            elif self.waypoint:
              self.set_state("walking")

          elif self.state == "guarding":
            if self.target.dead or abs(self.target.pos - self.puppet.pos) > 100:
              self.target = False
              self.get_target()

            if not self.target:
              if self.shot:
                self.puppet.magic.release(self.shot)
                self.shot = False
              self.set_state("idle")

          elif self.state == "walking":
            if not self.waypoint:
              self.set_state("idle")

      def state_action(self):
          if self.state == "idle":
            pass
          elif self.state == "guarding":
            # face the direction
            if self.target.pos < self.puppet.pos:
              if self.puppet.direction > 0:
                self.puppet.move_left()
                self.puppet.stop()
            else:
              if self.puppet.direction < 0:
                self.puppet.move_right()
                self.puppet.stop()

            # block the path
            if not self.shot or self.shot.dead:
              self.shot = self.puppet.magic.new(TimeBall)

            if self.target.pos < self.puppet.pos:
              dest_pos = self.puppet.pos - 20.0
            else:
              dest_pos = self.puppet.pos + 20.0
            dest_value = -1.0

            # shot position
            offset = abs(self.shot.pos - dest_pos)
            if offset > 1.0:
              if offset > 3.0:
                self.puppet.magic.power(self.shot, -1.0)
              c = min(1.0, abs(self.shot.pos + self.shot.speed - dest_pos) / 3.0)
              if self.shot.pos + self.shot.speed > dest_pos:
                self.puppet.magic.move(self.shot, -c * self.puppet.magic_energy)
              elif self.shot.pos + self.shot.speed < dest_pos:
                self.puppet.magic.move(self.shot,  c * self.puppet.magic_energy)

            # Field value
            if offset < 3.0:
              value = self.puppet.TimeField.value(self.shot.pos)
              diff  = dest_value - value
              c = min(1.0, abs(diff) / 0.05)
              if value < dest_value:
                self.puppet.magic.power(self.shot,  c * self.puppet.magic_energy)
              elif value > dest_value:
                self.puppet.magic.power(self.shot, -c * self.puppet.magic_energy)

          elif self.state == "walking":
            if self.time_passed(1.0):
              if self.puppet.pos > self.waypoint:
                self.puppet.move_left()
              else:
                self.puppet.move_right()

              if abs(self.puppet.pos - self.waypoint) < 1.0:
                self.puppet.stop()
                self.waypoint = False

class WimpyController(FSMController):
      """
      Indended for rabbits. Run around randomly (slowly drifting towards waypoint).
      If HP decreases fast enough, flee in the other direction.
      """
      states   = [ "idle", "flee" ]

      def __init__(self, *args):
          FSMController.__init__(self, *args)
          self.last_hp  = self.puppet.hp
          self.waypoint = 0.0

      def debug_info(self):
          return "%s waypoint=%3f" % (FSMController.debug_info(self), self.waypoint)
      def set_waypoint(self, waypoint):
          self.waypoint = waypoint

      def state_change(self):
          if self.state == "idle":
            if self.puppet.hp - self.last_hp < -self.puppet.timediff * 1.0:
              self.set_state("flee")
          elif self.state == "flee":
            if self.state_time() > 3.0:
              self.set_state("idle")
          self.last_hp = self.puppet.hp

      def state_action(self):
          if self.state == "idle":
            # move around randomly
            if self.time_passed(1.0, 2.0):
              decision = int(random() * 4) % 4
              if decision == 0:
                self.puppet.move_left()
              elif decision == 1:
                self.puppet.move_right()
              elif decision == 2:
                self.puppet.stop()
              elif decision == 3:
                if self.puppet.pos > self.waypoint:
                  self.puppet.move_left()
                else:
                  self.puppet.move_right()
          elif self.state == "flee":
            # reverse direction and start moving away from danger
            if self.time_passed(3.0):
              if self.puppet.direction > 0:
                self.puppet.move_left()
              else:
                self.puppet.move_right()

class HunterController(FSMController):
      """
      Hunt actors in self.puppet.prey.
      Try to keep appropriate distance, fire Life magic balls, evade nearby
      balls and heal self with Life magic.
      """
      states = [ "idle", "follow", "shoot", "evade", "heal" ]
      def __init__(self, puppet):
          FSMController.__init__(self, puppet)
          self.target   = False
          self.shot     = False
          self.waypoint = 0.0

      def debug_info(self):
          if self.target:
            target_pos = self.target.pos
          else:
            target_pos = 0
          return "%s target=%s (%.1f) waypoint=%.1f" % \
                 (FSMController.debug_info(self), self.target, target_pos, self.waypoint)
      def set_waypoint(self, waypoint):
          self.waypoint = waypoint

      def nearby(self, dist, who):
          closest = dist
          found   = False
          pos     = self.puppet.pos
          candidates = self.puppet.world.get_actors(pos - dist, pos + dist, include = who)
          for actor in candidates:
            distance = abs(actor.pos - pos)
            if distance < closest:
              closest = distance
              found   = actor
          return found
      # look for nearby actors and decide who to attack
      def acquire_target(self):
          new_target = self.nearby(75, self.puppet.prey)
          if new_target:
            self.target = new_target
      # look for nearby particles and decide which one to evade
      def acquire_particle(self):
          new_shot = self.nearby(5, [MagicParticle])
          if new_shot:
            self.shot = new_shot
            self.puppet.magic.capture(self.shot)
          
      def move_randomly(self):
          decision = int(random() * 4) % 4
          if decision == 0:
            self.puppet.move_left()
          elif decision == 1:
            self.puppet.move_right()
          elif decision == 2:
            self.puppet.stop()
          elif decision == 3:
            if self.puppet.pos > self.waypoint:
              self.puppet.move_left()
            else:
              self.puppet.move_right()

      def target_dist(self):
          return abs(self.target.pos - self.puppet.pos)
      def shot_dist(self):
          return abs(self.shot.pos - self.puppet.pos)
          
      def state_change(self):
          if self.state == "idle":
             if self.shot:
               self.set_state("evade")
             elif self.puppet.hp < self.puppet.initial_hp * 0.75:
               self.set_state("heal")
             elif self.target:
               self.set_state("follow")

          elif self.state == "follow":
            if self.state_time() > 3.0 or not self.target:
              self.target = False
              self.set_state("idle")
            elif self.shot:
              self.set_state("evade")
            elif self.state_time() > 1.0 and (50.0 > self.target_dist() > 10.0):
              self.set_state("shoot")

          elif self.state == "shoot":
            if self.state_time() > 5.0 or not self.shot:
              if self.shot:
                self.puppet.magic.release(self.shot)
                self.shot = False
              self.set_state("follow")

          elif self.state == "evade":
            if not self.shot:
              self.set_state("idle")

          elif self.state == "heal":
            if self.state_time() > 10.0 or self.puppet.hp > self.puppet.initial_hp * 0.9:
              if self.shot:
                self.puppet.magic.release(self.shot)
                self.shot = False
              self.set_state("idle")

      def state_action(self):
          if self.state == "idle":
            if self.time_passed(2.0, 1.0):
              self.move_randomly()
              self.acquire_target()
              self.acquire_particle()

          elif self.state == "follow":
            self.acquire_particle()
            if self.time_passed(1.0, 1.0):
              if abs(self.target.pos - self.puppet.pos) > 50.0:
                if self.target.pos > self.puppet.pos:
                  self.puppet.move_right()
                else:
                  self.puppet.move_left()
              elif abs(self.target.pos - self.puppet.pos) < 25.0:
                if self.target.pos > self.puppet.pos:
                  self.puppet.move_left()
                else:
                  self.puppet.move_right()
              else:
                self.move_randomly()

            # forget the dead
            if self.target.dead:
              self.target = False

          elif self.state == "shoot":
            # fire the shot and set it moving
            if not self.shot:
              if self.target.pos > self.puppet.pos:
                self.puppet.move_right()
              else:
                self.puppet.move_left()
              self.puppet.stop()
              self.shot = self.puppet.magic.new(LifeBall)
              self.puppet.magic.power(self.shot, 10.0)

            if self.shot.pos + self.shot.speed > self.target.pos:
              self.puppet.magic.move(self.shot, -3.0)
            else:
              self.puppet.magic.move(self.shot, 3.0)

          elif self.state == "evade":
            if self.shot_dist() > 10.0:
              self.puppet.magic.release(self.shot)
              self.shot = False
            elif self.time_passed(1.0, 1.0):
              if self.shot.pos > self.puppet.pos:
                self.puppet.magic.move(self.shot, 3.0)
                self.puppet.move_left()
              else:
                self.puppet.magic.move(self.shot, -3.0)
                self.puppet.move_right()

          elif self.state == "heal":
            if not self.shot:
              self.puppet.stop()
              self.shot = self.puppet.magic.new(LifeBall)
              self.puppet.magic.power(self.shot, -10.0)

            if self.shot.pos + self.shot.speed < self.puppet.pos:
              self.puppet.magic.move(self.shot, 1.0)
            else:
              self.puppet.magic.move(self.shot, -1.0)

# Controlled Actors
class HuntingDragon(Dragon):
      control = HunterController
      prey    = [Dude, Rabbit, Guardian]
class HuntingVillager(Villager):
      prey    = [Dragon]
      control = HunterController
class ScaredRabbit(Rabbit):
      control = WimpyController

class ControlledGuardian(Guardian):
      control = GuardianController
