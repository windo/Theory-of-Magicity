#!/usr/bin/python

import time, os, sys, math
from random import random

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
	    raise NoImage(name)

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

class Actor:
      # misc conf
      const_speed    = 0.0
      const_accel    = 0.0
      magic_distance = 5.0
      initial_health = 100

      # animation conf
      anim_speed   = 1.0
      hover_height = 0.0
      directed     = True
      def __init__(self, pos):
          # movement params
          self.speed  = 0.0
	  self.accel  = 0.0
	  self.pos    = pos

	  # animation params
	  self.direction = -1
	  self.moving    = False

	  # character params
	  self.magic = False
	  self.hp    = self.initial_health

	  # load images
	  if self.directed:
	    self.img_left  = sprites.get(self.sprite_names[0])
	    self.img_right = sprites.get(self.sprite_names[1])
	    self.image_count         = len(self.img_left)
	  else:
	    self.img_list  = sprites.get(self.sprite_names[0])
	    self.image_count         = len(self.img_list)
	  self.current_image_index = 0

      # moving the actor
      def move_left(self):
          if not self.const_accel:
            self.speed   = -self.const_speed
	  else:
	    self.accel   = -self.const_accel
	  self.moving    = True
	  self.direction = -1
      def move_right(self):
          if not self.const_accel:
	    self.speed   = self.const_speed
	  else:
	    self.accel   = self.const_accel
	  self.moving    = True
	  self.direction = 1
      def stop(self):
          if not self.const_accel:
            self.speed   = 0
	  else:
	    self.accel   = 0
	  self.moving    = False

      # doing magic
      def magic_start(self, particle):
          if self.magic:
	    self.magic.release()
          self.magic = particle(self.pos + self.direction * self.magic_distance)
	  return self.magic
      def magic_release(self):
          if self.magic:
	    self.magic.release()
            self.magic = False
      def magic_move_right(self):
          if self.magic:
	    self.magic.move_right()
      def magic_move_left(self):
          if self.magic:
	    self.magic.move_left()
      def magic_stop(self):
          if self.magic:
	    self.magic.stop()

      # called every frame
      def update(self):
          if self.accel:
	    self.speed += self.accel
          if self.speed:
            self.pos  += self.speed * fields.get(OilField).v(self.pos)
      
      # draw image, either left-right directed or unidirectional
      def draw(self, screen):
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
	  if self.moving:
	    self.current_image_index = int(time.time() * self.image_count * self.anim_speed) % self.image_count
	  else:
	    self.current_image_index = 0

	  # hovering in air (particles)
	  if self.hover_height:
	    hover = self.hover_height + self.hover_height * math.sin(time.time() * 2) * 0.3
	  else:
	    hover = 0.0

          # actual drawing
	  img = imglist[self.current_image_index]
	  coords = (view.pl2sc_x(self.pos) - img.get_width() / 2, 200 - img.get_height() - hover)
          screen.blit(img, coords)

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
      def sc_value(self, pos):
          return pos, view.pl2sc_y(self.v(view.sc2pl_x(pos)))
      def draw(self, screen):
	  if self.visibility:
	    # step should be float to cover the whole range
            step = float(screen.get_width()) / float(self.drawpoints)
            for pos in xrange(self.drawpoints):
              pygame.draw.line(screen, self.color, self.sc_value(pos * step), self.sc_value((pos + 1) * step))

class MagicFields:
      def __init__(self, fieldtypes):
          self.fields = { }
	  for fieldtype in fieldtypes:
	    self.get(fieldtype)

      # Class method, store different fields in class and return them
      def get(self, fieldtype):
          if self.fields.has_key(fieldtype):
	    return self.fields[fieldtype]
	  else:
	    f = fieldtype()
	    self.fields[fieldtype] = f
	    return f
      def all(self):
          return self.fields.values()

class MagicParticle(Actor):
      const_accel  = 0.02
      anim_speed   = 3.0
      hover_height = 25.0
      directed     = False
      def __init__(self, pos):
	  Actor.__init__(self, pos)
	  self.field    = fields.get(self.fieldtype)
	  self.dev      = 5.0
	  self.mult     = 10.0
	  self.decay    = 1.0
	  self.field.add_particle(self)

      def destroy(self):
          self.field.del_particle(self)
	  actors.pop(actors.index(self))

      def release(self):
          self.decay = 0.995

      # particle params (normal distribution)
      def get_params(self):
          return self.pos, self.dev, self.mult

      def update(self):
          Actor.update(self)
	  self.mult *= self.decay
	  if self.mult < 0.1:
	    self.destroy()

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
class OilBall(MagicParticle):
      sprite_names = ["oilball"]
      fieldtype    = OilField

class Tree:
      def __init__(self, pos):
          self.pos   = pos
          self.image = sprites.get("tree1")[0]

      def draw(self, screen):
          screen.blit(self.image, [view.pl2sc_x(self.pos) - self.image.get_width() / 2, 200 - self.image.get_height()])

class Dude(Actor):
      """
      Magic-using habitant
      """
      const_speed  = 0.4
      sprite_names = ["dude-left", "dude-right"]


