#!/usr/bin/env python

import optparse
from lib.settings import settings

p = optparse.OptionParser()
p.add_option("-p", "--profile", action = "store_true", dest = "profile", help = "Run game under cProfile")
p.add_option("--tests", dest = "tests", help = "Execute specified tests and exit")
p.add_option("--all-tests", action = "store_true", dest = "all_tests", help = "Execute all tests and exit")
p.add_option("--test-repeat", dest = "test_repeat", type = "int", help = "Repeat each test N times and exit", metavar = "N")
p.add_option("--screen", dest = "screen_size", help = "Screen size WIDTHxHEIGHT", metavar = "WxH")
p.add_option("--fullscreen", dest = "fullscreen", action = "store_true", help = "Start in fullscreen")
p.add_option("--no-fullscreen", dest = "no_fullscreen", action = "store_true", help = "Start windowed")
p.set_defaults(profile = False, all_tests = False, test_repeat = 5)
(options, args) = p.parse_args()

# set settings
if options.all_tests or options.tests:
  settings.set(fullscreen = False, screen_width = 800, screen_height = 400, game_speed = 500.0, target_fps = 5.0, debug = True, graphics_provider = "none")
if options.screen_size:
  w, h = options.screen_size.split("x")
  settings.set(screen_width = int(w), screen_height = int(h))
if options.fullscreen:
  settings.set(fullscreen = True)
if options.no_fullscreen:
  settings.set(fullscreen = False)
settings.dump()
print options

# pygame
import pygame
pygame.init()
pygame.key.set_repeat(300, 150)

# game init
from lib import debug, graphics, resources, menu
resources.Resources(graphics.default_provider())

def run_tests(testspec, iterations):
    if testspec is None:
      # run all
      tests = storybook.get_set("tests")
    else:
      # run listed tests
      tests = []
      for test in testspec.split(","):
        tests.append(storybook.get(test))
    for Story in tests:
      for i in xrange(iterations):
        debug.dbg("Running %u/%u iterations of %s" % (i + 1, iterations, Story.__name__))
        w = World(Story)
        debug.dbg("Finished: %s" % (w.story.debug_info()))

# testing
if options.all_tests or options.tests:
  from lib.stories import testlevels, storybook
  from lib.world import World
  if options.profile:
    import cProfile
    cProfile.run("run_tests(options.tests, options.test_repeat)", "game.stats")
  else:
    run_tests(options.tests, options.test_repeat)
# normal game
else:
  if options.profile:
    import cProfile
    cProfile.run("menu.title_menu.run()", "game.stats")
  else:
    menu.title_menu.run()
