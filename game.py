#!/usr/bin/python

import time, sys, math, types
from random import random

# pygame
import pygame
from pygame.locals import *

# game libraries
from lib import *
from lib.stories import campaign, testlevels

class Game:
      """
      Implements title screen, menu
      Runs different levels (stories) - the main game loop
      """
      name  = "Theory of Magicity"
      def __init__(self):
          # initialize pygame
          pygame.init()
          pygame.mixer.init()
          pygame.display.set_caption(self.name)
          pygame.key.set_repeat(300, 150)
          self.clock = pygame.time.Clock()

          # screen params
          debug.dbg("Setting up graphics and resources")
          self.graphics = graphics.default_provider()
          resources.Resources(self.graphics)

      def title_screen(self):
          menu.title_menu.run()

      def run_test(self, test):
          Story = stories.storybook.get(test)
          w = world.World(self.graphics, Story, target_fps = 10.0, game_speed = 100.0)
          debug.dbg("Finished test: %s" % (w.story))

import optparse

if __name__ == "__main__":
   p = optparse.OptionParser()
   p.add_option("--profile", action = "store_true", dest = "profile")
   p.add_option("--tests", dest = "tests")
   p.set_defaults(profile = False)
   (options, args) = p.parse_args()

   g = Game()
   if options.profile:
     import cProfile
     cProfile.run("g.title_screen()", "game.stats")
   elif options.tests:
     tests = options.tests.split(",")
     graphics.fullscreen = 0
     graphics.screen_width = 800
     graphics.screen_height = 600
     for test in tests:
       g.run_test(test)
   else:
     g.title_screen()
