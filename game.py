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

      def run_test(self, Story):
          w = world.World(self.graphics, Story, target_fps = 10.0, game_speed = 100.0)
          debug.dbg("Finished test: %s" % (w.story))

import optparse

if __name__ == "__main__":
   p = optparse.OptionParser()
   p.add_option("-p", "--profile", action = "store_true", dest = "profile", help = "Run game under cProfile")
   p.add_option("--tests", dest = "tests", help = "Execute specified tests and exit")
   p.add_option("--all-tests", action = "store_true", dest = "all_tests", help = "Execute all tests and exit")
   p.add_option("--test-repeat", dest = "test_repeat", help = "Repeat each test N times and exit", metavar = "N")
   p.set_defaults(profile = False, all_tests = False, test_repeat = 5)
   (options, args) = p.parse_args()

   if options.all_tests or options.tests:
     graphics.fullscreen = False
     graphics.screen_width = 800
     graphics.screen_height = 400

   g = Game()
   if options.profile:
     import cProfile
     cProfile.run("g.title_screen()", "game.stats")
   # testing
   elif options.all_tests:
     Stories = stories.storybook.get_set("tests")
     for Story in Stories:
       for i in xrange(int(options.test_repeat)):
         g.run_test(Story)
   elif options.tests:
     tests = options.tests.split(",")
     for test in tests:
       Story = stories.storybook.get(test)
       for i in xrange(int(options.test_repeat)):
         g.run_test(Story)
   # normal game
   else:
     g.title_screen()
