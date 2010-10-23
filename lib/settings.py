class Settings:
      def __init__(self):
          self.__dict__["s"] = {}
          # defaults
          self.set(game_name = "Theory of Magicity",
                   graphics_provider = "opengl", fullscreen = True,
                   screen_width = 1280, screen_height = 768,
                   target_fps = 45.0, game_speed = 1.0,
                   debug = False)

      def set(self, **kwargs):
          self.s.update(kwargs)

      def __getattr__(self, attr):
          return self.s[attr]
      def __setattr__(self, attr, value):
          self.__dict__["s"][attr] = value
      def dump(self):
          for key, value in self.s.iteritems():
            print "%s = %s" % (key, value)
settings = Settings()
