from random import random
import pygame, math

class MagicField:
      """
      An abstract magic field, currently consisting of
      normal distribution "particles"
      """
      # granularity of drawing the field
      drawpoints = 150
      basevalue  = 0.0

      def __init__(self):
          self.visibility = False
          self.particles  = []

          self.font = pygame.font.SysFont("any", 14)

      # could be overloaded
      def value(self, pos):
          return self.particle_values(pos) + 0.01 * random()

      # add a new normal distribution
      def add_particle(self, particle):
          self.particles.append(particle)
      def del_particle(self, particle):
          self.particles.pop(self.particles.index(particle))
      # add all particles together
      def particle_values(self, pos):
          v = self.basevalue
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
          return pos, view.pl2sc_y(self.value(view.sc2pl_x(pos)) + 1.0)
      def draw(self, view, screen):
          if self.visibility:
            # step should be float to cover the whole range
            step = float(screen.get_width()) / float(self.drawpoints)
            # first point
            this = self.sc_value(view, 0.0)
            for pos in xrange(self.drawpoints):
              # at the next position
              next = self.sc_value(view, (pos + 1) * step)
              # color of the line segment
              if this > 0.0: color = self.poscolor
              else: color = self.negcolor
              # draw
              pygame.draw.line(screen, color, this, next)
              if pos % (self.drawpoints / 5) == 0:
                value = self.value(view.sc2pl_x(pos))
                txt   = "%s.value = %.2f" % (str(self.__class__).split(".")[1], value)
                txt   = self.font.render(txt, False, (255, 255, 255))
                screen.blit(txt, this)
              # move on
              this = next

# Light
# affects: time speed < health regen? > vision
class LightField(MagicField):
      basevalue = 0.0
      poscolor  = (192, 192, 255)
      negcolor  = (64, 64, 0)

# Energy
# affects: right < health regen? > left
class EnergyField(MagicField):
      poscolor = (255, 255, 192)
      negcolor = (0, 0, 64)

# Earth
# affects: energy regen <-> health regen
class EarthField(MagicField):
      poscolor = (192, 64, 192)
      negcolor = (64, 192, 64)

all = [ LightField,
        EnergyField,
        EarthField ]

import actors
class MagicParticle(actors.Actor):
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
      mult_speed   = 0.25  # percentage change per second

      def __init__(self, world, pos):
          actors.Actor.__init__(self, world, pos)
          self.field     = world.get_field(self.fieldtype)
          self.dev       = self.base_dev
          self.mult      = 1.0
          self.deadtimer = False
          self.field.add_particle(self)

          # actors who are influencing this particle
          self.affects = []

      def debug_info(self):
          desc = actors.Actor.debug_info(self)
          desc += "\nAffecting: %s: %s" % (", ".join([str(aff.actor) for aff in self.affects]))
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

class LightBall(MagicParticle):
      sprite_names = ["iceball"]
      fieldtype    = LightField
class EnergyBall(MagicParticle):
      sprite_names = ["fireball"]
      fieldtype    = EnergyField
class EarthBall(MagicParticle):
      sprite_names = ["lifeball"]
      fieldtype    = EarthField
