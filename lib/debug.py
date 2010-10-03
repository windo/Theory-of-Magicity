import sys, re
import time

class RateLimit:
      def __init__(self, min_int, exp = 0.95, initial_relax = 1.0, initial_estimate = None):
          # current interval estimate
          self.est_int = initial_estimate
          # minimum allowed interval
          self.min_int = min_int
          # last logged message time
          self.last_time = time.time()
          # count of messages dropped in sequence
          self.dropped = 0
          # exponent for moving average
          self.exp = exp
          # inflate initial estimate (based on the first hit)
          self.initial_relax = initial_relax

      def check(self):
          """
          Check if this event should be allowed
          """
          # this interval
          now = time.time()
          timediff = now - self.last_time
          # on first attempt, set an inflated estimate
          if self.est_int is None:
            self.est_int = timediff * self.initial_relax
          # calculate what the new estimate would be
          new_int = self.est_int * self.exp + timediff * (1 - self.exp)
          if new_int >= self.min_int:
            # accept the event
            self.est_int = new_int
            self.last_time = now
            if self.dropped > 0:
              self.dropped = 0
            return True
          else:
            # drop the event
            self.dropped += 1
            return False

class Debug:
      """
      Print debugging messages
      """
      def __init__(self, debug_list, debug_all = False):
          # list of modules to print
          self.debug_list = debug_list
          # whether to ignore the list and just print everything
          self.debug_all = debug_all
          # ratelimiting
          self.rl = RateLimit(0.2, initial_estimate = 10.0)

      def debug(self, message):
          # ratelimit
          if not self.rl.check():
            return
          # get caller information
          frame = sys._getframe(1)
          module_name = frame.f_globals['__name__']
          # check filter
          if self.debug_all or (module_name in self.debug_list):
            # more information
            try:
              class_name = frame.f_locals['self'].__class__.__name__
            except:
              class_name = "<module>"
            func_name = frame.f_code.co_name
            
            # print the message
            ts = time.strftime("%H:%M:%S")
            origin = "%s::%s::%s()" % (module_name, class_name, func_name)
            print "%-8s %-40s %s" % (ts, origin, message)

# shared debugger object
debugger = Debug([], debug_all = True)
dbg = debugger.debug

## statistics ##

class Stat:
      """
      Numeric statistic type
      """
      value_type = float
      unit = ""
      def __str__(self): return "%.3f" % (self.get())
      def __add__(self, other): return self.value + self.value_type(other)
      def __sub__(self, other): return self.value - self.value_type(other)
      def __mul__(self, other): return self.value * self.value_type(other)
      def __div__(self, other): return self.value / self.value_type(other)
      def __int__(self): return int(self.value)
      def __float__(self): return float(self.value)
      def __coerce__(self, other): return (self.value, self.value_type(other))
      def get(self): return self.value_type(self.value)

class Counter(Stat):
      value_type = int
      def __init__(self):
          self.value = 0
      def count(self, value = 1):
          self.value += value

class RateCounter(Stat):
      unit = "/s"
      def __init__(self):
          self.value = 0
          self.items = []
      def count(self):
          now = time.time()
          self.items.append(now)
          while len(self.items) > 0 and self.items[0] < now - 1.0:
            self.items.pop(0)
          self.value = len(self.items)

class Value(Stat):
      def __init__(self):
          self.value = 0
      def set(self, value):
          self.value = value

class AvgValue(Stat):
      e = 0.95
      def __init__(self):
          self.value = None
      def set(self, value):
          if self.value is None:
            self.value = value
          else:
            self.value = self.e * self.value + (1 - self.e) * value

class Timer(Stat):
      unit = "ms"
      def __init__(self):
          self.start()
      def __str__(self):
          return "%.3f" % (self.get())
      def start(self):
          self.start_time = time.time()
          self.end_time = self.start_time
          self.value = 0
      def end(self):
          self.end_time = time.time()
          self.value = (self.end_time - self.start_time) * 1000

class StatSet:
      """
      Container for set(s) of statistics
      """
      def __init__(self, name = "Statistics"):
          self.name = name
          self.items = {}
      def add(self, stat_type, *ilist):
          for key in ilist:
            self.items[key] = stat_type()
      def __getattr__(self, key):
          return self.items[key]

      def dump(self):
          """
          Write out all the statistics in the set
          """
          stats = "%s:\n" % (self.name)
          keys = self.items.keys()
          keys.sort()
          for key in keys:
            value = self.items[key]
            stats += "%s = %s %s\n" % (key, value, value.unit)
          dbg(stats[:-1])
