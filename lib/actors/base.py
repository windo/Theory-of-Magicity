import math, time
from random import random
from lib import fields
from lib.resources import Resources

class Drawable:
      """
      All game objects that have a position in the game world and may be drawn.

      This includes background images, scenery objects and characters
      """
      ## animation conf
      # animate when not moving?
      animate_stop = False
      # how often to switch frames
      anim_speed   = 1.0
      # different images for left/right direction?
      directed     = False
      # order of drawing (lower stacking is drawn first)
      stacking     = 0
      # background objects move slower than foreground
      distance     = 1.0

      ## vertical position
      # wobble up and down to this amount
      hover_height = 0.0
      # distance from edge of screen
      base_height  = 0.0
      # position is counted from upper edge of screen
      from_ceiling = False

      # if draw_debug has any effect on this actor class
      in_dev_mode    = False

      def __init__(self, world, pos):
          self.world = world
          self.id    = world.next_actor_id()
          self.rsc   = Resources() 
          # movement params
          self.pos    = pos
          self.speed  = 0.0
          self.accel  = 0.0
          # only used for the background birds ATM
          self.ypos   = 0.0
          self.yspeed = 0.0
          self.yaccel = 0.0

          # animation params
          self.start_time = time.time()
          self.rnd_time_offset = random() * 25.0
          self.direction  = -1
          self.animate    = self.animate_stop

          self.debug_me = self.in_dev_mode

          # load images
          if len(self.sprite_names):
            if self.directed:
              self.img_left  = self.rsc.sprites[self.sprite_names[0]]
              self.img_right = self.rsc.sprites[self.sprite_names[1]]
              self.img_count = len(self.img_left)
              self.img_w     = self.img_left[0].get_width()
              self.img_h     = self.img_left[0].get_height()
            else:
              self.img_list  = self.rsc.sprites[self.sprite_names[0]]
              self.img_count = len(self.img_list)
              self.img_w     = self.img_list[0].get_width()
              self.img_h     = self.img_list[0].get_height()
            self.cur_img_idx = 0
          else:
            # no image, use dummy values
            # TODO: should do something more intelligent for particle effects - they may be wider
            self.img_w = 100
            self.img_h = 100

      def destroy(self):
          # no more updates or drawing
          self.world.del_actor(self)

      # used for drawing debug information - may overload to add more information
      def __str__(self):
          return "%s(%u)" % (self.__class__.__name__, self.id)
      def __repr__(self):
          return self.__str__()
      def debug_info(self):
          return "%s pos=(%.1f, %.1f) speed=(%.1f, %.1f)" % (str(self), self.pos, self.ypos, self.speed, self.yspeed)

      def update(self):
          """
          Periodic chance do update any parameters, called regularily from the game main loop
          """
          # should overload, if anything to do
          pass

      def get_xy(self):
          """
          x - center of image
          y - top edge of image
          """
          cam = self.world.camera
          # center of image
          x = cam.pl2sc_x(self.pos) / self.distance

          # hovering in air (slightly wobbling up and down)
          if self.hover_height:
            hover = self.hover_height + self.hover_height * \
                    math.sin((time.time() + self.rnd_time_offset - self.start_time) * 2) * 0.3
          else:
            hover = 0.0
          
          # top edge
          y = cam.pl2sc_y(self.ypos) / self.distance + hover + self.base_height
          if not self.from_ceiling:
            y = cam.sc_h() - self.img_h - y

          return x, y
      def draw(self, draw_debug = False):
          """
          Draw the image on screen, called in sequence from main game loop for each actor
          """
          x, y = self.get_xy()
          cam = self.world.camera

          # do not draw off-the screen actors
          if x + self.img_w / 2 < 0 or x - self.img_w / 2 > cam.sc_w():
            return False

          # draw debugging information
          if draw_debug and self.debug_me:
            lines = self.debug_info().split("\n")
            txts  = []
            for line in lines:
              txts.append(self.rsc.fonts.debugfont.render(line, True, (255, 255, 255)))
            i = 0
            for txt in txts:
              cam.graphics.blit(txt, (x, 70 + i * 20))
              i += 1

          # do not draw/animate spriteless actors
          if len(self.sprite_names) == 0:
            # Which ones are these?
            return True

          # facing direction
          if self.directed:
            if self.direction > 0:
              imglist = self.img_right
            else:
              imglist = self.img_left
          # non-directional
          else:
            imglist = self.img_list

          # to animate or not to animate
          if self.animate:
            self.cur_img_idx = int((self.rnd_time_offset + time.time()) * self.img_count * self.anim_speed) % self.img_count
          else:
            self.cur_img_idx = 0

          # actual drawing
          img = imglist[self.cur_img_idx]
          cam.graphics.blit(img, (x - self.img_w / 2, y))

          return True

