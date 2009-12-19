import pygame, math, time
from random import random

class MagicCaster:
      """
      Supplements an Actor

      Handles the list of magic particles controlled by an actor
      Manages how the actor influences the particles
      """
      magic_distance = 5.0

      def __init__(self, actor):
          self.actor   = actor
          self.used    = 0.0
          self.affects = {}

      # called by controllers
      # manage controlled particles list
      def new(self, particletype):
          """
          make a new particle and control it
          """
          # make a new particle
          pos = self.actor.pos + self.actor.direction * self.magic_distance
          particle = self.actor.world.new_actor(particletype, pos)
          # register to influence it [speed, mult]
          self.affects[particle] = [0.0, 1.0]
          particle.affect(self)
          # return it to the caller
          return particle
      def capture(self, particle):
          """
          add to the list of controlled particles
          """
          if not self.affects.has_key(particle):
            self.affects[particle] = [0.0, 0.0]
            particle.affect(self)
      def release(self, particle):
          """
          cease controlling a particle
          """
          if self.affects.has_key(particle):
            del self.affects[particle]
            particle.release(self)
      def release_all(self):
          """
          release all particles
          """
          for particle in self.affects.keys():
            self.release(particle)

      # affect controlled particles
      def move(self, particle, set = False, diff = False):
          return self.change(particle, 0, set, diff)
      def power(self, particle, set = False, diff = False):
          return self.change(particle, 1, set, diff)
      def change(self, particle, key, set, diff):
          if self.affects.has_key(particle):
            if set is not False:
              self.affects[particle][key] = set
            elif diff is not False:
              self.affects[particle][key] += diff
            else:
              return self.affects[particle][key]
            self.balance_energy()
          if not (set or diff):
            return 0.0

      def energy(self):
          return self.actor.magic_energy
      def balance_energy(self):
          """
          go over the list of affects and make sure we stay within
          the energy consumption limit
          """
          used = 0.0
          for speed, power in self.affects.values():
            used += abs(speed) + abs(power)
          if used > self.energy():
            ratio = self.energy() / used
            for affect in self.affects.keys():
              speed, power = self.affects[affect]
              speed *= ratio
              power *= ratio
              self.affects[affect] = [speed, power]
            corrected = 0.0
            for speed, power in self.affects.values():
              corrected += abs(speed) + abs(power)
            #print "used=%.1f > total=%.1f -> ratio=%.2f: corrected=%.1f" % (used, self.energy(), ratio, corrected)

      # called by particles
      def affect_particle(self, particle):
          return self.affects[particle]
      def notify_destroy(self, particle):
          if self.affects.has_key(particle):
            del self.affects[particle]

