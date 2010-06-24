import pygame
from pygame.locals import *

global screen
use_opengl = False

if use_opengl:
  import OpenGL
  OpenGL.ERROR_CHECKING = False
  from OpenGL.GL import *
  from OpenGL.GLU import *

class glFont(pygame.font.Font):
      def render(self, txt, antialias, color):
          img = pygame.font.Font.render(self, txt, antialias, color)
          return glImg(img)
               
class glImg:
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
          if glDeleteTextures is not None:
            glDeleteTextures(self.__texture)
          if glDeleteLists is not None:
            glDeleteLists(self.genlist, 1)

      def get_width(self):
          return self.width
      def get_height(self):
          return self.height

def pygimage(img):
    return img

def glinit(height, width):
    flags  = FULLSCREEN | HWSURFACE | DOUBLEBUF | OPENGL
    screen = pygame.display.set_mode((height, width), flags)
          
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity();
    gluOrtho2D(0, height, width, 0)
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    return screen
def pyginit(height, width):
    global screen
    flags  = FULLSCREEN | HWSURFACE | DOUBLEBUF
    screen = pygame.display.set_mode((height, width), flags)
    screen.fill((0, 0, 0, 255))
    return screen

def glclear():
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    glLoadIdentity() 
def pygclear():
    screen.fill((0, 0, 0, 255))

def glupdate():
    glFlush()
    pygame.display.flip()
def pygupdate():
    pygame.display.flip()

def glblit(img, coords):
    glLoadIdentity()
    glTranslate(coords[0], coords[1], 0)
    glCallList(img.genlist)
def pygblit(img, coords):
    screen.blit(img, coords)

def glrect(color, rect, fill):
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
def pygrect(color, rect, fill):
    if fill: width = 0
    else: width = 1
    pygame.draw.rect(screen, color, rect, width)

def glfill(color, rect = None):
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
def pygfill(color, rect = None):
    if rect:
      screen.fill(color, rect)
    else:
      screen.fill(color)


if use_opengl:
  init_screen = glinit

  image = glImg
  blit = glblit
  fill = glfill
  rect = glrect

  clear  = glclear
  update = glupdate

  Font = glFont
else:
  init_screen = pyginit

  image = pygimage
  blit = pygblit
  fill = pygfill
  rect = pygrect

  clear  = pygclear
  update = pygupdate
  
  Font = pygame.font.Font