class Actor(Drawable):
      """
      Game object that moves around, may have health and a controlling class
      """
      # animation params
      directed = True

      ## movement params
      const_speed = 0.0
      const_accel = 0.0
      # if false, no magic field effects are calculated
      feel_magic  = True

      ## sounds
      # sounds created during movement
      snd_move     = []
      # sounds to make upon death
      snd_death    = []
      # TODO: idle sounds, creation sounds?

      # char attributes
      initial_hp     = 100.0
      regeneration   = 0.5  # hp/sec
      initial_energy = 10.0 # magic energy
      
      # controller class (state machine or other)
      control          = None

      def __init__(self, *args):
          Drawable.__init__(self, *args)

          # field references for convenience
          self.TimeField = self.world.get_field(fields.TimeField)
          self.WindField = self.world.get_field(fields.WindField)
          self.LifeField = self.world.get_field(fields.LifeField)

          # actor clock, used to calibrate movement/damage/etc during update
          self.last_update  = self.world.get_time()
          self.last_control = self.world.get_time()
          self.timediff     = 0.0

          # used to throttle movement sound effects
          self.next_sound = 0.0

          # character params
          self.hp           = self.initial_hp
          self.magic_energy = self.initial_energy
          # manages the magic particles and energy budget
          self.magic        = MagicCaster(self)
          # not yet...
          self.dead         = False

          # instantiate the controller class, if any
          if self.control:
            self.controller = self.control(self)
          else:
            self.controller = None

      def destroy(self):
          Drawable.destroy(self)
          # no more magic balls for the dead
          self.magic.release_all()

      def debug_info(self):
          desc = Drawable.debug_info(self)
          if self.controller:
            desc += "\nController: %s" % (self.controller.debug_info())
          return desc

      # play sounds - called from other parts of the class (update() for example)
      def in_range(self):
          return self.pos > self.world.camera.pl_x1() and self.pos < self.world.camera.pl_x2()
      def movement_sound(self):
          if self.snd_move and self.in_range() and self.next_sound < self.world.get_time():
            self.next_sound = self.world.get_time() + 1.0 + random()
            count = len(self.snd_move)
            sound = self.snd_move[int(random() * count)]
            self.rsc.play_sound(sound)
      def death_sound(self):
          if self.snd_death and self.in_range():
            count = len(self.snd_death)
            sound = self.snd_death[int(random() * count)]
            self.rsc.play_sound(sound)

      # moving the actor - called from self.controller or main game loop for the protagonist
      def move_left(self):
          if not self.const_accel:
            self.speed   = -self.const_speed
          else:
            self.accel   = -self.const_accel
          self.animate   = True
          self.direction = -1
          self.movement_sound()
      def move_right(self):
          if not self.const_accel:
            self.speed   = self.const_speed
          else:
            self.accel   = self.const_accel
          self.animate   = True
          self.direction = 1
          self.movement_sound()
      def stop(self):
          if not self.const_accel:
            self.speed   = 0
          else:
            self.accel   = 0
          self.animate   = self.animate_stop

      def update(self):
          """
          Update actor parameters - called from main game loop in sequence for each actor
          """
          # update actor clock
          now              = self.world.get_time()
          self.timediff    = now - self.last_update
          self.last_update = now
          
          if self.feel_magic:
            windfield = self.WindField.value(self.pos)
            timefield = self.TimeField.value(self.pos)
            lifefield = self.LifeField.value(self.pos)
            
          # update movement
          if self.const_speed or self.const_accel:
            # normal movement
            self.speed  += self.timediff * self.accel
            self.yspeed += self.timediff * self.yaccel
            # magical movement
            if self.feel_magic:
              magic_speed = windfield * 10.0
              magic_mult  = timefield
              if magic_mult > 0:
                magic_mult *= 5.0
              else:
                magic_mult *= 1.0
              magic_mult   += 1.0
            else:
              magic_speed = 0.0
              magic_mult  = 1.0
            # update position
            self.pos   += magic_mult * self.timediff * (self.speed + magic_speed)
            self.ypos  += magic_mult * self.timediff * self.yspeed
            if self.animate:
              self.movement_sound()

          # update hp
          if self.initial_hp and self.feel_magic:
            time_damage = abs(timefield)    * 10.0
            wind_damage = abs(windfield)    * 10.0
            life_damage = max(lifefield, 0) * 25.0
            self.hp -= self.timediff * (time_damage + wind_damage + life_damage)
            if self.hp < self.initial_hp:
              magic_regen = max(-lifefield, 0) * 12.5
              self.hp += self.timediff * (self.regeneration + magic_regen)
            if self.hp > self.initial_hp:
              self.hp = self.initial_hp
            # death
            if self.hp <= 0 and self.initial_hp:
              self.dead = True
              self.death_sound()
              self.destroy()

          # set magic energy
          if self.initial_energy and self.feel_magic:
            magic_mult = lifefield / 2.0 + 1.0
            self.magic_energy = magic_mult * self.initial_energy
          
          # controlled actors most likely want to do something
          if self.controller:
            if self.last_control + self.controller.control_interval < self.world.get_time():
              self.controller.update()
              self.last_control = self.world.get_time()
      
      def draw(self, draw_debug = False):
          """
          Draw the image on screen, called in sequence from main game loop for each actor
          """
          ret = Drawable.draw(self, draw_debug)

          # draw hp bar (if there is one)
          if self.initial_hp:
            x, y      = self.get_xy()
            hp_color  = (64, 255, 64)
            hp_border = (x - 15, y, 30, 3)
            hp_fill   = (x - 15, y, 30 * (self.hp / self.initial_hp), 3)
            self.world.camera.graphics.rect(hp_color, hp_border, True)
            self.world.camera.graphics.rect(hp_color, hp_fill, False)
            return True
          return ret