class Actor:
      # movement
      const_speed    = 0.0
      const_accel    = 0.0

      # animation conf
      animate_stop = False
      anim_speed   = 1.0
      hover_height = 0.0
      base_height  = 0.0
      directed     = True
      from_ceiling = False
      stacking     = 0
      # sounds
      snd_move     = []
      snd_death    = []

      # char attributes
      initial_hp     = 100.0
      regeneration   = 0.5
      initial_energy = 10.0
      
      # "puppetmaster"
      control        = None

      def __init__(self, world, pos):
          # movement params
          self.speed = 0.0
          self.accel = 0.0
          self.pos   = pos
          self.world = world

          # fields
          self.LightField = self.world.get_field(fields.LightField)
          self.EnergyField = self.world.get_field(fields.EnergyField)
          self.EarthField = self.world.get_field(fields.EarthField)

          # actor clock
          self.last_update = world.get_time()
          self.timediff    = 0.0

          # animation params
          self.start_time = time.time()
          self.rnd_time_offset = random() * 25.0
          self.direction  = -1
          self.animate    = self.animate_stop
          self.next_sound = 0.0

          # character params
          self.hp           = self.initial_hp
          self.magic_energy = self.initial_energy
          self.magic        = MagicCaster(self)
          self.dead         = False

          # load images
          if len(self.sprite_names):
            if self.directed:
              self.img_left  = world.loader.get_spritelist(self.sprite_names[0])
              self.img_right = world.loader.get_spritelist(self.sprite_names[1])
              self.img_count = len(self.img_left)
              self.img_w     = self.img_left[0].get_width()
              self.img_h     = self.img_left[0].get_height()
            else:
              self.img_list  = world.loader.get_spritelist(self.sprite_names[0])
              self.img_count = len(self.img_list)
              self.img_w     = self.img_list[0].get_width()
              self.img_h     = self.img_list[0].get_height()
            self.cur_img_idx = 0
          else:
            self.img_w = 100
            self.img_h = 100

          # controller init
          if self.control:
            self.controller = self.control(self)
          else:
            self.controller = None
      def destroy(self):
          self.world.del_actor(self)
          self.magic.release_all()

      def __str__(self):
          return "%s(0x%s)" % (str(self.__class__).split(".")[1], id(self))
      def debug_info(self):
          desc = "%s pos=%.1f speed=%.3f" % (str(self), self.pos, self.speed)
          if self.controller:
            desc += "\nController: %s" % (self.controller.debug_info())
          return desc

      # play sounds
      def in_range(self):
          return self.pos > self.world.view.pl_x1() and self.pos < self.world.view.pl_x2()
      def movement_sound(self):
          if self.snd_move and self.in_range() and self.next_sound < self.world.get_time():
            self.next_sound = self.world.get_time() + 1.0 + random()
            count = len(self.snd_move)
            sound = self.snd_move[int(random() * count)]
            self.world.loader.play_sound(sound)
      def death_sound(self):
          if self.snd_death and self.in_range():
            count = len(self.snd_death)
            sound = self.snd_death[int(random() * count)]
            self.world.loader.play_sound(sound)

      # moving the actor
      def move_left(self):
          if not self.const_accel:
            self.speed   = -self.const_speed
          else:
            self.accel   = -self.const_accel
          self.animate   = True
          self.direction = -1
          self.movement_sound()
      def move_right(self):
          if not self.const_accel:
            self.speed   = self.const_speed
          else:
            self.accel   = self.const_accel
          self.animate   = True
          self.direction = 1
          self.movement_sound()
      def stop(self):
          if not self.const_accel:
            self.speed   = 0
          else:
            self.accel   = 0
          self.animate   = self.animate_stop

     # called every frame
      def update(self):
          # update actor clock
          now              = self.world.get_time()
          self.timediff    = now - self.last_update
          self.last_update = now
          # update movement
          if self.const_speed or self.const_accel:
            self.speed += self.timediff * self.accel
            magic_speed = self.EnergyField.value(self.pos) * 15.0
            magic_mult  = self.LightField.value(self.pos)
            if magic_mult > 0:
              magic_mult *= 5.0
            else:
              magic_mult *= 1.0
            magic_mult   += 1.0
            self.pos   += magic_mult * self.timediff * (self.speed + magic_speed)
            if self.animate:
              self.movement_sound()
          # update hp
          light_damage  = abs(self.LightField.value(self.pos))    * 10.0
          energy_damage = abs(self.EnergyField.value(self.pos))   * 10.0
          earth_damage  = max(self.EarthField.value(self.pos), 0) * 25.0
          self.hp -= self.timediff * (light_damage + energy_damage + earth_damage)
          if self.hp < self.initial_hp:
            magic_regen = max(-self.EarthField.value(self.pos), 0) * 12.5
            self.hp += self.timediff * (self.regeneration + magic_regen)
          if self.hp > self.initial_hp:
            self.hp = self.initial_hp
          # death
          if self.hp <= 0 and self.initial_hp:
            self.dead = True
            self.death_sound()
            self.destroy()
          # set magic energy
          magic_mult = self.EarthField.value(self.pos) / 2.0 + 1.0
          self.magic_energy = magic_mult * self.initial_energy
          # controlled actors
          if self.controller:
            self.controller.update()
      
      # draw image, either left-right directed or unidirectional
      def draw(self, screen, draw_debug = False, draw_hp = False):
          view = self.world.view
          # do not draw off-the screen actors
          if self.pos + self.img_w < view.pl_x1() or self.pos - self.img_w > view.pl_x2():
            return

          # draw debugging information
          if draw_debug:
            lines = self.debug_info().split("\n")
            txts  = []
            for line in lines:
              txts.append(self.world.loader.debugfont.render(line, True, (255, 255, 255)))
            i = 0
            for txt in txts:
              screen.blit(txt, (view.pl2sc_x(self.pos) - self.img_w / 2, int(draw_debug) + 20 + i * 20))
              i += 1

          # do not draw/animate spriteless actors
          if len(self.sprite_names) == 0:
            return

          # facing direction
          if self.directed:
            if self.direction > 0:
              imglist = self.img_right
            else:
              imglist = self.img_left
          # unidirectional
          else:
            imglist = self.img_list

          # to animate or not to animate
          if self.animate:
            self.cur_img_idx = int(time.time() * self.img_count * self.anim_speed) % self.img_count
          else:
            self.cur_img_idx = 0

          # hovering in air (particles)
          if self.hover_height:
            hover = self.hover_height + self.hover_height * \
                    math.sin((time.time() + self.rnd_time_offset - self.start_time) * 2) * 0.3
          else:
            hover = 0.0

          # actual drawing
          img = imglist[self.cur_img_idx]
          coords = (view.pl2sc_x(self.pos) - self.img_w / 2, view.sc_h() - self.img_h - hover - self.base_height)
          screen.blit(img, coords)

          # draw hp bar (if there is one)
          if draw_hp and self.initial_hp:
            hp_color   = (64, 255, 64)
            hp_border  = (view.pl2sc_x(self.pos), view.sc_h() - self.img_h - hover, 30, 3)
            hp_fill    = (view.pl2sc_x(self.pos), view.sc_h() - self.img_h - hover, 30 * (self.hp / self.initial_hp), 3)
            pygame.draw.rect(screen, hp_color, hp_border, 1)
            pygame.draw.rect(screen, hp_color, hp_fill, 0)

