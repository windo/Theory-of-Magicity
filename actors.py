import pygame, math, time
from random import random

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
      # order of drawing (lower stacking is drawed first)
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
          self.world  = world
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

          # load images
          if len(self.sprite_names):
            if self.directed:
              self.img_left  = world.loader.get_spritelist(self.sprite_names[0])
              self.img_right = world.loader.get_spritelist(self.sprite_names[1])
              self.img_count = len(self.img_left)
              self.img_w     = self.img_left[0].get_width()
              self.img_h     = self.img_left[0].get_height()
            else:
              self.img_list  = world.loader.get_spritelist(self.sprite_names[0])
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
          return "%s(0x%s)" % (str(self.__class__).split(".")[1], id(self))
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
          view = self.world.view
          # center of image
          x = view.pl2sc_x(self.pos) / self.distance

          # hovering in air (slightly wobbling up and down)
          if self.hover_height:
            hover = self.hover_height + self.hover_height * \
                    math.sin((time.time() + self.rnd_time_offset - self.start_time) * 2) * 0.3
          else:
            hover = 0.0
          
          # top edge
          y = view.pl2sc_y(self.ypos) / self.distance + hover + self.base_height
          if not self.from_ceiling:
            y = view.sc_h() - self.img_h - y

          return x, y
      def draw(self, screen, draw_debug = False):
          """
          Draw the image on screen, called in sequence from main game loop for each actor
          """
          x, y = self.get_xy()

          # do not draw off-the screen actors
          if x + self.img_w / 2 < 0 or x - self.img_w / 2 > self.world.view.sc_w():
            return

          # draw debugging information
          if draw_debug and self.in_dev_mode:
            lines = self.debug_info().split("\n")
            txts  = []
            for line in lines:
              txts.append(self.world.loader.debugfont.render(line, True, (255, 255, 255)))
            i = 0
            for txt in txts:
              screen.blit(txt, (x, int(draw_debug) + 20 + i * 20))
              i += 1

          # do not draw/animate spriteless actors
          if len(self.sprite_names) == 0:
            return

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
            self.cur_img_idx = int(time.time() * self.img_count * self.anim_speed) % self.img_count
          else:
            self.cur_img_idx = 0

          # actual drawing
          img = imglist[self.cur_img_idx]
          screen.blit(img, (x - self.img_w / 2, y))

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
      control_interval = 0.05

      def __init__(self, world, pos):
          Drawable.__init__(self, world, pos)

          # field references for convenience
          self.LightField = self.world.get_field(fields.LightField)
          self.EnergyField = self.world.get_field(fields.EnergyField)
          self.EarthField = self.world.get_field(fields.EarthField)

          # actor clock, used to calibrate movement/damage/etc during update
          self.last_update  = world.get_time()
          self.last_control = world.get_time()
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
          return self.pos > self.world.view.pl_x1() and self.pos < self.world.view.pl_x2()
      def movement_sound(self):
          if self.snd_move and self.in_range() and self.next_sound < self.world.get_time():
            self.next_sound = self.world.get_time() + 1.0 + random()
            count = len(self.snd_move)
            sound = self.snd_move[int(random() * count)]
            self.world.loader.play_sound(sound)
      def death_sound(self):
          if self.snd_death and self.in_range():
            count = len(self.snd_death)
            sound = self.snd_death[int(random() * count)]
            self.world.loader.play_sound(sound)

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
            energyfield = self.EnergyField.value(self.pos)
            lightfield  = self.LightField.value(self.pos)
            earthfield  = self.EarthField.value(self.pos)
            
          # update movement
          if self.const_speed or self.const_accel:
            # normal movement
            self.speed  += self.timediff * self.accel
            self.yspeed += self.timediff * self.yaccel
            # magical movement
            if self.feel_magic:
              magic_speed = energyfield * 10.0
              magic_mult  = lightfield
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
            light_damage  = abs(lightfield)    * 10.0
            energy_damage = abs(energyfield)   * 10.0
            earth_damage  = max(earthfield, 0) * 25.0
            self.hp -= self.timediff * (light_damage + energy_damage + earth_damage)
            if self.hp < self.initial_hp:
              magic_regen = max(-earthfield, 0) * 12.5
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
            magic_mult = earthfield / 2.0 + 1.0
            self.magic_energy = magic_mult * self.initial_energy
          
          # controlled actors most likely want to do something
          if self.controller:
            if self.last_control + self.control_interval < self.world.get_time():
              self.controller.update()
              self.last_control = self.world.get_time()
      
      def draw(self, screen, draw_debug = False):
          """
          Draw the image on screen, called in sequence from main game loop for each actor
          """
          Drawable.draw(self, screen, draw_debug)

          # draw hp bar (if there is one)
          if self.initial_hp:
            x, y      = self.get_xy()
            hp_color  = (64, 255, 64)
            hp_border = (x - 15, y, 30, 3)
            hp_fill   = (x - 15, y, 30 * (self.hp / self.initial_hp), 3)
            pygame.draw.rect(screen, hp_color, hp_border, 1)
            pygame.draw.rect(screen, hp_color, hp_fill, 0)

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