class Rabbit(Actor):
      const_speed  = 0.5
      anim_speed   = 2.0
      sprite_names = ["rabbit-left", "rabbit-right"]

      def update(self):
          Actor.update(self)
	  if random() < 0.05:
	    decision = int(random() * 3) % 3
	    if decision == 0:
	      self.move_left()
	    elif decision == 1:
	      self.move_right()
	    else:
	      self.stop()

class Dragon(Actor):
      const_speed  = 0.1
      sprite_names = ["dragon-left", "dragon-right"]
      def __init__(self, pos):
          Actor.__init__(self, pos)
	  self.dev   = 1.0
	  self.mult  = 2.0
	  fields.get(FireField).add_particle(self)

      def update(self):
          Actor.update(self)
	  if random() < 0.01:
	    decision = int(random() * 3) % 3
	    if decision == 0:
	      self.move_left()
	    elif decision == 1:
	      self.move_right()
	    else:
	      self.stop()

      # particle params (normal distribution)
      def get_params(self):
          return self.pos, self.dev, self.mult


pygame.init()
pygame.display.set_caption('Magic')
screensize = (1000, 200)

screen  = pygame.display.set_mode(screensize)
clock   = pygame.time.Clock()

global sprites, view, actors, fields
sprites = SpriteLoader()
sprites.load("fire.png", "fireball", 25)
sprites.load("ice.png", "iceball", 25)
sprites.load("oil.png", "oilball", 25)
sprites.load("dude.png", "dude-right", 25)
sprites.load("dude.png", "dude-left", 25, flip = True)
sprites.load("rabbit.png", "rabbit-right", 25)
sprites.load("rabbit.png", "rabbit-left", 25, flip = True)
sprites.load("dragon.png", "dragon-right", 25)
sprites.load("dragon.png", "dragon-left", 25, flip = True)
sprites.load("tree1.png", "tree1")
sprites.load("grass.png", "grass")

view    = View(screensize, (0, 0, 100, 2))
fields  = MagicFields([FireField, IceField, OilField])
tree    = Tree(50)
scenery = [tree]
dude    = Dude(10)
dragon  = Dragon(70)
actors  = [dude, dragon]
for i in xrange(10):
  rabbit = Rabbit(100 * random())
  actors.append(rabbit)


# loop
forever    = True
# calibration
lasttime   = int(time.time())
frames     = 0
lastframes = 0
# state
casting    = False
while forever:
  # center view to dude
  diff = dude.pos - view.get_center_x()
  if 30.0 > abs(diff) > 5.0:
    view.move_x(diff * 0.005)
  elif abs(diff) > 30.0:
    view.move_x(diff * 0.01)

  # draw
  day = math.sin(time.time()) + 1
  screen.fill([day * 32, 64 + day * 32, 192 + day * 32])
  for obj in scenery:
    obj.draw(screen)
  for field in fields.all():
    field.draw(screen)
  for actor in actors:
    actor.draw(screen)
  grass = sprites.get("grass")[0]
  w = grass.get_width()
  for i in xrange(view.pl2sc_x(200) / w):
    screen.blit(grass, [view.pl2sc_x(0 - 100) + i * w, 200 - grass.get_height() + 5])
  pygame.display.update()

  # handle events
  for event in pygame.event.get():
    if event.type == pygame.QUIT:
      forever = False
    
    # key events
    if event.type == pygame.KEYDOWN:
      if event.key == pygame.K_ESCAPE:
        forever = False

      elif event.key == pygame.K_LEFT:
        if not casting:
          dude.move_left()
      elif event.key == pygame.K_RIGHT:
        if not casting:
          dude.move_right()

      elif event.key == pygame.K_LSHIFT:
        casting = True
      
      elif event.key == pygame.K_z:
        if casting:
          dude.stop()
          actors.append(dude.magic_start(FireBall))
          fields.get(FireField).toggle_visibility(True)
	else:
          fields.get(FireField).toggle_visibility()
      elif event.key == pygame.K_x:
        if casting:
          dude.stop()
          actors.append(dude.magic_start(IceBall))
          fields.get(IceField).toggle_visibility(True)
	else:
          fields.get(IceField).toggle_visibility()
      elif event.key == pygame.K_c:
        if casting:
          dude.stop()
          actors.append(dude.magic_start(OilBall))
          fields.get(OilField).toggle_visibility(True)
	else:
          fields.get(OilField).toggle_visibility()

      elif event.key == pygame.K_a:
        dude.magic_move_left()
      elif event.key == pygame.K_d:
        dude.magic_move_right()

    if event.type == pygame.KEYUP:
      if event.key == pygame.K_LSHIFT:
        dude.magic_release()
        casting = False
      elif event.key == pygame.K_LEFT:
        dude.stop()
      elif event.key == pygame.K_RIGHT:
        dude.stop()

      elif event.key == pygame.K_a:
        dude.magic_stop()
      elif event.key == pygame.K_d:
        dude.magic_stop()

  # actors moving
  for actor in actors:
    actor.update()

  # calibration
  clock.tick(45)
  frames += 1
  if int(time.time()) != lasttime:
    print "FPS: %f" % (frames - lastframes)
    lasttime   = int(time.time())
    lastframes = frames


