#!/usr/bin/python

# pygame
import pygame
pygame.init()
pygame.key.set_repeat(300, 150)

import optparse

if __name__ == "__main__":
   p = optparse.OptionParser()
   p.add_option("-p", "--profile", action = "store_true", dest = "profile", help = "Run game under cProfile")
   p.add_option("--tests", dest = "tests", help = "Execute specified tests and exit")
   p.add_option("--all-tests", action = "store_true", dest = "all_tests", help = "Execute all tests and exit")
   p.add_option("--test-repeat", dest = "test_repeat", help = "Repeat each test N times and exit", metavar = "N")
   p.add_option("--screen", dest = "screen_size", help = "Screen size WIDTHxHEIGHT", metavar = "WxH")
   p.add_option("--fullscreen", dest = "fullscreen", action = "store_true", help = "Start in fullscreen")
   p.add_option("--no-fullscreen", dest = "no_fullscreen", action = "store_true", help = "Start windowed")
   p.set_defaults(profile = False, all_tests = False, test_repeat = 5)
   (options, args) = p.parse_args()
   
   from lib.settings import settings

   # set settings
   if options.all_tests or options.tests:
     settings.set(fullscreen = False, screen_width = 800, screen_height = 400, game_speed = 100.0, target_fps = 5.0, debug = True)
   if options.screen_size:
     w, h = options.screen_size.split("x")
     settings.set(screen_width = int(w), screen_height = int(h))
   if options.fullscreen:
     settings.set(fullscreen = True)
   if options.no_fullscreen:
     settings.set(fullscreen = False)
   settings.dump()

   from lib import debug, graphics, resources, menu
   resources.Resources(graphics.default_provider())

   if options.profile:
     import cProfile
     cProfile.run("menu.title_menu.run()", "game.stats")
   # testing
   elif options.all_tests:
     from lib.stories import testlevels, storybook
     from lib.world import World
     Stories = storybook.get_set("tests")
     for Story in Stories:
       for i in xrange(int(options.test_repeat)):
         w = World(Story)
         debug.dbg("Finished test: %s" % (w.story.debug_info()))
   elif options.tests:
     from lib.stories import testlevels, storybook
     from lib.world import World
     tests = options.tests.split(",")
     for test in tests:
       Story = storybook.get(test)
       for i in xrange(int(options.test_repeat)):
         w = World(Story)
         debug.dbg("Finished test: %s" % (w.story.debug_info()))
   # normal game
   else:
     menu.title_menu.run()