import fields

## stacking rules:
# sky background - 0-4
# background     - 5-9
# scenery        - 10-14
# level objects  - 15-19
# NPCs           - 20-24
# player         - 25
# magicparticles - 26
# foreground objects - 27+

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

      def draw(self, screen, draw_debug = False): 
          img    = self.img_list[0]
          bg_w   = img.get_width() 
          bg_h   = img.get_height()
          view   = self.world.view
          offset = (view.pl2sc_x(0) / self.distance) % bg_w - bg_w 
          count  = int(view.sc_w() / bg_w) + 2 
          for i in xrange(count):
            screen.blit(img, (offset + i * bg_w, view.sc_h() - bg_h))

class BackgroundHills(Background):
      sprite_names = ["hills"]

# swarming demo
class Bird(Actor):
      animate_stop = True
      stacking     = 3
      base_height  = 0
      from_ceiling = True
      distance     = 3.0

      feel_magic   = False
      initial_hp   = 0
class SmallBird(Bird):
      sprite_names = ["smallbird-left", "smallbird-right"]
      const_speed  = 5
      const_accel  = 25
class BigBird(Bird):
      sprite_names = ["bigbird-left", "bigbird-right"]
      const_speed  = 10
      const_accel  = 15

# Characters
class Character(Actor):
      stacking = 20

class Dude(Character):
      const_speed  = 6.0
      initial_hp   = 100
      sprite_names = ["dude-left", "dude-right"]
      snd_move     = ["step", "cape1", "cape2"]
      snd_death    = ["cry"]
      stacking     = 25
      in_dev_mode  = True

class Rabbit(Character):
      const_speed  = 9.0
      anim_speed   = 2.0
      initial_hp   = 15
      regeneration = 2.0
      sprite_names = ["rabbit-left", "rabbit-right"]
      snd_move     = ["jump"]
      snd_death    = ["beep1", "beep2"]

class Dragon(Character):
      const_speed  = 2.0
      sprite_names = ["dragon-left", "dragon-right"]
      snd_move     = ["crackle1", "crackle2"]
      snd_death    = ["moan1", "moan2"]
      in_dev_mode  = True

class Guardian(Character):
      const_speed    = 1.0
      initial_hp     = 250
      regeneration   = 2.0
      initial_energy = 30.0
      sprite_names = ["guardian-left", "guardian-right"]
      in_dev_mode = True

# controllers
class Controller:
      def __init__(self, puppet):
          self.puppet = puppet
      def __str__(self):
          return "%s" % (str(self.__class__).split(".")[1])
      def debug_info(self):
          return "%s" % (str(self))
      def update(self):
          pass

