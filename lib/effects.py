#!/usr/bin/python

import pygame, math, time
from random import random
import graphics

global circle_cache, circle_cache_hit, circle_cache_miss
circle_cache = {}
circle_cache_hit = circle_cache_miss = 0
def get_circle(color, radius, screen = False, blur = 0):
    global circle_cache, circle_cache_hit, circle_cache_miss
    # color accuracy
    c = tuple()
    for i in xrange(4):
      colval = int(color[i] / 8 + 0.5) * 8
      if colval > 255: colval = 255
      c += (colval,)
    color  = tuple(c)
    radius = int(radius)
    blur   = int(blur)

    # try to get it from cache
    if circle_cache.has_key((color, radius, blur)):
      circle_cache_hit += 1
      return circle_cache[(color, radius, blur)]
    else:
      circle_cache_miss += 1
      s = pygame.surface.Surface((radius * 2, radius * 2), pygame.SRCALPHA, 32)
      # 0-alpha background
      s.fill(color[:3] + (0,))
      # circle
      pygame.draw.circle(s, color, (radius, radius), radius, 0)

      # blur the edges of the circle (just set the alpha)
      if blur:
        alphas      = pygame.surfarray.pixels_alpha(s)
        color_alpha = color[3]
        center      = radius
        for y in xrange(radius):
          for x in xrange(radius):
            if x + y < radius - blur:
              pass
            dist = ((x - center) ** 2 + (y - center) ** 2) ** 0.5
            if dist < radius - blur:
              pass
            elif dist > radius + 0.5:
              pass
            else:
              alpha = max(radius - dist, 0.0) / (blur + 1) * color_alpha
              alphas[y][x] = alpha
              alphas[2 * center - 1 - y][x] = alpha
              alphas[y][2 * center - 1 - x] = alpha
              alphas[2 * center - 1 - y][2 * center - 1 - x] = alpha

      # optimize for screen
      if screen:
        s = s.convert_alpha(screen)
      s = graphics.image(s)

      # save to cache
      circle_cache[(color, radius, blur)] = s
      return s

class Dot:
      img_cache_time = 0.1
      def __init__(self, x, y, xs, ys, age = 0.0):
          self.x   = x
          self.y   = y
          self.xs  = xs
          self.ys  = ys
          self.age = age
          # cached image
          self.img = False
          self.ts  = 0
class ParticleEffect:
      normal_particles = 50.0
      def __init__(self, magic = None, intensity = 1.0, max_age = 2.0, xofs = 100.0):
          # how many to generate per second
          self.intensity = intensity
          # when to remove the dot
          self.max_age   = max_age
          self.last_time = time.time()
          self.dots      = []
          # for game
          self.magic     = magic
          # for standalone tester
          self.xofs      = xofs

      def update(self, intensity = None):
          # override one passed at init
          if intensity is not None:
            self.intensity = intensity
          self.persec    = abs(self.intensity) * self.normal_particles
          # timing
          if self.magic:
            new_time = self.magic.world.get_time()
          else:
            new_time = time.time()
          timediff = new_time - self.last_time
          self.last_time = new_time

          # update each dot
          i = 0
          while i < len(self.dots):
            dot = self.dots[i]
            dot.age += timediff
            self.update_speed(dot, timediff)
            dot.x   += dot.xs * timediff
            dot.y   += dot.ys * timediff
            # age old dots
            if dot.age > self.max_age:
              self.dots.pop(i)
            else:
              i += 1

          # generate new dots
          if random() < self.persec * timediff:
            dot = self.gen_dot()
            if self.magic is not None:
              dot.pos   = self.magic.pos
              dot.hover = self.magic.hover_height
            self.dots.append(dot)
            
      def draw(self, screen, draw_debug = False):
          if self.magic:
            now = self.magic.world.get_time()
          else:
            now = time.time()
          for dot in self.dots:
            if dot.ts + dot.img_cache_time > now and dot.img:
              s = dot.img
            else:
              color        = self.get_color(dot)
              radius, blur = self.get_radius(dot)
              # TODO: there really should be a better way to do this (but apparently there isn't?)
              s = get_circle(color, radius, screen, blur)
              dot.ts  = now
              dot.img = s
            if self.magic:
              view = self.magic.world.view
              x = view.pl2sc_x(dot.pos) + dot.x - s.get_width() / 2
              y = view.sc_h() - dot.hover + dot.y - s.get_height() / 2
              view.blit(s, (x, y))
            else:
              screen.blit(s, (dot.x + self.xofs - s.get_width() / 2, 100 + dot.y - s.get_height() / 2))

# A template
class Dummy(ParticleEffect):
      def gen_dot(self):
          return Dot(0, 0, 0, 0)
      def get_radius(self, dot):
          return 1, 0
      def get_color(self, dot):
          return (0, 0, 0, 0)
      def update_speed(self, dot, timediff):
          pass

class Gradient:
      def __init__(self, gradient):
          self.gradient = gradient
      def get_color(self, pos):
          # find the two gradients to blend between
          if self.gradient[0][0] >= pos:
            return self.gradient[0][1:]
          elif self.gradient[len(self.gradient) - 1][0] <= pos:
            return self.gradient[len(self.gradient) - 1][1:]
          else:
            i = 0
            while i < len(self.gradient):
              g = self.gradient[i]
              if pos < g[0]:
                p2, c2 = g[0], g[1:]
                glast = self.gradient[i - 1]
                p1, c1 = glast[0], glast[1:]
                break
              elif g[0] == pos:
                return g[1:]
              i += 1

          # do the blend
          k = (pos - p1) / (p2 - p1)
          c = [] 
          for i in xrange(len(c1)):
            c.append(int(c1[i] + k * (c2[i] - c1[i])))
          return tuple(c)
          