import fields

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
          self.set_state(self.start_state)
      def __str__(self):
          return "%s" % (str(self.__class__).split(".")[1])
      def debug_info(self):
          return "%s: [%s]" % (str(self), self.state)

      def set_state(self, newstate):
          if not newstate in self.states:
            raise self.InvalidState(newstate)
          if newstate != self.state:
            self.state       = newstate
            self.state_start = self.puppet.world.get_time()
            self.action_time = 0.0

      def time_passed(self, duration, rand = 0.0):
          passed = self.puppet.world.get_time() - self.action_time
          if passed > duration + rand * random():
            self.action_time = self.puppet.world.get_time()
            return True
          else:
            return False

      def state_time(self):
          return self.puppet.world.get_time() - self.state_start

      def update(self):
          self.state_change()
          self.last_hp = self.puppet.hp
          self.state_action()
      def state_change(self):
          pass
      def state_action(self):
          pass

# scenery
class Scenery(Actor):
      directed   = False
      stacking   = 0
      initial_hp = 0
class Tree(Scenery):
      sprite_names = ["tree"]
class Sun(Scenery):
      sprite_names = ["sun"]
      base_height  = 300
class Post(Scenery):
      sprite_names = ["post"]
      animate_stop = True
      stacking     = 5

# Characters
class Character(Actor):
      stacking = 10

class Dude(Character):
      const_speed  = 6.0
      initial_hp   = 100
      sprite_names = ["dude-left", "dude-right"]
      snd_move     = ["step", "cape1", "cape2"]
      snd_death    = ["cry"]

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
      const_speed    = 0.5
      initial_hp     = 250
      regeneration   = 2.0
      initial_energy = 20.0
      sprite_names = ["guardian-left", "guardian-right"]

