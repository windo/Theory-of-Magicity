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
          self.particles  = []
          self.loader  = loader

      # could be overloaded
      def value(self, pos):
          v = self.particle_values(pos)
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

      # Get the field's value at pos as translated through the view
      def draw(self, view, screen, draw_debug = False):
          # step should be float to cover the whole range
          step = float(view.sc_w()) / float(self.drawpoints)
          for i in xrange(self.drawpoints):
            pos   = i * step
            value = self.value(view.sc2pl_x(pos))
            ypos  = view.sc_h() - (value + 1.0) * view.sc_h() / 2.0
            # draw
            if abs(value) > 0.01:
              # color of the line segment
              alpha = min(192, abs(value) * 256 * 8)
              color = self.color + (alpha,)
              s = effects.get_circle(color, min(3, abs(value) * 100, screen))
              screen.blit(s, (pos, ypos))
              if draw_debug and i % (self.drawpoints / 5) == 0:
                at  = view.sc2pl_x(pos)
                txt = "%s.value(%.2f:%.2f) = %.2f" % (str(self.__class__).split(".")[1], i, at, value)
                txt = self.loader.debugfont.render(txt, True, (255, 255, 255))
                screen.blit(txt, (pos, ypos))

# Light
# affects: speed < health regen? > vision
# TODO: vision effects
class LightField(MagicField):
      basevalue = 0.0
      color  = (192, 192, 255)

# Energy
# affects: right < health regen? > left
class EnergyField(MagicField):
      color = (255, 255, 128)

# Earth
# affects: energy regen <-> health regen
class EarthField(MagicField):
      color = (192, 64, 192)

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
          self.mult      = 0.0
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
          #value = self.field.value(self.pos)
          value = self.mult / 10.0
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

      def draw(self, screen, draw_debug = False):
          actors.Actor.draw(self, screen, draw_debug)
          # draw magic "ball"
          radius = 25
          x      = self.world.view.pl2sc_x(self.pos)
          y      = self.world.view.sc_h() - self.hover_height
          s = effects.get_circle((255, 255, 255, 32), radius, screen)
          screen.blit(s, (x - radius, y - radius))

          # draw field effects
          for fx in self.particle_effects:
            fx.draw(screen, draw_debug)
            
          # if it's selected
          if self.selected:
            radius = 50
            s = effects.get_circle((255, 255, 255, 16), radius, screen)
            screen.blit(s, (x - radius, y - radius))
            # affects
            s = effects.get_circle((255, 255, 255, 64), 5, screen)
            for caster in self.affects:
              accel, mult = caster.affect_particle(self)
              screen.blit(s, (x - 5 + accel * 3.0, y - 5 - mult * 3.0))



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
