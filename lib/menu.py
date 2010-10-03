import types
from lib.resources import Resources
from lib import stories
from lib.world import World

import pygame
from pygame.locals import *

class ExitAction:
      pass

class MenuItem:
      def __init__(self, menu, action, seq, txt = None):
          self.menu = menu
          self.action = action
          self.seq = seq
          self.pos = 150 + 72 * self.seq

          if self.is_exit(action):
            self.text = txt or "Exit Menu"
          elif self.is_story(action):
            self.text = action.story_name()
          elif self.is_menu(action):
            self.text = action.title

      def gen_img(self):
          """
          Separate function on menu initialization due to fucked up resource loading scheme
          """
          self.img_idle = self.menu.rsc.fonts.smallgoth.render(self.text, True, (64, 64, 64))
          self.img_sel = self.menu.rsc.fonts.smallgoth.render(self.text, True, (192, 192, 192))

      def is_exit(self, action):
          return isinstance(action, ExitAction)
      def is_story(self, action):
          return type(action) == types.ClassType and issubclass(action, stories.Story)
      def is_menu(self, action):
          return isinstance(action, Menu)

      def run(self):
          action = self.action
          if self.is_exit(action):
            self.menu.active = False
          elif self.is_story(action):
            World(self.menu.rsc.graphics, action)
            self.menu.rsc.set_music("happytheme")
          elif self.is_menu(action):
            action.run()

class Menu:
      def __init__(self, title):
          self.cur_seq = 0
          self.items = []
          self.title = title
          self.rsc = Resources()

      def add(self, action, txt = None):
          self.items.append(MenuItem(self, action, len(self.items), txt))

      def run(self):
          rsc = self.rsc
          # loop variables
          self.active = True
          select = 0

          # interesting music
          rsc.set_music("happytheme")

          # text
          title       = rsc.fonts.biggoth.render(self.title, True, (192, 64, 32))
          titleshadow = rsc.fonts.biggoth.render(self.title, True, (48, 48, 48))

          # bg
          background = rsc.get_spritelist("title-bg")[0]

          for item in self.items:
            item.gen_img()

          while self.active:
            # graphics
            rsc.graphics.blit(background, (0, 0))
            rsc.graphics.center_blit(titleshadow, 5, 25)
            rsc.graphics.center_blit(title, 0, 20)
            # menu
            for item in self.items:
              rsc.graphics.center_blit(item.seq == select and item.img_sel or item.img_idle, 0, item.pos)
            # set on screen
            rsc.graphics.update()

            # events
            for event in pygame.event.get():
              if event.type == QUIT:
                self.forever = False

              if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                  self.active = False
                if event.key == K_RETURN or event.key == K_SPACE:
                  self.items[select].run()
                elif event.key == K_UP:
                  select -= 1
                elif event.key == K_DOWN:
                  select += 1

              elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                  self.items[select].run()

              elif event.type == MOUSEMOTION:
                # selection with mouse
                x, y = event.pos
                center = rsc.graphics.screen_width / 2
                for item in self.items:
                  ofs = item.img_idle.get_width() / 2
                  if center - ofs < x < center + ofs:
                    if item.pos < y < item.pos + item.img_idle.get_height():
                      select = item.seq

            # stay in menu
            if select == len(self.items):
              select = 0
            elif select < 0:
              select = len(self.items) - 1

sb = stories.storybook
m = story_menu = Menu("Campaign")
m.add(sb.get("campaign.Shepherd"))
m.add(sb.get("campaign.Massacre"))
m.add(sb.get("campaign.Blockade"))
m.add(sb.get("campaign.Siege"))
m.add(ExitAction(), "Return")

m = demo_menu = Menu("Demo")
for t in sb.get_set("demos"):
  m.add(t)
m.add(ExitAction(), "Return")

m = test_menu = Menu("Tests")
for t in sb.get_set("tests"):
  m.add(t)
m.add(ExitAction(), "Return")

m = title_menu = Menu("Theory of Magicity")
m.add(story_menu)
m.add(demo_menu)
m.add(test_menu)
m.add(ExitAction(), "Exit Game")