class Fire(ParticleEffect):
      def __init__(self, *args, **kwargs):
          ParticleEffect.__init__(self, *args, **kwargs)
          self.firegradient = Gradient((
            (   0, 255, 255, 255, 255),
            (0.25, 255, 255,   0, 255),
            (0.75, 255, 150,   0, 255),
            ( 1.5, 150,   0,   0, 255),
            ( 1.5, 128, 128, 128, 255),
            ( 2.0, 128, 128, 128,   0)
            ))
      def gen_dot(self):
          x = random() * 10.0 - 5.0
          y = random() * 10.0 - 5.0
          xs = random() * 5.0 - 2.5
          ys = random() * 5.0 - 30.0
          return Dot(x, y, xs, ys)
      def get_radius(self, dot):
          if dot.age < 0.1:
            return 5.0, 1.0
          else:
            return min(5 + dot.age ** 2 * 3.0, 20), 2.0
      def get_color(self, dot):
          return self.firegradient.get_color(dot.age)
      def update_speed(self, dot, timediff):
          dot.ys += timediff * 1.0
          dot.xs += math.sin(dot.age * 25.0)

class Nature(ParticleEffect):
      def __init__(self, *args, **kwargs):
          ParticleEffect.__init__(self, *args, **kwargs)
          self.naturegradient1 = Gradient((
            (   0,  32, 192,   0, 255),
            (0.25,  32, 192,   0, 255),
            (   2, 224,   0,   0, 128),
            ))
          self.naturegradient2 = Gradient((
            (   0,  64, 224,   0, 128),
            (0.25, 128, 224,   0, 128),
            (   1, 128,  64,   0, 128),
            (   2,  64,  32,   0,  64),
            ))
      def gen_dot(self):
          dot = Dot(random() * 10 - 5, random() * 25.0, random() * 2.0 - 1.0, 5.0 + random() * 1.0)
          if random() < 0.5:
            dot.radius = 1.0, 0.0
          else:
            dot.radius = 5.0, 2.0
          dot.seed = random() * 100.0
          return dot
      def get_radius(self, dot):
          return dot.radius
      def get_color(self, dot):
          if dot.radius == 1:
            return self.naturegradient1.get_color(dot.age)
          else:
            return self.naturegradient2.get_color(dot.age)
      def update_speed(self, dot, timediff):
          dot.xs = math.sin(dot.seed + dot.age * 6) * 10.0 + math.sin(dot.seed + dot.age * 4) * 15.0
          dot.ys += 5.0 * timediff

class Wind(ParticleEffect):
      normal_particles = 50
      def gen_dot(self):
          x = random() * 10 - 5.0
          y = random() * 10
          dot = Dot(x, y, 0, 0)
          dot.seed = random() * 100.0
          if random() < 0.8:
            dot.radius = 1, 0
          else:
            dot.radius = 4, 2
          return dot
      def get_radius(self, dot):
          return dot.radius
      def get_color(self, dot):
          return (0, 0, 0, 64)
      def update_speed(self, dot, timediff):
          if self.intensity > 0: mult = -1
          else: mult = 1
          dot.xs = mult * math.cos(dot.seed + dot.age * 12.0 * abs(self.intensity)) * 100.0 * abs(self.intensity)
          dot.ys = math.sin(dot.seed + dot.age * 12.0 * abs(self.intensity)) * 100.0 * abs(self.intensity)

class Energy(ParticleEffect):
      def gen_dot(self):
          dot = Dot(random() * 10.0 - 5.0, random() * 10.0 - 5.0, 0, 0)
          dot.xseed = random() * 100.0
          dot.yseed = random() * 100.0
          dot.xdiff = random() / 5.0
          light = 32 * random()
          if self.intensity > 0:
            dot.color = (255 - random() * 96, 32 + light, 32 + light, 32)
          else:
            dot.color = (32 + light, 32 + light, 255 - random() * 96, 32)
          return dot
      def get_radius(self, dot):
          return math.sin(6 * dot.age + dot.xseed) * 5.0 + 5.0, 3.0
      def get_color(self, dot):
          return dot.color
      def update_speed(self, dot, timediff):
          dot.xs = math.sin(6 * dot.age + dot.xseed * dot.xdiff) * 20.0
          dot.ys = math.sin(6 * dot.age + dot.yseed) * 20.0
          
if __name__ == "__main__":
  # TODO: broken since merging to game
  screen  = pygame.display.set_mode((500, 200)) #, pygame.FULLSCREEN)
  overlay = pygame.surface
  clock   = pygame.time.Clock()
  
  forever   = True
  intensity = 1.0
  fx = []
  fx.append(Fire(xofs = 100))
  fx.append(Wind(xofs = 200))
  fx.append(Nature(xofs = 300))
  fx.append(Energy(xofs = 400))
  while forever:
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        forever = False
      if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
          forever = False
        if event.key == pygame.K_UP:
          intensity += 0.1
        if event.key == pygame.K_DOWN:
          intensity -= 0.1
  
    # draw
    screen.fill([32, 32, 96, 255])
    for p in fx:
      p.draw(screen)
    pygame.display.update()
  
    clock.tick(45)
    for p in fx:
      p.update(intensity)
