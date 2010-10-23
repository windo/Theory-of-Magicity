import pygame
from pygame.locals import *
from lib.debug import dbg
from lib.settings import settings

try:
  import OpenGL
  OpenGL.ERROR_CHECKING = False
  from OpenGL.GL import *
  from OpenGL.GLU import *
  opengl_available = True
except:
  opengl_available = False

class provider:
      screen_width = settings.screen_width
      screen_height = settings.screen_height
      def __init__(self):
          pygame.display.set_caption(settings.game_name)
          dbg("Initializing graphics %ux%u fullscreen=%s" % \
              (settings.screen_width, settings.screen_height, settings.fullscreen))
      def center_blit(self, img, x, y):
          self.blit(img, (settings.screen_width / 2 - img.get_width() / 2 + x, y))

class nographics_provider(provider):
      def __init__(self, *args, **kwargs):
          provider.__init__(self, *args, **kwargs)
          dbg("Using no graphics")
          self.screen = None

      Font = pygame.font.Font
      def image(self, img): return img
      def dummy(self, *args, **kwargs): pass
      clear = update = fill = rect = blit = dummy
      
class pygame_provider(provider):
      def __init__(self, *args, **kwargs):
          provider.__init__(self, *args, **kwargs)
          dbg("Using pygame (SDL)")
          flags = (settings.fullscreen and FULLSCREEN or 0) | HWSURFACE | DOUBLEBUF
          dbg("Available modes: %s" % (pygame.display.list_modes(0, flags)))
          self.screen = pygame.display.set_mode((settings.screen_width, settings.screen_height), flags)
          self.screen.fill((0, 0, 0, 255))

      Font = pygame.font.Font

      def image(self, img):
          return img
      
      def clear(self):
          self.screen.fill((0, 0, 0, 255))
      
      def update(self):
          pygame.display.flip()
      
      def blit(self, img, coords):
          self.screen.blit(img, coords)
      
      def rect(self, color, rect, fill):
          if fill: width = 0
          else: width = 1
          pygame.draw.rect(self.screen, color, rect, width)
      
      def fill(self, color, rect = None):
          if rect:
            self.screen.fill(color, rect)
          else:
            self.screen.fill(color)
      def line(self, start, end, color, width = 1):
          pygame.drawline(self.screen, start, end, color, width)
      
class opengl_provider(provider):
      def __init__(self, *args, **kwargs):
          provider.__init__(self, *args, **kwargs)
          dbg("Using OpenGL")
          flags = (settings.fullscreen and FULLSCREEN or 0) | HWSURFACE | DOUBLEBUF | OPENGL
          dbg("Available modes: %s" % (pygame.display.list_modes(0, flags)))
          self.screen = pygame.display.set_mode((settings.screen_width, settings.screen_height), flags)
                
          glClearColor(0.0, 0.0, 0.0, 1.0)
          glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
      
          glMatrixMode(GL_PROJECTION)
          glLoadIdentity();
          gluOrtho2D(0, settings.screen_width, settings.screen_height, 0)
          glMatrixMode(GL_MODELVIEW)
      
          glEnable(GL_TEXTURE_2D)
          glEnable(GL_BLEND)
          glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

      class Font(pygame.font.Font):
            def render(self, txt, antialias, color):
                img = pygame.font.Font.render(self, txt, antialias, color)
                return opengl_provider.image(img)
               
      class image:
            def __init__(self, img):
                # create texture
                w, h = img.get_width(), img.get_height()
                self.width  = w
                self.height = h
      
                texdata = pygame.image.tostring(img, "RGBA", 1)
                tex = glGenTextures(1)
                self.__texture = tex
                glBindTexture(GL_TEXTURE_2D, tex)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, texdata)
          
                # create genlist
                genlist = glGenLists(1)
                glNewList(genlist, GL_COMPILE)
                glBindTexture(GL_TEXTURE_2D, tex)
                glBegin(GL_QUADS)
                glTexCoord2f(0, 1); glVertex2f(0, 0)
                glTexCoord2f(0, 0); glVertex2f(0, h)
                glTexCoord2f(1, 0); glVertex2f(w, h)
                glTexCoord2f(1, 1); glVertex2f(w, 0)
                glEnd()
                glEndList()
                self.genlist = genlist

            def __del__(self):
                try:
                  glDeleteTextures(self.__texture)
                except AttributeError:
                  pass
                except TypeError:
                  pass
                try:
                  glDeleteLists(self.genlist, 1)
                except TypeError:
                  pass
      
            def get_width(self):
                return self.width
            def get_height(self):
                return self.height

      def clear(self):
          glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
          glLoadIdentity() 

      def update(self):
          glFlush()
          pygame.display.flip()

      def blit(self, img, coords):
          glLoadIdentity()
          glTranslate(coords[0], coords[1], 0)
          glCallList(img.genlist)

      def rect(self, color, rect, fill):
          glLoadIdentity()
          glBindTexture(GL_TEXTURE_2D, 0)
          glColor3f(color[0]/255, color[1]/255, color[2]/255)
          if fill:
            glBegin(GL_QUADS)
          else:
            glBegin(GL_LINE_LOOP)
          glVertex2f(rect[0], rect[1])
          glVertex2f(rect[0] + rect[2], rect[1])
          glVertex2f(rect[0] + rect[2], rect[1] + rect[3])
          glVertex2f(rect[0], rect[1] + rect[3])
          glEnd()
          glColor4f(1.0, 1.0, 1.0, 1.0)

      def fill(self, color, rect = None):
          if rect is None:
            rect = (0, 0, settings.screen_width, settings.screen_height)
          glLoadIdentity()
          glColor3f(color[0]/255, color[1]/255, color[2]/255)
          glBindTexture(GL_TEXTURE_2D, 0)
          glBegin(GL_QUADS)
          glVertex2f(rect[0], rect[1])
          glVertex2f(rect[0] + rect[2], rect[1])
          glVertex2f(rect[0] + rect[2], rect[1] + rect[3])
          glVertex2f(rect[0], rect[1] + rect[3])
          glEnd()
          glColor4f(1.0, 1.0, 1.0, 1.0)

      def line(self, start, end, color, width = 1):
          glLoadIdentity()
          glColor3f(color[0]/255, color[1]/255, color[2]/255)
          glBindTexture(GL_TEXTURE_2D, 0)
          glBegin(GL_LINES)
          glVertex2f(*start)
          glVertex2f(*end)
          glEnd()
          glColor4f(1.0, 1.0, 1.0, 1.0)

# choose what is specified, falling back to pygame_provider
def default_provider():
    requested = settings.graphics_provider
    if requested == "opengl":
      if opengl_available:
        return opengl_provider()
      else:
        dbg("OpenGL not available, falling back to pygame")
        return pygame_provider()
    elif requested == "none":
      return nographics_provider()
    else:
      return pygame_provider()
