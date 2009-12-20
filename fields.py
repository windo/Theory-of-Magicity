from random import random
import pygame, math
import effects

class MagicField:
      """
      An abstract magic field, currently consisting of
      normal distribution "particles"
      """
      # granularity of drawing the field
      drawpoints = 150
      basevalue  = 0.0

      def __init__(self, loader):
          self.visibility = False
          self.particles  = []
          self.loader  = loader

      # could be overloaded
      def value(self, pos):
          v = self.particle_values(pos) + 0.003 * random()
          #if abs(v) > 0.2:
          #  print (pos, v)
          return v

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
          return pos, view.sc_h() - (self.value(view.sc2pl_x(pos)) + 1.0) * view.sc_h() / 2.0
      def draw(self, view, screen, draw_debug = False):
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
              pygame.draw.line(screen, color, this, next, 3)
              if draw_debug:
                if pos % (self.drawpoints / 5) == 0:
                  at    = view.sc2pl_x(pos * step)
                  val   = self.value(at)
                  txt   = "%s.value(%.2f:%.2f) = %.2f" % (str(self.__class__).split(".")[1], pos, at, val)
                  txt   = self.loader.debugfont.render(txt, True, (255, 255, 255))
                  screen.blit(txt, this)
              # move on
              this = next

# Light
# affects: speed < health regen? > vision
# TODO: vision effects
class LightField(MagicField):
      basevalue = 0.0
      poscolor  = (192, 192, 255)
      negcolor  = (64, 64, 0)

# Energy
# affects: right < health regen? > left
class EnergyField(MagicField):
      poscolor = (255, 255, 128)
      negcolor = (0, 0, 128)

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
      hover_height = 100.0
      initial_hp   = 0
      directed     = False
      stacking     = 26

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
          self.dead      = False
          self.field.add_particle(self)

          # animation
          if len(self.effectors) == 1:
            fx = self.effectors[0](self)
            self.particle_effects = [fx]
          else:
            fxpos = self.effectors[0](self)
            fxneg = self.effectors[1](self)
            self.particle_effects = [fxpos, fxneg]

          # MagicCaster objects of actors who are influencing this particle
          self.affects  = []
          # selected in game UI
          self.selected = False

      def debug_info(self):
          desc  = actors.Actor.debug_info(self)
          desc += "\nAffecting:\n"
          for aff in self.affects:
            name      = str(aff.actor)
            acc, mult = aff.affect_particle(self)
            desc += "%s: acc=%.2f, mult=%.2f\n" % (name, acc, mult)
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
          actors.Actor.update(self)

          # update fancy graphics drawers
          value = self.field.value(self.pos)
          if len(self.particle_effects) == 1:
            self.particle_effects[0].update(value)
          else:
            if value > 0:
              self.particle_effects[0].update(value)
              self.particle_effects[1].update(0)
            else:
              self.particle_effects[0].update(0)
              self.particle_effects[1].update(abs(value))
         
          # each caster can effect the particle
          accel = 0.0
          mult  = 0.0
          for caster in self.affects:
            affects = caster.affect_particle(self)
            accel += affects[0]
            mult  += affects[1]
          self.accel = accel * 3.0
          self.mult += (mult - self.mult) * self.mult_speed * self.timediff

          # if the power drops too low, terminate itself
          if abs(self.mult) < 0.1:
            if self.deadtimer:
              if self.deadtimer + 1.0 < self.world.get_time():
                self.dead = True
                self.destroy()
            else:
              self.deadtimer = self.world.get_time()
          else:
            self.deadtimer = False

      def draw(self, screen, draw_debug = False, draw_hp = False):
          actors.Actor.draw(self, screen, draw_debug, draw_hp)
          # draw magic "ball"
          radius = 25
          s = pygame.surface.Surface((radius * 2, radius * 2), pygame.SRCALPHA, 32)
          pygame.draw.circle(s, (255, 255, 255, 32), (radius, radius), radius, 0)
          screen.blit(s, (self.world.view.pl2sc_x(self.pos) - radius, self.world.view.sc_h() - self.hover_height - radius))
          if self.selected:
            radius = 50
            s = pygame.surface.Surface((radius * 2, radius * 2), pygame.SRCALPHA, 32)
            pygame.draw.circle(s, (255, 255, 255, 16), (radius, radius), radius, 0)
            screen.blit(s, (self.world.view.pl2sc_x(self.pos) - radius, self.world.view.sc_h() - self.hover_height - radius))
          # draw field effects
          for fx in self.particle_effects:
            fx.draw(screen, draw_debug)


class LightBall(MagicParticle):
      sprite_names = []
      effectors    = [ effects.Energy ]
      fieldtype    = LightField
class EnergyBall(MagicParticle):
      sprite_names = []
      effectors    = [ effects.Wind ]
      fieldtype    = EnergyField
class EarthBall(MagicParticle):
      sprite_names = []
      effectors    = [ effects.Fire, effects.Nature ]
      fieldtype    = EarthField
