from base import Drawable

# scenery
class Scenery(Drawable):
      pass
class Tree(Scenery):
      sprite_names = ["tree"]
      stacking     = 10
class Post(Scenery):
      sprite_names = ["post"]
      animate_stop = True
      stacking     = 15
class Hut(Scenery):
      sprite_names = ["hut"]
      stacking     = 15

class Sky(Drawable):
      from_ceiling = True
class Sun(Sky):
      distance     = 4.0
      sprite_names = ["sun"]
      base_height  = 50
      stacking     = 0
class Cloud(Sky):
      distance     = 3.0
      sprite_names = ["cloud"]
      base_height  = 150
      hover_height = 5
      stacking     = 5
      def update(self):
          # TODO: slowly flying around
          pass

## background images
class Background(Drawable):
      distance = 3.0
      stacking = 2

      def draw(self): 
          img  = self.img_list[0]
          bg_w = img.get_width() 
          bg_h = img.get_height()
          cam  = self.world.camera
          offset = (cam.pl2sc_x(0) / self.distance) % bg_w - bg_w 
          count  = int(cam.sc_w() / bg_w) + 2 
          for i in xrange(count):
            cam.graphics.blit(img, (offset + i * bg_w, cam.sc_h() - bg_h))

class BackgroundHills(Background):
      sprite_names = ["hills"]
class ForegroundGrass(Background):
      distance = 1
      stacking = 30
      sprite_names  = ["grass"]
class ForegroundOldGrass(Background):
      distance = 0.8
      stacking = 31
      sprite_names  = ["oldbiggrass"]
