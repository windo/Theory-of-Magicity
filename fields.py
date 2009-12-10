from random import random
import pygame, math

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
      def value(self, pos):
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
          return pos, view.pl2sc_y(self.value(view.sc2pl_x(pos)))
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
              # move on
              this = next

# Temperature (fire-ice)
# affects: speed, energy
class FireField(MagicField):
      poscolor = (255, 0, 0)
      negcolor = (0, 128, 255)

# Quickness (water-earth)?
# multiplier for movement speed - like "oiled up"
class QuickField(MagicField):
      poscolor = (192, 192, 192)
      negcolor = (96, 32, 64)

# Movement (air-
# constant speed acceleration - like "wind"
class WindField(MagicField):
      poscolor = (128, 128, 128)
      negcolor = (128, 128, 128)

# regeneration/detoriation
# direct hp effects - like health/sickness
class LifeField(MagicField):
      poscolor = (32, 224, 32)
      negcolor = (0, 0, 0)

# damage limitation/multiplication
class GuardField(MagicField):
      poscolor = (192, 192, 0)
      negcolor = (192, 0, 192)

# magic energy multiplier
class EnergyField(MagicField):
      poscolor = (192, 192, 255)
      negcolor = (64, 64, 96)

# visibility field - either invisible or visible from far away
class SmokeField(MagicField):
      poscolor = (128, 128, 192)
      negcolor = (255, 255, 255)
      
all = [ FireField,
        QuickField,
        MoveField,
        LifeField,
        GuardField,
        EnergyField,
        SmokeField ]
