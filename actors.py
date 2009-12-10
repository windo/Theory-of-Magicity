import pygame, math, time
from random import random

class MagicCaster:
      """
      Supplements an Actor

      Handles the list of magic particles controlled by an actor
      Manages how the actor influences the particles
      """
      magic_distance = 5.0

      def __init__(self, actor, magic_energy):
          self.actor   = actor
          self.energy  = magic_energy
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
          # register to influence it [speed, power]
          self.affects[particle] = [0.0, 10.0]
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
      def move_right(self, particle):
          if self.affects.has_key(particle):
            self.affects[particle][0] = 5.0
            self.balance_energy()
      def move_left(self, particle):
          if self.affects.has_key(particle):
            self.affects[particle][0] = -5.0
            self.balance_energy()
      def power_up(self, particle):
          if self.affects.has_key(particle):
            self.affects[particle][1] += 1.0
            self.balance_energy()
      def power_down(self, particle):
          if self.affects.has_key(particle):
            self.affects[particle][1] -= 1.0
            self.balance_energy()
      def stop(self, particle):
          if self.affects.has_key(particle):
            self.affects[particle][0] = 0
            self.balance_energy()

      def balance_energy(self):
          """
          go over the list of affects and make sure we stay within
          the energy consumption limit
          """
          used = 0.0
          for speed, power in self.affects.values():
            used += abs(speed) + abs(power)
          if used > self.energy:
            ratio = self.energy / used
            for affect in self.affects.keys():
              speed, power = self.affects[affect]
              speed *= ratio
              power *= ratio
              self.affects[affect] = [speed, power]
            corrected = 0.0
            for speed, power in self.affects.values():
              corrected += abs(speed) + abs(power)
            #print "used=%.1f > total=%.1f -> ratio=%.2f: corrected=%.1f" % (used, self.energy, ratio, corrected)

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
      directed     = True

      # char attributes
      initial_hp   = 100.0
      regeneration = 0.5
      magic_energy = 25.0
      
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
          self.direction  = -1
          self.animate    = self.animate_stop

          # character params
          self.hp     = self.initial_hp
          self.magic  = MagicCaster(self, self.magic_energy)

          # load images
          if self.directed:
            self.img_left  = world.sprites.get(self.sprite_names[0])
            self.img_right = world.sprites.get(self.sprite_names[1])
            self.img_count = len(self.img_left)
            self.img_w     = self.img_left[0].get_width()
            self.img_h     = self.img_left[0].get_height()
          else:
            self.img_list  = world.sprites.get(self.sprite_names[0])
            self.img_count = len(self.img_list)
            self.img_w     = self.img_list[0].get_width()
            self.img_h     = self.img_list[0].get_height()
          self.cur_img_idx = 0

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

      # moving the actor
      def move_left(self):
          if not self.const_accel:
            self.speed   = -self.const_speed
          else:
            self.accel   = -self.const_accel
          self.animate   = True
          self.direction = -1
      def move_right(self):
          if not self.const_accel:
            self.speed   = self.const_speed
          else:
            self.accel   = self.const_accel
          self.animate   = True
          self.direction = 1
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
          # magic effect on time:
          magic_time_mult  = (self.LightField.value(self.pos) * 10.0 + 1.0)
          self.timediff    = self.timediff * magic_time_mult
          # update movement
          self.speed += self.timediff * self.accel
          magic_speed = self.EnergyField.value(self.pos)
          self.pos   += self.timediff * (self.speed + magic_speed)
          # effects of magic
          self.hp -= self.timediff * self.damage()
          if self.hp < self.initial_hp:
            self.hp += self.timediff * self.regeneration
          # death
          if self.hp <= 0 and self.initial_hp:
            self.destroy()
          # controlled actors
          if self.controller:
            self.controller.update()
      # different Actors can implement their own way of changing their hp
      def damage(self):
          light_damage  = abs(self.LightField.value(self.pos)) * 0.0
          energy_damage = abs(self.EnergyField.value(self.pos))
          earth_damage  = max(self.EarthField.value(self.pos), 0)
          return (light_damage + energy_damage + earth_damage) * 25.0
      
      # draw image, either left-right directed or unidirectional
      def draw(self, view, screen, draw_hp = False, draw_debug = False):
          # do not draw off-the screen actors
          if self.pos + self.img_w < self.world.view.pl_x1() or self.pos - self.img_w > self.world.view.pl_x2():
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
            hover = self.hover_height + self.hover_height * math.sin((time.time() - self.start_time) * 2) * 0.3
          else:
            hover = 0.0

          # actual drawing
          img = imglist[self.cur_img_idx]
          coords = (view.pl2sc_x(self.pos) - self.img_w / 2, view.sc_h() - self.img_h - hover)
          screen.blit(img, coords)

          # draw hp bar
          if draw_hp and self.initial_hp:
            hp_color   = (64, 255, 64)
            hp_border  = (view.pl2sc_x(self.pos), view.sc_h() - self.img_h - hover, 30, 3)
            hp_fill    = (view.pl2sc_x(self.pos), view.sc_h() - self.img_h - hover, 30 * (self.hp / self.initial_hp), 3)
            pygame.draw.rect(screen, hp_color, hp_border, 1)
            pygame.draw.rect(screen, hp_color, hp_fill, 0)

          if draw_debug:
            lines = self.debug_info().split("\n")
            txts  = []
            for line in lines:
              txts.append(self.world.font.render(line, False, (255, 255, 255)))
            i = 0
            for txt in txts:
              screen.blit(txt, (view.pl2sc_x(self.pos) - img.get_width() / 2, int(draw_debug) + 20 + i * 10))
              i += 1

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

class Tree(Actor):
      sprite_names = ["tree"]
      directed     = False
      initial_hp   = 0

class Dude(Actor):
      const_speed  = 4.0
      initial_hp   = 100
      sprite_names = ["dude-left", "dude-right"]

class Rabbit(Actor):
      const_speed  = 9.0
      anim_speed   = 2.0
      initial_hp   = 15
      regeneration = 5.0
      sprite_names = ["rabbit-left", "rabbit-right"]

class Dragon(Actor):
      const_speed  = 2.0
      sprite_names = ["dragon-left", "dragon-right"]

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
          if isinstance(actor, fields.MagicParticle):
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
              self.shot = self.puppet.magic.new(fields.EarthBall)
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