class MagicCaster:
      """
      Supplements an Actor

      Handles the list of magic particles controlled by an actor
      Manages how the actor influences the particles
      Manages the actor's magic energy budget (never overuse)
      """
      magic_distance = 5.0

      def __init__(self, actor):
          self.actor   = actor
          self.used    = 0.0
          self.affects = {}

      # called by controllers
      # manage controlled particles list
      def new(self, particletype):
          """
          make a new particle and control it
          """
          # make a new particle
          pos = self.actor.pos + self.actor.direction * self.magic_distance
          particle = self.actor.world.new_actor(particletype, pos)
          # register to influence it [speed, mult]
          self.affects[particle] = [0.0, 1.0]
          particle.affect(self)
          # make sure there is enough magic energy
          self.balance_energy()
          # return it to the caller
          return particle
      def capture(self, particle):
          """
          add to the list of controlled particles
          """
          if not self.affects.has_key(particle):
            self.affects[particle] = [0.0, 0.0]
            particle.affect(self)
      def release(self, particle):
          """
          cease controlling a particle
          """
          if self.affects.has_key(particle):
            del self.affects[particle]
            particle.release(self)
      def release_all(self):
          """
          release all particles
          """
          for particle in self.affects.keys():
            self.release(particle)

      # affect controlled particles
      def move(self, particle, set = False, diff = False):
          return self.change(particle, 0, set, diff)
      def power(self, particle, set = False, diff = False):
          return self.change(particle, 1, set, diff)
      def change(self, particle, key, set, diff):
          if self.affects.has_key(particle):
            if set is not False:
              self.affects[particle][key] = set
            elif diff is not False:
              self.affects[particle][key] += diff
            else:
              return self.affects[particle][key]
            self.balance_energy()
          if not (set or diff):
            return 0.0

      def energy(self):
          return self.actor.magic_energy
      def balance_energy(self):
          """
          go over the list of affected particles and make sure we stay within
          the energy consumption limit
          """
          used = 0.0
          for speed, power in self.affects.values():
            used += abs(speed) + abs(power)
          if used > self.energy():
            ratio = self.energy() / used
            for affect in self.affects.keys():
              speed, power = self.affects[affect]
              speed *= ratio
              power *= ratio
              self.affects[affect] = [speed, power]
            corrected = 0.0
            for speed, power in self.affects.values():
              corrected += abs(speed) + abs(power)

      # called by particles
      def affect_particle(self, particle):
          return self.affects[particle]
      def notify_destroy(self, particle):
          if self.affects.has_key(particle):
            del self.affects[particle]

## background images
class Background(Drawable):
      distance = 3.0
      stacking = 2

      def draw(self, draw_debug = False): 
          img  = self.img_list[0]
          bg_w = img.get_width() 
          bg_h = img.get_height()
          cam  = self.world.camera
          offset = (cam.pl2sc_x(0) / self.distance) % bg_w - bg_w 
          count  = int(cam.sc_w() / bg_w) + 2 
          for i in xrange(count):
            cam.graphics.blit(img, (offset + i * bg_w, cam.sc_h() - bg_h))
          return True

# controllers
class Controller:
      """
      An actor may have a controller that moves it around
      """
      control_interval = 0.1
      def __init__(self, puppet):
          self.puppet = puppet
      def __str__(self):
          return "%s" % (self.__class__.__name__)
      def debug_info(self):
          return "%s" % (str(self))
      def update(self):
          pass

class FSMController(Controller):
      """
      Container for finite state machines
      """
      states = [ "idle" ]
      start_state = "idle"

      class InvalidState(Exception):
            def __init__(self, state):
                self.state = state
            def __str__(self):
                return "Invalid state change to: %s" % (self.state)

      def __init__(self, puppet):
          Controller.__init__(self, puppet)
          self.state   = False
          self.set_state(self.start_state)
      def debug_info(self):
          return "%s ['%s' %.1fs]" % (Controller.debug_info(self), self.state, self.state_time())

      def set_state(self, newstate):
          if not newstate in self.states:
            raise self.InvalidState(newstate)
          if newstate != self.state:
            self.state       = newstate
            self.state_start = self.puppet.world.get_time()
            self.action_time = 0.0

      def state_time(self):
          return self.puppet.world.get_time() - self.state_start
      def time_passed(self, duration, rand = 0.0):
          passed = self.puppet.world.get_time() - self.action_time
          if passed > duration + rand * random():
            self.action_time = self.puppet.world.get_time()
            return True
          else:
            return False

      def update(self):
          self.state_change()
          self.state_action()
      def state_change(self):
          """
          Must be overloaded to switch states as neccessary
          """
          pass
      def state_action(self):
          """
          Must be overloaded to take action based on the state
          """
          pass

