import pygame, time

from actors import Actor
import graphics

class ResourceLoader:
      """
      Load images and divide them to separate surfaces
      Load fonts
      Load sounds
      """
      class NoImage(Exception):
            def __init__(self, name):
                self.name = name
            def __str__(self):
                return "No Image %s" % (self.name) 

      def __init__(self, screen):
          self.spritelists = {}
          self.imagelist   = {}
          self.soundlist   = {}
          self.screen      = screen

          # load fonts
          self.spritelists["dummyfont"] = []
          font = graphics.Font
          self.biggoth   = font("font/Deutsch.ttf", 104)
          self.smallgoth = font("font/Deutsch.ttf", 56)
          self.textfont  = font("font/angltrr.ttf", 20)
          self.debugfont = font("font/freesansbold.ttf", 16)

          # scaling function
          if hasattr(pygame.transform, "smoothscale"):
            self.scale = pygame.transform.smoothscale
          else:
            self.scale = pygame.transform.scale

          # load sprites
          self.sprite("dude_svg", "dude-right", 100, resize = (50, 200))
          self.sprite("dude_svg", "dude-left", 100, flip = True, resize = (50, 200))
          self.sprite("villager", "villager-right", 100, resize = (50, 200))
          self.sprite("villager", "villager-left", 100, flip = True, resize = (50, 200))
          self.sprite("rabbit_svg", "rabbit-right", 100, resize = (50, 50))
          self.sprite("rabbit_svg", "rabbit-left", 100, flip = True, resize = (50, 50))
          self.sprite("dragon_svg", "dragon-right", 100, resize = (50, 100))
          self.sprite("dragon_svg", "dragon-left", 100, flip = True, resize = (50, 100))
          self.sprite("guardian_svg", "guardian-right", 100, resize = (50, 200))
          self.sprite("guardian_svg", "guardian-left", 100, flip = True, resize = (50, 200))

          self.sprite("smallbird", "smallbird-left", 50, resize = (12, 6))
          self.sprite("smallbird", "smallbird-right", 50, flip = True, resize = (12, 6))
          self.sprite("bigbird", "bigbird-left", 100, resize = (25, 12))
          self.sprite("bigbird", "bigbird-right", 100, flip = True, resize = (25, 12))

          self.sprite("tree_svg", "tree", resize = (400, 400))
          self.sprite("sun", "sun", resize = (400, 400))
          self.sprite("cloud", "cloud")
          self.sprite("post", "post", 25)
          self.sprite("hut", "hut")

          self.sprite("hills", "hills")
          self.sprite("grass", "grass")
          self.sprite("oldbiggrass", "oldbiggrass")

          # load sounds
          self.sounds(["cry", "cape1", "cape2", "step"])
          self.sounds(["beep1", "beep2", "jump"])
          self.sounds(["moan1", "moan2", "crackle1", "crackle2"])
          self.sounds(["wind1", "wind2", "wind3"], volume = 0.01)

      def sprite(self, name, listname = False, width = False, start = 0, to = False, flip = False, resize = False):
          # load the file, if not already loaded
          if not self.imagelist.has_key(name):
            self.imagelist[name] = pygame.image.load("img/%s.png" % (name))
          img = self.imagelist[name]

          # make an image list as well?
          if listname:
            if not width:
              width = img.get_width()
            # use all subsurfaces?
            if not to:
              to = int(img.get_width() / width)
            self.spritelists[listname] = []
            for i in xrange(start, to):
              rect = [ i * width, 0, width, img.get_height() ]
              subimg = img.subsurface(rect)
              self.process_sprite(listname, subimg, flip, resize)

      def process_sprite(self, listname, img, flip, resize):
          if flip:
            img = pygame.transform.flip(img, True, False)
          if resize:
            img = self.scale(img, resize)
          # TODO: does this help at all?
          #img = img.convert_alpha(self.screen)
          img = graphics.image(img)
          self.spritelists[listname].append(img)
          return img

      def get_sprite(self, name):
          if name in self.imagelist.keys():
            return self.imagelist[name]
          else:
            raise self.NoImage(name)
      def get_spritelist(self, name):
          if name in self.spritelists.keys():
            return self.spritelists[name]
          else:
            raise self.NoImage(name)

      def sounds(self, load_sounds, volume = 1.0):
          for load_sound in load_sounds:
            self.sound(load_sound, volume)
      def sound(self, name, volume = 1.0):
          if not self.soundlist.has_key(name):
            snd = pygame.mixer.Sound("sound/%s.ogg" % (name))
            snd.set_volume(volume)
            self.soundlist[name] = snd
      def play_sound(self, name):
          self.soundlist[name].play()

      def set_music(self, track, volume = 0.1):
          pygame.mixer.music.load("music/%s.ogg" % (track))
          pygame.mixer.music.set_volume(volume)
          pygame.mixer.music.play(-1)

