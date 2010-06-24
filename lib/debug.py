import sys, re
import time

global dbg_list, debug_all
debug_list = [
              'lib.graphics',
              'lib.actors.planner',
             ]
debug_all = True

def dbg(message):
    # (<frame object at 0x1ea90e0>, 'lib/debug.py', 19, 'function', ['contents of line\n'], 0)
    frame = sys._getframe(1)
    module_name = frame.f_globals['__name__']
    if debug_all or module_name in debug_list:
      try:
        class_name = frame.f_locals['self'].__class__.__name__
      except:
        class_name = "no_class"
      func_name   = frame.f_code.co_name

      print "%-16s %-25s %-32s %s" % (time.time(), module_name, "%s::%s()" % (class_name, func_name), message)

#def dbg(message): return
