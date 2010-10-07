import pygame
from lib.debug import dbg

class FileNotFound(Exception):
      def __init__(self, name):
          self.name = name
      def __str__(self):
          return "Resourceloader did not find: %s" % (self.name) 

class Resourcelist(dict):
      def __getattr__(self, name):
          return self[name]

class Resources:
      """
      Load images and divide them to separate surfaces
      Load fonts
      Load sounds
      """
      sprites = Resourcelist()
      images = Resourcelist()
      sounds = Resourcelist()
      fonts = Resourcelist()
      graphics = None

      def __init__(self, graphics = None):
          # first invocation should pass in graphics provider
          if graphics is not None and self.graphics is None:
            self.__class__.graphics = graphics
          else:
            return

          if self.graphics is None:
            raise Exception()

          dbg("Loading resources")
          # load fonts
          self.font("biggoth", "Deutsch.ttf", 104)
          self.font("smallgoth", "Deutsch.ttf", 56)
          self.font("textfont", "angltrr.ttf", 20)
          self.font("debugfont", "Anonymous Pro.ttf", 12)

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

          self.sprite("title-bg", "title-bg", resize = (self.graphics.screen_width, self.graphics.screen_height))

          # load sounds
          self.sound("cry", "cape1", "cape2", "step")
          self.sound("beep1", "beep2", "jump")
          self.sound("moan1", "moan2", "crackle1", "crackle2")
          self.sound("wind1", "wind2", "wind3", volume = 0.01)

      def sprite(self, name, listname = False, width = False, start = 0, to = False, flip = False, resize = False):
          # load the file, if not already loaded
          if not self.images.has_key(name):
            self.images[name] = pygame.image.load("img/%s.png" % (name))
          img = self.images[name]

          # make an image list as well?
          if listname and not self.sprites.has_key(listname):
            if not width:
              width = img.get_width()
            # use all subsurfaces?
            if not to:
              to = int(img.get_width() / width)
            self.sprites[listname] = []
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
          img = self.graphics.image(img)
          self.sprites[listname].append(img)
          return img

      def get_sprite(self, name):
          if name in self.images.keys():
            return self.images[name]
          else:
            raise FileNotFound(name)
      def get_spritelist(self, name):
          if name in self.sprites.keys():
            return self.sprites[name]
          else:
            raise FileNotFound(name)

      def sound(self, *names, **kwargs):
          volume = kwargs.has_key("volume") and kwargs["volume"] or 1.0
          for name in names:
            if not self.sounds.has_key(name):
              snd = pygame.mixer.Sound("sound/%s.ogg" % (name))
              snd.set_volume(volume)
              self.sounds[name] = snd
      def play_sound(self, name):
          self.sounds[name].play()

      def set_music(self, track, volume = 0.1):
          pygame.mixer.music.load("music/%s.ogg" % (track))
          pygame.mixer.music.set_volume(volume)
          pygame.mixer.music.play(-1)

      def font(self, name, path, size):
          if not self.fonts.has_key(name):
            self.fonts[name] = self.graphics.Font("font/%s" % (path), size)
