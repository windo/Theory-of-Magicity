#!/usr/bin/python

import time, os, sys, math
from random import random
from operator import attrgetter

import pygame
from pygame.locals import *

class SpriteLoader:
      """
      Load images and divide them to separate surfaces
      """
      class NoImage(Exception):
            def __init__(self, name):
                self.name = name
            def __str__(self):
                return "No Image %s" % (self.name) 

      def __init__(self):
          self.lists  = {}
          self.images = {}

      def load(self, filename, listname = False, width = False, start = 0, to = False, flip = False):
          # load the file, if not already loaded
          if not self.images.has_key(filename):
            self.images[filename] = pygame.image.load("img/" + filename)
          img = self.images[filename]

          # make an image list as well?
          if listname:
            if not width:
              if flip:
                img = pygame.transform.flip(img, True, False)
              self.lists[listname] = [img]
            else:
              # use all subsurfaces?
              if not to:
                to = int(img.get_width() / width)
              self.lists[listname] = []
              for i in xrange(start, to):
                rect = [ i * width, 0, width, img.get_height() ]
                subimg = img.subsurface(rect)
                if flip:
                  subimg = pygame.transform.flip(subimg, True, False)
                self.lists[listname].append(subimg)

      def get(self, name):
          if name in self.images.keys():
            return self.images[name]
          elif name in self.lists.keys():
            return self.lists[name]
          else:
            raise self.NoImage(name)

class View:
      """
      Viewport/scale to use for translating in-game coordinates to screen coordinates
      """
      def __init__(self, view, plane):
          """
          view is (width, height) - input/output scale
          plane is (x1, y1, x2, y2) - the MagicField area to fit in the view
          """
          self.view  = list(view)
          self.plane = list(plane)
          self.recalculate()
      def recalculate(self):
          view_w, view_h = self.view
          plane_x1, plane_y1, plane_x2, plane_y2 = self.plane
          plane_w = plane_x2 - plane_x1
          plane_h = plane_y2 - plane_y1
          # multiplier to get plane coordinates from view coordinates
          self.mult_x = float(plane_w) / float(view_w)
          self.mult_y = float(plane_h) / float(view_h)
          # offset to apply to plane coordinates
          self.offset_x = plane_x1
          self.offset_y = plane_y2

      def pl_x1(self): return self.plane[0]
      def pl_x2(self): return self.plane[2]
      def pl_y1(self): return self.plane[1]
      def pl_y2(self): return self.plane[3]
      def sc_w(self): return self.view[0]
      def sc_h(self): return self.view[1]

      def get_center_x(self):
          return self.plane[0] + float(self.plane[2] - self.plane[0]) / 2.0
      def move_x(self, x):
          self.offset_x += x
          self.plane[0] += x
          self.plane[2] += x

      def sc2pl_x(self, x):
          return x * self.mult_x + self.offset_x
      def sc2pl_y(self, y):
          return self.offset_y - y * self.mult_y
      def pl2sc_x(self, x):
          return (x - self.offset_x) / self.mult_x
      def pl2sc_y(self, y):
          return (self.offset_y - y) / self.mult_y

class World:
      def __init__(self, sprites, fieldtypes, view):
          self.sprites     = sprites
          self.view        = view
          self.time_offset = 0.0
          self.pause_start = False

          # world objects
          self.fields  = {}
          for fieldtype in fieldtypes:
            field = fieldtype()
            self.fields[fieldtype] = field
          self.actors  = []

          # for convenience
          self.font    = pygame.font.SysFont("any", 14)
          self.bigfont = pygame.font.SysFont("any", 20)

      def time(self):
          if self.pause_start:
            return self.pause_start
          return time.time() - self.time_offset

      def pause(self):
          if self.pause_start:
            self.time_offset += time.time() - self.pause_start
            self.pause_start = False
          else:
            self.pause_start = time.time()
      def paused(self):
          if self.pause_start:
            return True
          else:
            return False

      # actor management
      def new_actor(self, actor_class, pos):
          actor = actor_class(self, pos)
          self.actors.append(actor)
          return actor
      def del_actor(self, actor):
          self.actors.pop(self.actors.index(actor))
      def all_actors(self):
          return self.actors
      def get_actors(self, x1 = False, x2 = False, filter = False):
          """
          Get actors with position in range [x1 : x2] and matching filter
          """
          ret = []
          for actor in self.actors:
            if x1 and actor.pos < x1:
              continue
            if x2 and actor.pos > x2:
              continue
            if filter and not filter(actor):
              continue
            ret.append(actor)
          return ret
      def sort_actors(self):
          self.actors.sort(key = attrgetter("pos"))

      # field management
      def get_field(self, fieldtype):
          return self.fields[fieldtype]
      def all_fields(self):
          return self.fields.values()

