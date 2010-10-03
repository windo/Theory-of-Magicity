import sys, re, time, string

class DrawDebug:
      """
      Handle debugging information on screen
      """
      line_height = 14
      char_width = 8
      base_x = 10
      base_y = 50
      margin = 10

      def __init__(self):
          # hack to avoid circular imports
          from lib.resources import Resources
          self.clear_allocations()
          self.rsc = Resources()
      
      def allocate_space(self, text):
          """
          Keep track of next potential free coordinate to fit a message are
          Try create rows of message areas:
           * First - allocate columns, tracking max message width
           * If row is full, start filling a new row
          """
          # message are size
          lines = text.split("\n")
          longest = max([len(l) for l in lines])
          width = longest * self.char_width
          height = len(lines) * self.line_height

          # try to fit to the row
          if self.alloc_y + height < self.rsc.graphics.screen_height - self.base_y:
            if width > self.row_width:
              self.row_width = width
            pos = (self.alloc_x, self.alloc_y)
            self.alloc_y += height + self.margin
          # full, create a new row
          else:
            self.alloc_x += self.row_width + self.margin
            pos = (self.alloc_x, 0)
            self.alloc_y = height + self.margin
            self.row_width = width
          # return actual coordinates
          x, y = pos
          return (x + self.base_x, y + self.base_y)
      def clear_allocations(self):
          self.alloc_x = 0
          self.alloc_y = 0
          self.row_width = 0

      def draw(self, text, x, y, black = False):
          lines = text.split("\n")
          line_imgs = []
          for line in lines:
            line_imgs.append(self.rsc.fonts.debugfont.render(line, True, (255, 255, 255)))
          for i in xrange(len(line_imgs)):
            img = line_imgs[i]
            txt_y = y + i * self.line_height
            if black:
              self.rsc.graphics.fill((0,0,0), (x, txt_y, img.get_width(), img.get_height()))
            self.rsc.graphics.blit(img, (x, txt_y))
          return txt_y + self.line_height

      def draw_msg(self, text, obj_x, obj_y):
          # allocate space and draw message
          text = string.rstrip(text)
          x, y = self.allocate_space(text)
          bottom = self.draw(text, x, y)
          # draw a line
          start = (x + self.margin, bottom)
          end = (obj_x, obj_y)
          self.rsc.graphics.line(start, end, (255, 255, 255))

      def draw_stats(self, stats):
          self.draw(stats, 5, 5, black = True)

class RateLimit:
      """
      Ratelimiter used for updating debug information
      """
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
          self.rl = RateLimit(0.1, initial_estimate = 10.0)

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
      e = 0.95
      def __init__(self):
          self.start()
          self.value = 0.0
      def __str__(self):
          return "%.3f" % (self.get())
      def start(self):
          self.start_time = time.time()
          self.end_time = self.start_time
      def end(self):
          self.end_time = time.time()
          value = (self.end_time - self.start_time) * 1000.0
          self.value = self.value * self.e + value * (1 - self.e)

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