class FlyingController(Controller):
      def __init__(self, *args):
          Controller.__init__(self, *args)
          self.xdiff = self.ydiff = 0.0

      def debug_info(self):
          return "%s dir=[%.1f,%.1f]" % \
                 (Controller.debug_info(self), self.xdiff, self.ydiff)
      def normalize_xy(self, x, y, sum, scale_up = True, scale_down = True):
          """
          ensure that the cumulative vector of x,y is not smaller/larger than sum
          """
          # the vector length
          real_sum = (x ** 2 + y ** 2) ** 0.5
          if real_sum == 0:
            return x, y
          # scale up/down
          mult = sum / real_sum
          if real_sum < sum and scale_up or real_sum > sum and scale_down:
            x *= mult
            y *= mult
          return x, y

      def find_offset(self):
          pass

      def update(self):
          # where to fly?
          self.find_offset()

          # face left/right
          if self.puppet.speed > 0:
            self.puppet.direction = 1
          else:
            self.puppet.direction = -1

          # accelerate
          x, y = self.normalize_xy(self.xdiff, self.ydiff, self.puppet.const_accel)
          self.puppet.accel  = x
          self.puppet.yaccel = y
          # limit speed
          x, y = self.normalize_xy(self.puppet.speed, self.puppet.yspeed, self.puppet.const_speed)
          self.puppet.speed  = x
          self.puppet.yspeed = y

class BirdFlocker(FlyingController):
      def __init__(self, *args):
          FlyingController.__init__(self, *args)
          ## flocking params
          # grand scheme
          self.weight_waypoint = 4.5
          self.weight_flock    = 5.0
          self.weight_predator = 10.0
          self.weight_bounds   = 15.0
          # in flock
          self.weight_repel = 10.0
          self.weight_group = 5.0
          # flock shape
          self.prefer_dist  = 5.0
          self.group_size   = 20.0
          self.visible_dist = 30.0
          # random flying around points
          self.ypos_upper_bound = 90.0
          self.pos_max_spread   = 1000
          self.random_waypoint()

      def debug_info(self):
          return "%s way=[%.1f,%.1f]" % \
                 (FlyingController.debug_info(self), self.xwaypoint, self.ywaypoint)

      def random_waypoint(self):
          self.xwaypoint = random() * self.pos_max_spread - (self.pos_max_spread / 2)
          self.ywaypoint = random() * self.ypos_upper_bound

      def find_offset(self):
          # calculate destination, prefer waypoint
          x, y = self.normalize_xy(self.xwaypoint - self.puppet.pos,
                                   self.ywaypoint - self.puppet.ypos,
                                   self.weight_waypoint)
          self.xdiff, self.ydiff = x, y

          # bounds
          if self.puppet.ypos > self.ypos_upper_bound:
            self.ydiff -= self.weight_bounds

          # predators
          preds = self.puppet.world.get_actors(include = [BigBird])
          pred_xdiff = pred_ydiff = 0.0
          for pred in preds:
            xdiff = pred.pos - self.puppet.pos
            ydiff = pred.ypos - self.puppet.ypos
            dist  = (xdiff ** 2 + ydiff ** 2) ** (0.5)
            if dist < self.visible_dist:
              pred_xdiff += -xdiff * (1 - dist / self.visible_dist)
              pred_ydiff += -ydiff * (1 - dist / self.visible_dist)
          if preds:
            x, y = self.normalize_xy(pred_xdiff, pred_ydiff, self.weight_predator)
            self.xdiff += x
            self.ydiff += y

          # find other birds
          neighs = self.puppet.world.get_actors(include = [SmallBird])
          # flocking
          flock_xdiff = flock_ydiff = 0.0
          for neigh in neighs:
            if neigh == self.puppet:
              continue
            xdiff = neigh.pos - self.puppet.pos
            ydiff = neigh.ypos - self.puppet.ypos
            dist  = (xdiff ** 2 + ydiff ** 2) ** (0.5)
            # repel if too close
            if dist < self.prefer_dist :
              const = (-1.0 + dist / self.prefer_dist) * self.weight_repel
            # group locally
            elif dist < self.group_size:
              const = self.weight_group * (dist - self.prefer_dist) / (self.group_size - self.prefer_dist)
            elif dist < self.visible_dist:
              const = self.weight_group - (dist - self.group_size) / (self.visible_dist - self.group_size)
            # ignore beyond sight
            else:
              const = 0.0
            flock_xdiff += const * xdiff
            flock_ydiff += const * ydiff
          if neighs:
            x, y = self.normalize_xy(flock_xdiff, flock_ydiff, self.weight_flock)
            self.xdiff += x
            self.ydiff += y

      def update(self):
          FlyingController.update(self)
          # choose a next waypoint 
          if abs(self.xwaypoint - self.puppet.pos) < 1.0 and abs(self.ywaypoint - self.puppet.ypos) < 1.0:
            self.random_waypoint()