class MagicCaster:
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
      def release(self):
          """
          cease controlling a particle
          """
          if self.affects.has_key(particle):
            del self.affects[particle]
            particle.release(self)

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
      regeneration = 0.01
      magic_energy = 25.0
      
      # "puppetmaster"
      control        = None

      def __init__(self, world, pos):
          # movement params
          self.speed = 0.0
          self.accel = 0.0
          self.pos   = pos
          self.world = world
          # actor clock
          self.last_update = world.time()
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

      def __str__(self):
          desc = "%s(0x%s) pos=%.1f speed=%.3f" % (str(self.__class__).split(".")[1], id(self), self.pos, self.speed)
          if self.controller:
            desc += "\n Controller: %s" % (str(self.controller))
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
          now              = self.world.time()
          self.timediff    = now - self.last_update
          self.last_update = now
          # update movement
          if self.accel:
            self.speed += self.timediff * self.accel
          if self.speed:
            self.pos  += self.timediff * self.speed * self.world.get_field(OilField).v(self.pos)
          # effects of magic
          self.hp -= self.timediff * self.damage()
          if self.hp < self.initial_hp:
            self.hp += self.timediff * self.regeneration
          # death
          if self.hp <= 0 and self.initial_hp:
            self.world.del_actor(self)
          # controlled actors
          if self.controller:
            self.controller.update()
      # different Actors can implement their own way of changing their hp
      def damage(self):
          return self.world.fields.get(FireField).v(self.pos) * 25.0
      
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
            lines = str(self).split("\n")
            txts  = []
            for line in lines:
              txts.append(self.world.font.render(line, False, (255, 255, 255)))
            i = 0
            for txt in txts:
              screen.blit(txt,(view.pl2sc_x(self.pos) - 100, int(draw_debug) + 20 + i * 10))
              i += 1

class MagicField:
      """
      An abstract magic field, currently consisting of
      normal distribution "particles"
      """
      # granularity of drawing the field
      drawpoints = 150

      def __init__(self):
          self.visibility = False
          self.particles  = []

      # could be overloaded
      def v(self, pos):
          return self.particle_values(pos) + 0.01 * random()

      # add a new normal distribution
      def add_particle(self, particle):
          self.particles.append(particle)
      def del_particle(self, particle):
          self.particles.pop(self.particles.index(particle))
      # add all particles together
      def particle_values(self, pos):
          v = 0.0
          for particle in self.particles:
            # likely not to have any effect farther than that, optimize out
            if abs(particle.pos - pos) < 25:
              mean, dev, mult = particle.get_params()
              v += 1 / (dev * math.sqrt(2 * math.pi)) * math.exp((-(pos - mean) ** 2)/(2 * dev ** 2)) * mult
          return v

      # draw the field on screen
      def toggle_visibility(self, set = None):
          if set == None:
            self.visibility = not self.visibility
          else:
            self.visibility = set
      # Get the field's value at pos as translated through the view
      def sc_value(self, view, pos):
          return pos, view.pl2sc_y(self.v(view.sc2pl_x(pos)))
      def draw(self, view, screen):
          if self.visibility:
            # step should be float to cover the whole range
            step = float(screen.get_width()) / float(self.drawpoints)
            for pos in xrange(self.drawpoints):
              pygame.draw.line(screen, self.color, self.sc_value(view, pos * step), self.sc_value(view, (pos + 1) * step))