class View:
      """
      Viewport/scale to use for translating in-game coordinates to screen coordinates
      and vice versa
      """
      def __init__(self, screen, plane):
          """
          view is (width, height) - input/output scale
          plane is (x1, y1, x2, y2) - the MagicField area to fit in the view
          """
          # screen / plane
          self.screen = screen
          self.blit   = graphics.blit
          self.fill   = graphics.fill
          self.rect   = graphics.rect

          self.view   = [screen.get_width(), screen.get_height()]
          self.plane  = list(plane)
          self.recalculate()
          # camera
          self.anchor    = 0.0
          self.pan       = False # smooth scroll
          self.find_time = 0.5   # seconds
          self.pan_speed = 50.0  # pos/sec
          self.last_time = time.time()

      def recalculate(self):
          view_w, view_h = self.view
          plane_x1, plane_x2, plane_y1, plane_y2 = self.plane
          plane_w = plane_x2 - plane_x1
          plane_h = plane_y2 - plane_y1
          # multiplier to get plane coordinates from view coordinates
          self.mult_x = float(plane_w) / float(view_w)
          self.mult_y = float(plane_h) / float(view_h)
          # offset to apply to plane coordinates
          self.offset_x = plane_x1
          self.offset_y = plane_y1

      def pl_x1(self): return self.plane[0]
      def pl_x2(self): return self.plane[1]
      def pl_y1(self): return self.plane[2]
      def pl_y2(self): return self.plane[3]
      def pl_w(self): return self.plane[1] - self.plane[0]
      def sc_w(self): return self.view[0]
      def sc_h(self): return self.view[1]

      def sc2pl_x(self, x):
          return x * self.mult_x + self.offset_x
      def sc2pl_y(self, y):
          return y * self.mult_y + self.offset_y
      def pl2sc_x(self, x):
          return (x - self.offset_x) / self.mult_x
      def pl2sc_y(self, y):
          return (y - self.offset_y) / self.mult_y

      # camera stuff
      def get_center_x(self):
          return self.plane[0] + float(self.plane[1] - self.plane[0]) / 2.0
      def move_x(self, x):
          self.offset_x += x
          self.plane[0] += x
          self.plane[1] += x
      def set_x(self, x):
          self.anchor = False
          diff = x - self.get_center_x()
          self.move_x(diff)

      def goto(self, anchor):
          self.anchor = False
          if isinstance(anchor, Actor):
            self.set_x(anchor.pos)
          else:
            self.set_x(anchor)
      def follow(self, anchor, immediate = False, pan = False):
          self.anchor = anchor
          self.pan    = pan
          if immediate:
            self.goto(anchor)
      def update(self):
          # passed time
          timediff = min(time.time() - self.last_time, 0.1)
          self.last_time = time.time()
          # noone to follow?
          if not self.anchor:
            return
          # follow
          if isinstance(self.anchor, Actor):
            dst  = self.anchor.pos
            # TODO: should use real movement speed
            speeddiff = self.anchor.speed * 5.0
            diff = speeddiff
            # not too far away
            maxdiff = self.pl_w() / 3
            # focus on magic balls
            if self.anchor.magic and self.anchor.magic.affects:
              balldiff = 0.0
              for ball in self.anchor.magic.affects.keys():
                d = (ball.pos - self.anchor.pos) / 2
                if d > maxdiff: d = maxdiff
                elif d < -maxdiff: d = -maxdiff
                balldiff += d
              balldiff /= len(self.anchor.magic.affects)
              diff += balldiff
            if diff > maxdiff: diff = maxdiff
            elif diff < -maxdiff: diff = -maxdiff
            dst += diff
          else:
            dst = self.anchor
          diff = dst - self.get_center_x()

          # movement
          if self.pan:
            # move with constant speed
            if diff > 0: dir = +1
            else:        dir = -1
            movement = dir * self.pan_speed * timediff
            # end the pan
            if abs(diff) < 10.0:
              self.pan = False
            else:
              self.move_x(movement)
          else:
            if abs(diff) < 5.0:
              const = 0.0
            elif abs(diff) < 10.0:
              const = (abs(diff) - 5.0) / 5.0
            else:
              const = 1.0
            self.move_x(diff * const * timediff / self.find_time)

class World:
      """
      A container for all level objects (actors, fields)
      A time source
      Also keeps ResourceLoader instance reference
      """
      def __init__(self, loader, fieldtypes, view):
          self.loader      = loader
          self.view        = view
          self.time_offset = 0.0
          self.pause_start = False

          # world objects
          self.fields  = {}
          for fieldtype in fieldtypes:
            field = fieldtype(loader)
            self.fields[fieldtype] = field
          self.actors   = []
          self.actor_id = 0

      def get_time(self):
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
      def next_actor_id(self):
          id = self.actor_id
          self.actor_id += 1
          return id
      def new_actor(self, actor_class, pos):
          actor = actor_class(self, pos)
          self.actors.append(actor)
          return actor
      def del_actor(self, actor):
          self.actors.pop(self.actors.index(actor))
      def all_actors(self):
          return self.actors
      def get_actors(self, x1 = False, x2 = False, filter = False, include = False, exclude = False):
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
            if include:
              decision = False
              for klass in include:
                if isinstance(actor, klass):
                  decision = True
                  break
              if not decision:
                continue
            if exclude:
              decision = True
              for klass in exclude:
                if isinstance(actor, klass):
                  decision = False
                  break
              if not decision:
                continue

            ret.append(actor)
          return ret
      def sort_actors(self):
          self.actors.sort(lambda x, y: cmp(x.stacking, y.stacking) or cmp(x.pos, y.pos))

      # field management
      def get_field(self, fieldtype):
          return self.fields[fieldtype]
      def all_fields(self):
          return self.fields.values()