class BirdPredator(FlyingController):
      def __init__(self, *args):
          FlyingController.__init__(self, *args)
          self.random_target()
      def debug_info(self):
          return "%s target=[%.1f,%.1f]" % \
                 (FlyingController.debug_info(self), self.target.pos, self.target.ypos)
      def random_target(self):
          birds = self.puppet.world.get_actors(include = [SmallBird])
          self.target = birds[int(random() * len(birds))]
      def find_offset(self):
          self.xdiff = self.target.pos  - self.puppet.pos
          self.ydiff = self.target.ypos - self.puppet.ypos
      def update(self):
          FlyingController.update(self)
          if abs(self.target.pos - self.puppet.pos) < 1.0 and abs(self.target.ypos - self.puppet.ypos) < 1.0:
            self.random_target()

class FSMController(Controller):
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
          pass
      def state_action(self):
          pass

class GuardianController(FSMController):
      states = [ "idle", "guarding", "walking" ]
      danger = [ Dragon ]
      def __init__(self, puppet):
          FSMController.__init__(self, puppet)
          self.target   = False
          self.shot     = False
          self.waypoint = False
      def set_waypoint(self, waypoint):
          self.waypoint = waypoint

      def debug_info(self):
          return "%s target=%s waypoint=%.3s" % \
                 (FSMController.debug_info(self), self.target, self.waypoint)

      def get_target(self):
          closest    = 75.0
          new_target = False
          dangers = self.puppet.world.get_actors(self.puppet.pos - closest, self.puppet.pos + closest, include = self.danger)
          for danger in dangers:
            dist = abs(danger.pos - self.puppet.pos)
            if dist < closest:
              closest = dist
              new_target = danger

          if new_target:
            self.target = new_target
              
      def state_change(self):
          if self.state == "idle":
            if self.time_passed(2.0):
              self.get_target()
            if self.target:
              self.set_state("guarding")
            elif self.waypoint:
              self.set_state("walking")

          elif self.state == "guarding":
            if self.target.dead or abs(self.target.pos - self.puppet.pos) > 100:
              self.target = False
              self.get_target()

            if not self.target:
              if self.shot:
                self.puppet.magic.release(self.shot)
                self.shot = False
              self.set_state("idle")

          elif self.state == "walking":
            if not self.waypoint:
              self.set_state("idle")

      def state_action(self):
          if self.state == "idle":
            pass
          elif self.state == "guarding":
            # face the direction
            if self.target.pos < self.puppet.pos:
              if self.puppet.direction > 0:
                self.puppet.move_left()
                self.puppet.stop()
            else:
              if self.puppet.direction < 0:
                self.puppet.move_right()
                self.puppet.stop()

            # block the path
            if not self.shot or self.shot.dead:
              self.shot = self.puppet.magic.new(fields.LightBall)

            if self.target.pos < self.puppet.pos:
              dest_pos = self.puppet.pos - 20.0
            else:
              dest_pos = self.puppet.pos + 20.0
            dest_value = -1.0

            # shot position
            offset = abs(self.shot.pos - dest_pos)
            if offset > 1.0:
              if offset > 3.0:
                self.puppet.magic.power(self.shot, -1.0)
              c = min(1.0, abs(self.shot.pos + self.shot.speed - dest_pos) / 3.0)
              if self.shot.pos + self.shot.speed > dest_pos:
                self.puppet.magic.move(self.shot, -c * self.puppet.magic_energy)
              elif self.shot.pos + self.shot.speed < dest_pos:
                self.puppet.magic.move(self.shot,  c * self.puppet.magic_energy)

            # Field value
            if offset < 3.0:
              value = self.puppet.LightField.value(self.shot.pos)
              diff  = dest_value - value
              c = min(1.0, abs(diff) / 0.05)
              if value < dest_value:
                self.puppet.magic.power(self.shot,  c * self.puppet.magic_energy)
              elif value > dest_value:
                self.puppet.magic.power(self.shot, -c * self.puppet.magic_energy)

          elif self.state == "walking":
            if self.time_passed(1.0):
              if self.puppet.pos > self.waypoint:
                self.puppet.move_left()
              else:
                self.puppet.move_right()

              if abs(self.puppet.pos - self.waypoint) < 1.0:
                self.puppet.stop()
                self.waypoint = False