class MagicParticle(Actor):
      # Actor params
      const_accel  = 5.0
      animate_stop = True
      anim_speed   = 3.0
      hover_height = 25.0
      initial_hp   = 0
      directed     = False

      # Particle params
      base_dev     = 5.0
      base_mult    = 10.0
      mult_speed   = 0.1  # percentage change per second
      energy_drain = 30.0

      def __init__(self, world, pos):
          Actor.__init__(self, world, pos)
          self.field     = world.get_field(self.fieldtype)
          self.dev       = self.base_dev
          self.mult      = 1.0
          self.deadtimer = False
          self.field.add_particle(self)

          # actors who are influencing this particle
          self.affects = []

      def __str__(self):
          desc = Actor.__str__(self)
          desc += "\nAffecting: %s" % (", ".join([str(aff.actor.__class__).split(".")[1] for aff in self.affects]))
          return desc

      # MagicCasters register to influence the particle
      def affect(self, caster):
          self.affects.append(caster)
      def release(self, caster):
          self.affects.pop(self.affects.index(caster))

      # particle params (position, normal distribution params) for field calculation
      def get_params(self):
          return [self.pos, self.dev, self.mult]

      def destroy(self):
          # no more field effects
          self.field.del_particle(self)
          # remove from world
          self.world.del_actor(self)
          # notify casters that the particle is gone now
          for caster in self.affects:
            caster.notify_destroy(self)

      def update(self):
          Actor.update(self)
         
          # each caster can effect the particle
          accel = 0.0
          mult  = 0.0
          for caster in self.affects:
            affects = caster.affect_particle(self)
            accel += affects[0]
            mult  += affects[1]
          self.accel = accel
          self.mult += (mult - self.mult) * self.mult_speed * self.timediff

          # if the power drops too low, terminate itself
          if self.mult < 0.1:
            if self.deadtimer:
              if self.deadtimer + 1.0 < self.world.time():
                self.destroy()
            else:
              self.deadtimer = self.world.time()

class FireField(MagicField):
      color = (255, 0, 0)
class IceField(MagicField):
      color = (0, 128, 255)
class OilField(MagicField):
      color = (32, 32, 48)
      def v(self, pos):
          return 1.0 + self.particle_values(pos) + 0.01 * random()

class FireBall(MagicParticle):
      sprite_names = ["fireball"]
      fieldtype    = FireField
class IceBall(MagicParticle):
      sprite_names = ["iceball"]
      fieldtype    = IceField
      #fieldtype    = FireField
      #def get_params(self):
      #    params = MagicParticle.get_params(self)
      #    params[2] *= -1
      #    return params
class OilBall(MagicParticle):
      sprite_names = ["oilball"]
      fieldtype    = OilField

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
      regeneration = 0.1
      sprite_names = ["rabbit-left", "rabbit-right"]

class Dragon(Actor):
      const_speed  = 2.0
      sprite_names = ["dragon-left", "dragon-right"]
      def __init__(self, world, pos):
          Actor.__init__(self, world, pos)
          self.dev   = 1.0
          self.mult  = 2.0
          world.fields.get(FireField).add_particle(self)

      # particle params (normal distribution)
      def get_params(self):
          return self.pos, self.dev, self.mult

      def damage(self):
          return self.world.fields.get(IceField).v(self.pos) * 25.0

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
          return "%s: [%s]" % (str(self.__class__).split(".")[1], self.state)

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
      def __str__(self):
          return "%s: [%s] -> %s" % (str(self.__class__).split(".")[1], self.state, self.target)

      def valid_target(self, actor):
          """
          Decide if an Actor is worth targeting
          """
          if actor == self.puppet:
            return False
          if isinstance(actor, MagicParticle):
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
              self.shot = self.puppet.magic.new(FireBall)
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

