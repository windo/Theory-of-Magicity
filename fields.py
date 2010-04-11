from random import random
import pygame, math
import effects

class MagicField:
      """
      An abstract magic field, currently consisting of
      normal distribution "particles"
      """
      # step for drawing the field
      draw_real_points = 50
      # extra points to interpolate
      interpolate = 2
      # field base value - currently nothing changes this
      basevalue  = 0.0

      def __init__(self, loader):
          self.particles  = []
          self.loader  = loader
      def __str__(self):
          return str(self.__class__).split(".")[1]
      def __repr__(self):
          return self.__str__()

      # could be overloaded
      def value(self, pos):
          v = self.particle_values(pos)
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
      def draw(self, view, draw_debug = False):
          # step should be float to cover the whole range
          step = float(view.sc_w()) / float(self.draw_real_points)
          cur  = self.value(view.sc2pl_x(0))
          for i in xrange(self.draw_real_points):
            i   += 1
            pos  = i * step
            next = self.value(view.sc2pl_x(pos))
            for j in xrange(self.interpolate):
              value = cur + (next - cur) / self.interpolate * j
              # draw
              if abs(value) > 0.01:
                # color of the line segment
                alpha = min(192, abs(value) * 256 * 8)
                color = self.color + (alpha,)
                s = effects.get_circle(color, min(5, abs(value) * 100), view.screen, 3)
                ypos = view.sc_h() - (value + 1.0) * view.sc_h() / 2.0
                view.blit(s, (pos - step + j * step / self.interpolate, ypos))

            # draw debug
            if draw_debug and i % (self.draw_real_points / 5) == 0 and abs(cur) > 0.01:
              at  = view.sc2pl_x(pos)
              txt = "%s.value(%.2f:%.2f) = %.2f" % (str(self), i, at, next)
              txt = self.loader.debugfont.render(txt, True, (255, 255, 255))
              ypos = view.sc_h() - (next + 1.0) * view.sc_h() / 2.0
              view.blit(txt, (pos, ypos))

            # next interpolation
            cur = next

# Time
# affects: speed < health regen? > vision
# TODO: vision effects
class TimeField(MagicField):
      basevalue = 0.0
      color  = (192, 192, 255)

# Wind
# affects: right < health regen? > left
class WindField(MagicField):
      color = (255, 255, 128)

# Life
# affects: energy regen <-> health regen
class LifeField(MagicField):
      color = (192, 64, 192)

all = [ TimeField,
        WindField,
        LifeField ]

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
      in_dev_mode  = False

      # Particle params
      base_dev     = 5.0
      base_mult    = 10.0
      base_coeff   = 0.8  # seems that this is the maximum output with dev=5 and mult=10, used to normalize the mult
      mult_speed   = 0.25 # percentage change per second

      def __init__(self, world, pos):
          actors.Actor.__init__(self, world, pos)
          self.field     = world.get_field(self.fieldtype)
          self.dev       = self.base_dev
          self.mult      = 0.0
          self.accel     = 0.0
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
          desc += "\nState: acc=%.1f mult=%.1f\n" % (self.accel, self.mult)
          desc += "Affecting:\n"
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
          return [self.pos, self.dev, self.mult / self.base_coeff]

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
          # smooth changing of multiplier
          multdiff = (mult - self.mult)
          self.mult += self.timediff * multdiff * self.mult_speed
          # acceleration is immediate 
          self.accel = accel * 3.0

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

      def draw(self, draw_debug = False):
          view = self.world.view
          actors.Actor.draw(self, draw_debug)
          # draw magic "ball"
          radius = 25 
          x      = self.world.view.pl2sc_x(self.pos)
          y      = self.world.view.sc_h() - self.hover_height
          s = effects.get_circle((255, 255, 255, 64), radius, view.screen, blur = 15)
          view.blit(s, (x - radius, y - radius))

          # draw field effects
          for fx in self.particle_effects:
            fx.draw(view.screen, draw_debug)
            
          # if it's selected
          if self.selected:
            radius = 50
            s = effects.get_circle((255, 255, 255, 16), radius, view.screen)
            view.blit(s, (x - radius, y - radius))
            # affects
            s = effects.get_circle((255, 255, 255, 64), 5, view.screen, 2)
            for caster in self.affects:
              accel, mult = caster.affect_particle(self)
              for i in xrange(5):
                xdiff = accel * 55.0 / 10 / 5 * i
                ydiff = mult  * 55.0 / 10 / 5 * i
                view.blit(s, (x - 5 + xdiff, y - 5 - ydiff))

class TimeBall(MagicParticle):
      sprite_names = []
      effectors    = [ effects.Energy ]
      fieldtype    = TimeField
class WindBall(MagicParticle):
      sprite_names = []
      effectors    = [ effects.Wind ]
      fieldtype    = WindField
      snd_move     = ["wind1", "wind2", "wind3"]
class LifeBall(MagicParticle):
      sprite_names = []
      effectors    = [ effects.Fire, effects.Nature ]
      fieldtype    = LifeField

field2ball = { TimeField: TimeBall, WindField: WindBall, LifeField: LifeBall }