class WimpyController(FSMController):
      states   = [ "idle", "flee" ]

      def __init__(self, *args):
          FSMController.__init__(self, *args)
          self.last_hp  = self.puppet.hp
          self.waypoint = 0.0

      def debug_info(self):
          return "%s waypoint=%3f" % (FSMController.debug_info(self), self.waypoint)
      def set_waypoint(self, waypoint):
          self.waypoint = waypoint

      def state_change(self):
          if self.state == "idle":
            if self.puppet.hp - self.last_hp < -self.puppet.timediff * 1.0:
              self.set_state("flee")
          elif self.state == "flee":
            if self.state_time() > 3.0:
              self.set_state("idle")
          self.last_hp = self.puppet.hp

      def state_action(self):
          if self.state == "idle":
            # move around randomly
            if self.time_passed(1.0, 2.0):
              decision = int(random() * 4) % 4
              if decision == 0:
                self.puppet.move_left()
              elif decision == 1:
                self.puppet.move_right()
              elif decision == 2:
                self.puppet.stop()
              elif decision == 3:
                if self.puppet.pos > self.waypoint:
                  self.puppet.move_left()
                else:
                  self.puppet.move_right()
          elif self.state == "flee":
            # reverse direction and start moving away from danger
            if self.time_passed(3.0):
              if self.puppet.direction > 0:
                self.puppet.move_left()
              else:
                self.puppet.move_right()

