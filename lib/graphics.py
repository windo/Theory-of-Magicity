import pygame
from pygame.locals import *
from lib.debug import dbg

try:
  import OpenGL
  OpenGL.ERROR_CHECKING = False
  from OpenGL.GL import *
  from OpenGL.GLU import *
  use_opengl = True
except:
  use_opengl = False

global fullscreen, screen_width, screen_height
screen_width = 1024
screen_height = 768
fullscreen = FULLSCREEN

class provider:
      screen_width = screen_width
      screen_height = screen_height
      def __init__(self):
          dbg("Initializing graphics %ux%u fullscreen=%s" % (screen_width, screen_height, fullscreen))
      def center_blit(self, img, x, y):
          self.blit(img, (screen_width / 2 - img.get_width() / 2 + x, y))

class nographics_provider(provider):
      def __init__(self, *args, **kwargs):
          provider.__init__(self, *args, **kwargs)
          dbg("Using no graphics")
          self.screen = None

      Font = pygame.font.Font
      def image(self, img): return img
      def clear(self): pass
      def update(self): pass
      

class pygame_provider(provider):
      def __init__(self, *args, **kwargs):
          provider.__init__(self, *args, **kwargs)
          dbg("Using pygame (SDL)")
          flags = fullscreen | HWSURFACE | DOUBLEBUF
          self.screen = pygame.display.set_mode((screen_width, screen_height), flags)
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
          flags = fullscreen | HWSURFACE | DOUBLEBUF | OPENGL
          self.screen = pygame.display.set_mode((screen_width, screen_height), flags)
                
          glClearColor(0.0, 0.0, 0.0, 1.0)
          glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
      
          glMatrixMode(GL_PROJECTION)
          glLoadIdentity();
          gluOrtho2D(0, screen_width, screen_height, 0)
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
            rect = (0, 0, 1024, 768)
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

if use_opengl:
  default_provider = opengl_provider
else:
  default_provider = pygame_provider
