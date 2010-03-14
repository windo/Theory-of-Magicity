import pygame
from OpenGL.GL import *
from OpenGL.GLU import *

def rect(color, rect, fill):
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
          glDeleteTextures(self.__texture);
          glDeleteLists(self.genlist, 1)

      def get_width(self):
          return self.width
      def get_height(self):
          return self.height