class HunterController(FSMController):
      states = [ "idle", "follow", "shoot", "evade", "heal" ]
      def __init__(self, puppet):
          FSMController.__init__(self, puppet)
          self.target   = False
          self.shot     = False
          self.waypoint = 0.0

      def debug_info(self):
          if self.target:
            target_pos = self.target.pos
          else:
            target_pos = 0
          return "%s target=%s (%3f) waypoint=%3f" % \
                 (FSMController.debug_info(self), self.target, target_pos, self.waypoint)
      def set_waypoint(self, waypoint):
          self.waypoint = waypoint

      def nearby(self, dist, who):
          closest = dist
          found   = False
          pos     = self.puppet.pos
          candidates = self.puppet.world.get_actors(pos - dist, pos + dist, include = who)
          for actor in candidates:
            distance = abs(actor.pos - pos)
            if distance < closest:
              closest = distance
              found   = actor
          return found
      # look for nearby actors and decide who to attack
      def acquire_target(self):
          new_target = self.nearby(75, self.puppet.prey)
          if new_target:
            self.target = new_target
      # look for nearby particles and decide which one to evade
      def acquire_particle(self):
          new_shot = self.nearby(5, [fields.MagicParticle])
          if new_shot:
            self.shot = new_shot
            self.puppet.magic.capture(self.shot)
          
      def move_randomly(self):
          decision = int(random() * 4) % 4
          if decision == 0:
            self.puppet.move_left()
          elif decision == 1:
            self.puppet.move_right()
          elif decision == 2:
            self.puppet.stop()
          elif decision == 3:
            if self.puppet.pos > self.waypoint:
              self.puppet.move_left()
            else:
              self.puppet.move_right()

      def target_dist(self):
          return abs(self.target.pos - self.puppet.pos)
      def shot_dist(self):
          return abs(self.shot.pos - self.puppet.pos)
          
      def state_change(self):
          if self.state == "idle":
             if self.shot:
               self.set_state("evade")
             elif self.puppet.hp < self.puppet.initial_hp * 0.75:
               self.set_state("heal")
             elif self.target:
               self.set_state("follow")

          elif self.state == "follow":
            if self.state_time() > 3.0 or not self.target:
              self.target = False
              self.set_state("idle")
            elif self.shot:
              self.set_state("evade")
            elif self.state_time() > 1.0 and (50.0 > self.target_dist() > 10.0):
              self.set_state("shoot")

          elif self.state == "shoot":
            if self.state_time() > 5.0 or not self.shot:
              if self.shot:
                self.puppet.magic.release(self.shot)
                self.shot = False
              self.set_state("follow")

          elif self.state == "evade":
            if not self.shot:
              self.set_state("idle")

          elif self.state == "heal":
            if self.state_time() > 10.0 or self.puppet.hp > self.puppet.initial_hp * 0.9:
              self.set_state("idle")

      def state_action(self):
          if self.state == "idle":
            if self.time_passed(2.0, 1.0):
              self.move_randomly()
              self.acquire_target()
              self.acquire_particle()

          elif self.state == "follow":
            self.acquire_particle()
            if self.time_passed(1.0, 1.0):
              if abs(self.target.pos - self.puppet.pos) > 50.0:
                if self.target.pos > self.puppet.pos:
                  self.puppet.move_right()
                else:
                  self.puppet.move_left()
              elif abs(self.target.pos - self.puppet.pos) < 25.0:
                if self.target.pos > self.puppet.pos:
                  self.puppet.move_left()
                else:
                  self.puppet.move_right()
              else:
                self.move_randomly()

            # forget the dead
            if self.target.dead:
              self.target = False

          elif self.state == "shoot":
            # fire the shot and set it moving
            if not self.shot:
              if self.target.pos > self.puppet.pos:
                self.puppet.move_right()
              else:
                self.puppet.move_left()
              self.puppet.stop()
              self.shot = self.puppet.magic.new(fields.EarthBall)
              self.puppet.magic.power(self.shot, 10.0)
              if self.target.pos > self.shot.pos:
                self.puppet.magic.move(self.shot, 3.0)
              else:
                self.puppet.magic.move(self.shot, -3.0)

            if self.shot.pos + self.shot.speed > self.target.pos:
              self.puppet.magic.move(self.shot, -3.0)
            else:
              self.puppet.magic.move(self.shot, 3.0)

          elif self.state == "evade":
            if self.shot_dist() > 10.0:
              self.puppet.magic.release(self.shot)
              self.shot = False
            elif self.time_passed(1.0, 1.0):
              if self.shot.pos > self.puppet.pos:
                self.puppet.magic.move(self.shot, 3.0)
                self.puppet.move_left()
              else:
                self.puppet.magic.move(self.shot, -3.0)
                self.puppet.move_right()

          elif self.state == "heal":
            if not self.shot:
              self.puppet.stop()
              self.shot = self.puppet.magic.new(fields.EarthBall)
              self.puppet.magic.power(self.shot, -10.0)

            if self.shot.pos + self.shot.speed < self.puppet.pos:
              self.puppet.magic.move(self.shot, 1.0)
            else:
              self.puppet.magic.move(self.shot, -1.0)

class HuntingDragon(Dragon):
      control = HunterController
      prey    = [Dude, Rabbit, Guardian]
class HuntingDude(Dude):
      control = HunterController
      prey    = [Dragon]
class ScaredRabbit(Rabbit):
      control = WimpyController
class ControlledGuardian(Guardian):
      control = GuardianController
class FlockingBird(SmallBird):
      control = BirdFlocker
class PredatorBird(BigBird):
      control = BirdPredator