# controllers
class GuardianController(FSMController):
      states = [ "idle", "guarding" ]
      def __init__(self, puppet):
          FSMController.__init__(self, puppet)
          self.target = False
          self.shot   = False

      def state_change(self):
          if self.state == "idle":
            if self.time_passed(2.0):
              dude = self.puppet.world.get_actors(self.puppet.pos - 75, self.puppet.pos + 75, include = [ Dude ])
              if dude:
                self.target = dude[0]
                self.set_state("guarding")

          elif self.state == "guarding":
            if self.target.dead or abs(self.target.pos - self.puppet.pos) > 100:
              self.target = False
              if self.shot:
                self.puppet.magic.release(self.shot)
                self.shot = False
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
              self.shot = self.puppet.magic.new(fields.LightBall)

            # shot position
            if self.target.pos < self.puppet.pos:
              dest_pos = self.puppet.pos - 20.0
            else:
              dest_pos = self.puppet.pos + 20.0

            offset = abs(self.shot.pos - dest_pos)
            if offset > 1.0:
              self.puppet.magic.power(self.shot, 0.0)
              if self.shot.pos + self.shot.speed > dest_pos:
                self.puppet.magic.move(self.shot, -self.puppet.magic_energy)
              elif self.shot.pos + self.shot.speed < dest_pos:
                self.puppet.magic.move(self.shot, self.puppet.magic_energy)

            # Field value
            if offset < 3.0:
              value      = self.puppet.LightField.value(self.shot.pos)
              dest_value = -1.0
              if value < dest_value:
                self.puppet.magic.power(self.shot, self.puppet.magic_energy)
              elif value > dest_value:
                self.puppet.magic.power(self.shot, -self.puppet.magic_energy)

class RabbitController(FSMController):
      states   = [ "idle", "flee" ]

      def __init__(self, *args):
          FSMController.__init__(self, *args)
          self.waypoint = 0.0

      def debug_info(self):
          return "%s waypoint=%3f" % (FSMController.debug_info(self), self.waypoint)
      def set_waypoint(self, waypoint):
          self.waypoint = waypoint

      def state_change(self):
          if self.state == "idle":
            if self.last_hp * 0.99 > self.puppet.hp:
              self.set_state("flee")
          elif self.state == "flee":
            if self.state_time() > 3.0:
              self.set_state("idle")

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

class DragonController(FSMController):
      states = [ "idle", "follow", "shoot", "evade", "heal" ]
      def __init__(self, puppet):
          FSMController.__init__(self, puppet)
          self.target   = False
          self.shot     = False
          self.waypoint = 0.0

      def debug_info(self):
          return "%s target=%s waypoint=%3f" % (FSMController.debug_info(self), self.target, self.waypoint)
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
          new_target = self.nearby(75, [Dude, Rabbit])
          if new_target:
            self.target = new_target
      # look for nearby particles and decide which one to evade
      def acquire_particle(self):
          new_shot = self.nearby(5, [fields.MagicParticle])
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
              if self.target.pos - self.puppet.pos > 50.0:
                if self.target.pos > self.puppet.pos:
                  self.puppet.move_right()
                else:
                  self.puppet.move_left()
              elif self.target.pos - self.puppet.pos < 25.0:
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
              self.shot = self.puppet.magic.new(fields.EarthBall)
              self.puppet.magic.power(self.shot, 10.0)
              if self.target.pos > self.shot.pos:
                self.puppet.magic.move(self.shot, 3.0)
              else:
                self.puppet.magic.move(self.shot, -3.0)

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
              self.shot = self.puppet.magic.new(fields.EarthBall)
              self.puppet.magic.power(self.shot, -10.0)

            if self.shot.pos + self.shot.speed < self.puppet.pos:
              self.puppet.magic.move(self.shot, 1.0)
            else:
              self.puppet.magic.move(self.shot, -1.0)

class ControlledDragon(Dragon):
      control = DragonController
class ControlledRabbit(Rabbit):
      control = RabbitController
class ControlledGuardian(Guardian):
      control = GuardianController
