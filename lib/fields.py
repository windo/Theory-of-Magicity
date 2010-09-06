from random import random
import pygame, math
import effects
import actors
from lib.debug import dbg

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
      # maximum distance where particles will have an effect
      maxdist = 25

      def __init__(self, loader):
          self.particles = []
          self.loader    = loader
      def __str__(self):
          return self.__class__.__name__
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

          total = len(self.particles)
          if total > 0:
            # find first particle
            #dbg("Finding first particle")
            first = i = 0
            last = total - 1
            while last > first:
              half = int(math.ceil(float(last - first) / 2))
              i = first + half
              #dbg("first=%u i=%u last=%u" % (first, i, last))
              if self.particles[i].pos - pos < -self.maxdist:
                first += half
              else:
                last -= half
          
            # count all of them
            while i < len(self.particles) and self.particles[i].pos < pos + self.maxdist:
              particle = self.particles[i]
              mean, dev, mult = particle.get_params()
              value = 1 / (dev * math.sqrt(2 * math.pi)) * math.exp((-(pos - mean) ** 2)/(2 * dev ** 2)) * mult
              v += value
              i += 1
          return v

      def update(self):
          self.particles.sort(lambda x, y: cmp(x.pos, y.pos))

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
                s = effects.get_circle(color, min(5, abs(value) * 100), view.graphics, 3)
                ypos = view.sc_h() - (value + 1.0) * view.sc_h() / 2.0
                view.graphics.blit(s, (pos - step + j * step / self.interpolate, ypos))

            # draw debug
            if draw_debug and i % (self.draw_real_points / 5) == 0 and abs(cur) > 0.01:
              at  = view.sc2pl_x(pos)
              txt = "%s.value(%.2f:%.2f) = %.2f" % (str(self), i, at, next)
              txt = self.loader.debugfont.render(txt, True, (255, 255, 255))
              ypos = view.sc_h() - (next + 1.0) * view.sc_h() / 2.0
              view.graphics.blit(txt, (pos, ypos))

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