class Game:
      def __init__(self):
          # initialize pygame
          pygame.init()
          pygame.display.set_caption('Magic')
          screensize  = (1200, 300)
          self.screen = pygame.display.set_mode(screensize)
          self.clock  = pygame.time.Clock()

          # loading sprites
          self.sprites = sprites = SpriteLoader()
          sprites.load("fire.png", "fireball", 25)
          sprites.load("ice.png", "iceball", 25)
          sprites.load("oil.png", "oilball", 25)
          sprites.load("dude.png", "dude-right", 25)
          sprites.load("dude.png", "dude-left", 25, flip = True)
          sprites.load("rabbit.png", "rabbit-right", 25)
          sprites.load("rabbit.png", "rabbit-left", 25, flip = True)
          sprites.load("dragon.png", "dragon-right", 25)
          sprites.load("dragon.png", "dragon-left", 25, flip = True)
          sprites.load("tree.png", "tree")

          # set up game objects
          self.view   = view   = View(screensize, (0, 0, 100, 2))
          self.world  = world  = World(sprites, [FireField, IceField, OilField], view)

          for i in xrange(10):
            world.new_actor(Tree, -250 + 100 * i)
          world.new_actor(ControlledDragon, 70)
          world.new_actor(ControlledDragon, 75)
          world.new_actor(ControlledDragon, 80)
          for i in xrange(15):
            world.new_actor(ControlledRabbit, 300 * random())

          # player-controlled object
          self.dude = world.new_actor(Dude, 10)

      def run(self):
          # loop
          forever = True

          # calibrating game speed
          lasttime   = int(time.time())
          frames     = 0
          lastframes = 0
          fps        = 0

          # performance debugging stats
          draw_field_time = 0
          draw_actor_time = 0
          update_actor_time = 0

          # extra debugging(?) output
          draw_hp     = False
          draw_debug  = False
          free_camera = False

          # input states
          get_magic  = False
          cast_magic = False
          sel_magic  = False

          # omit self.
          dude   = self.dude
          world  = self.world
          view   = self.view
          screen = self.screen

          while forever:
            # actors moving
            stime = time.time()
            if not world.paused():
              for actor in world.all_actors():
                actor.update()
            update_actor_time = time.time() - stime
          
            # center view to dude
            if not free_camera:
              diff = dude.pos - view.get_center_x()
              if 30.0 > abs(diff) > 5.0:
                view.move_x(diff * 0.005)
              elif 45.0 > abs(diff) >= 30.0:
                view.move_x(diff * 0.01)
              elif abs(diff) >= 45.0:
                view.move_x(diff * 0.05)
          
            # draw
            # background changes slightly in color
            if world.paused():
              day = -1.0
              screen.fill([16, 32, 96])
            else:
              day = math.sin(time.time()) + 1
              screen.fill([day * 32, 64 + day * 32, 192 + day * 32])
            # draw fields
            stime = time.time()
            for field in world.all_fields():
              field.draw(view, screen)
            draw_field_time = time.time() - stime
            # draw actors (with debug data?)
            debug_offset = 1
            stime = time.time()
            self.world.sort_actors()
            for actor in self.world.all_actors():
              actor.draw(view, screen, draw_hp, int(draw_debug) * debug_offset)
              debug_offset = (debug_offset + 20) % (view.sc_h() - 20 - 100)
            draw_actor_time = time.time() - stime
            # draw performance stats
            if draw_debug:
              fps_txt = world.font.render("FPS: %.1f" % (fps), False, (255, 255, 255))
              stats   = world.font.render("Actors: %u, Draw field=%.3f actors=%.3f, update actors=%.3f" % (len(world.all_actors()), draw_field_time, draw_actor_time, update_actor_time), False, (255, 255, 255))
              screen.blit(fps_txt, (10, 10))
              screen.blit(stats, (10, 25))
            # draw magic selection
            if get_magic:
              i = 1
              local_balls = self.world.get_actors(dude.pos - 100, dude.pos + 100, lambda x: isinstance(x, MagicParticle))
              for ball in local_balls:
                ball_txt = world.font.render("%u: %s" % (i, str(ball)), False, ball.field.color)
                ball_nr  = world.bigfont.render("%u" % (i), False, ball.field.color)
                screen.blit(ball_txt, (10, 40 + i * 10))
                screen.blit(ball_nr, (view.pl2sc_x(ball.pos), view.sc_h() - 80))
                i += 1
            # draw dude's magic (magic selection)
            if sel_magic:
              pygame.draw.circle(screen, (255, 255, 255), (view.pl2sc_x(sel_magic.pos), view.sc_h() - 40), 25, 1)
            pygame.display.update()
          
            # handle events
            for event in pygame.event.get():
              if event.type == pygame.QUIT:
                forever = False
              
              # key events
              if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                  forever = False

                if event.key == pygame.K_p:
                  world.pause()
          
                # dude moving
                elif event.key == pygame.K_LEFT:
                  dude.move_left()
                elif event.key == pygame.K_RIGHT:
                  dude.move_right()

                elif event.key == pygame.K_j:
                  free_camera = True
                  view.move_x(-10.0)
                elif event.key == pygame.K_k:
                  free_camera = False
                elif event.key == pygame.K_l:
                  free_camera = True
                  view.move_x(+10.0)
          
                # magic moving
                elif sel_magic and event.key == pygame.K_a:
                  dude.magic.move_left(sel_magic)
                elif sel_magic and event.key == pygame.K_d:
                  dude.magic.move_right(sel_magic)
                elif sel_magic and event.key == pygame.K_w:
                  dude.magic.power_up(sel_magic)
                elif sel_magic and event.key == pygame.K_s:
                  dude.magic.power_down(sel_magic)

                # mode switching
                elif event.key == pygame.K_TAB:
                  draw_hp    = not draw_hp
                  draw_debug = not draw_debug
                elif event.key == pygame.K_LSHIFT:
                  cast_magic = True
                  sel_magic  = False
                elif event.key == pygame.K_LCTRL:
                  get_magic  = True
                  sel_magic  = False
                
                # cast_magic & fields
                elif cast_magic and event.key == pygame.K_z:
                  sel_magic = dude.magic.new(FireBall)
                  casting = False
                elif cast_magic and event.key == pygame.K_x:
                  sel_magic = dude.magic.new(IceBall)
                  casting = False
                elif cast_magic and event.key == pygame.K_c:
                  sel_magic = dude.magic.new(OilBall)
                  casting = False

                # toggle magic fields
                elif event.key == pygame.K_z:
                  world.get_field(FireField).toggle_visibility()
                elif event.key == pygame.K_x:
                  world.get_field(IceField).toggle_visibility()
                elif event.key == pygame.K_c:
                  world.get_field(OilField).toggle_visibility()

                # recapture existing particles
                elif get_magic and event.key >= pygame.K_1 and event.key <= pygame.K_9:
                  idx = event.key - pygame.K_1
                  if len(local_balls) > idx:
                    sel_magic = local_balls[idx]
                    dude.magic.capture(sel_magic)
                elif get_magic and not cast_magic and event.key == pygame.K_a:
                  capture_ball = False
                  for ball in local_balls:
                    if ball.pos < dude.pos:
                      capture_ball = ball
                  if capture_ball:
                    sel_magic = capture_ball
                    dude.magic.capture(sel_magic)
                elif get_magic and not cast_magic and event.key == pygame.K_d:
                  capture_ball = False
                  for ball in local_balls:
                    if ball.pos > dude.pos:
                      capture_ball = ball
                      break
                  if capture_ball:
                    sel_magic = capture_ball
                    dude.magic.capture(sel_magic)
          
              # key releases
              if event.type == pygame.KEYUP:
                # movement
                if event.key == pygame.K_LEFT:
                  dude.stop()
                elif event.key == pygame.K_RIGHT:
                  dude.stop()

                # magic movement
                elif event.key == pygame.K_a and sel_magic:
                  dude.magic.stop(sel_magic)
                elif event.key == pygame.K_d and sel_magic:
                  dude.magic.stop(sel_magic)

                # input modes
                elif event.key == pygame.K_LSHIFT:
                  cast_magic = False
                elif event.key == pygame.K_LCTRL:
                  get_magic = False
          
            # calibration
            self.clock.tick(45)
            frames += 1
            if int(time.time()) != lasttime:
              fps = (frames - lastframes)
              lasttime   = int(time.time())
              lastframes = frames
          
if __name__ == "__main__":
   g = Game()
   g.run()
