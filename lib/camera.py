import time
from actors import Actor

class Camera:
      """
      Viewport/scale to use for translating in-game coordinates to screen coordinates
      and vice versa
      """
      def __init__(self, graphics, plane):
          """
          view is (width, height) - input/output scale
          plane is (x1, y1, x2, y2) - the MagicField area to fit in the view
          """
          # screen / plane
          self.graphics = graphics

          self.view   = [graphics.screen_width, graphics.screen_height]
          self.plane  = list(plane)
          self.recalculate()
          # camera
          self.anchor    = None
          self.pan       = False # smooth scroll
          self.find_time = 0.5   # seconds
          self.pan_speed = 50.0  # pos/sec
          self.last_time = time.time()

      def recalculate(self):
          view_w, view_h = self.view
          plane_x1, plane_x2, plane_y1, plane_y2 = self.plane
          plane_w = plane_x2 - plane_x1
          plane_h = plane_y2 - plane_y1
          # multiplier to get plane coordinates from view coordinates
          self.mult_x = float(plane_w) / float(view_w)
          self.mult_y = float(plane_h) / float(view_h)
          # offset to apply to plane coordinates
          self.offset_x = plane_x1
          self.offset_y = plane_y1

      def pl_x1(self): return self.plane[0]
      def pl_x2(self): return self.plane[1]
      def pl_y1(self): return self.plane[2]
      def pl_y2(self): return self.plane[3]
      def pl_w(self): return self.plane[1] - self.plane[0]
      def sc_w(self): return self.view[0]
      def sc_h(self): return self.view[1]

      def sc2pl_x(self, x):
          return x * self.mult_x + self.offset_x
      def sc2pl_y(self, y):
          return y * self.mult_y + self.offset_y
      def pl2sc_x(self, x):
          return (x - self.offset_x) / self.mult_x
      def pl2sc_y(self, y):
          return (y - self.offset_y) / self.mult_y

      # camera stuff
      def get_center_x(self):
          return self.plane[0] + float(self.plane[1] - self.plane[0]) / 2.0
      def move_x(self, x):
          self.offset_x += x
          self.plane[0] += x
          self.plane[1] += x
      def set_x(self, x):
          self.anchor = None
          diff = x - self.get_center_x()
          self.move_x(diff)

      def pan_x(self, x):
          if self.anchor is None:
            self.follow(self.offset_x + x)
          elif isinstance(self.anchor, Actor):
            self.follow(self.anchor.pos + x)
          else:
            self.follow(self.anchor + x)

      def goto(self, anchor):
          self.anchor = None
          if isinstance(anchor, Actor):
            self.set_x(anchor.pos)
          else:
            self.set_x(anchor)
      def follow(self, anchor, immediate = False, pan = False):
          self.anchor = anchor
          self.pan    = pan
          if immediate and anchor is not None:
            self.goto(anchor)
      def update(self):
          # passed time
          timediff = min(time.time() - self.last_time, 0.1)
          self.last_time = time.time()
          # noone to follow?
          if self.anchor is None:
            return
          # follow
          if isinstance(self.anchor, Actor):
            dst  = self.anchor.pos
            # TODO: should use real movement speed
            speeddiff = self.anchor.speed * 5.0
            diff = speeddiff
            # not too far away
            maxdiff = self.pl_w() / 3
            # focus on magic balls
            if self.anchor.magic and self.anchor.magic.affects:
              balldiff = 0.0
              for ball in self.anchor.magic.affects.keys():
                d = (ball.pos - self.anchor.pos) / 2
                if d > maxdiff: d = maxdiff
                elif d < -maxdiff: d = -maxdiff
                balldiff += d
              balldiff /= len(self.anchor.magic.affects)
              diff += balldiff
            if diff > maxdiff: diff = maxdiff
            elif diff < -maxdiff: diff = -maxdiff
            dst += diff
          else:
            dst = self.anchor
          diff = dst - self.get_center_x()

          # movement
          if self.pan:
            # move with constant speed
            if diff > 0: dir = +1
            else:        dir = -1
            movement = dir * self.pan_speed * timediff
            # end the pan
            if abs(diff) < 10.0:
              self.pan = False
            else:
              self.move_x(movement)
          else:
            if abs(diff) < 5.0:
              const = 0.0
            elif abs(diff) < 10.0:
              const = (abs(diff) - 5.0) / 5.0
            else:
              const = 1.0
            self.move_x(diff * const * timediff / self.find_time)
