import pygame, math, time
from random import random
import graphics

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
          self.id     = world.next_actor_id()
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
          return "%s(%u)" % (str(self.__class__).split(".")[1], self.id)
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
      def draw(self, draw_debug = False):
          """
          Draw the image on screen, called in sequence from main game loop for each actor
          """
          x, y = self.get_xy()
          view = self.world.view

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
              view.blit(txt, (x, int(draw_debug) + 20 + i * 20))
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
          view.blit(img, (x - self.img_w / 2, y))

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
          Drawable.draw(self, draw_debug)

          # draw hp bar (if there is one)
          if self.initial_hp:
            x, y      = self.get_xy()
            hp_color  = (64, 255, 64)
            hp_border = (x - 15, y, 30, 3)
            hp_fill   = (x - 15, y, 30 * (self.hp / self.initial_hp), 3)
            graphics.rect(hp_color, hp_border, 1)
            graphics.rect(hp_color, hp_fill, 0)

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

      def draw(self, draw_debug = False): 
          img    = self.img_list[0]
          bg_w   = img.get_width() 
          bg_h   = img.get_height()
          view   = self.world.view
          offset = (view.pl2sc_x(0) / self.distance) % bg_w - bg_w 
          count  = int(view.sc_w() / bg_w) + 2 
          for i in xrange(count):
            view.blit(img, (offset + i * bg_w, view.sc_h() - bg_h))

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
      in_dev_mode  = False

class Villager(Dude):
      sprite_names = ["villager-left", "villager-right"]
      stacking     = 20

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
      in_dev_mode = False

# controllers
class Controller:
      """
      An actor may have a controller that moves it around
      """
      control_interval = 0.1
      def __init__(self, puppet):
          self.puppet = puppet
      def __str__(self):
          return "%s" % (str(self.__class__).split(".")[1])
      def debug_info(self):
          return "%s" % (str(self))
      def update(self):
          pass

class FlyingController(Controller):
      """
      A controller for the birds flying around in background.
      The different birds just need to implement the decision where to fly.
      """
      control_interval = 0.2
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
          """
          Must be overloaded to set up self.xdiff and self.ydiff
          to direct towards the destination where to fly
          """
          pass

      def update(self):
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
      """
      A controller that attempts to fly around randomly prefering to keep
      together in flocks.
      
      When a predator brid approaches, the primary goal is to escape it.
      """
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
          self.weight_speed = 1.0
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

          vis_start = self.puppet.pos - self.visible_dist
          vis_end   = self.puppet.pos + self.visible_dist
          # predators
          preds = self.puppet.world.get_actors(vis_start, vis_end, include = [BigBird])
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
          neighs = self.puppet.world.get_actors(vis_start, vis_end, include = [SmallBird])
          # flocking
          flock_xdiff  = flock_ydiff  = 0.0
          flock_xspeed = flock_yspeed = 0.0
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
            # synchronize speeds
            if dist < self.prefer_dist * 2:
              flock_xspeed += neigh.speed
              flock_yspeed += neigh.yspeed
            flock_xdiff  += const * xdiff
            flock_ydiff  += const * ydiff
          if neighs:
            x, y = self.normalize_xy(flock_xdiff, flock_ydiff, self.weight_flock)
            self.xdiff += x
            self.ydiff += y
            x, y = self.normalize_xy(flock_xspeed, flock_yspeed, self.weight_speed)
            self.xdiff += x
            self.ydiff += y

      def update(self):
          FlyingController.update(self)
          # choose a next waypoint 
          if abs(self.xwaypoint - self.puppet.pos) < 1.0 and abs(self.ywaypoint - self.puppet.ypos) < 1.0:
            self.random_waypoint()

class BirdPredator(FlyingController):
      """
      Pick a random small bird and fly towards it
      """
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

class GuardianController(FSMController):
      """
      Block the movement of actors in self.danger with Time magic.
      If there is a waypoint, move to it abandoning the blocking action.
      """
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
              self.shot = self.puppet.magic.new(fields.TimeBall)

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
              value = self.puppet.TimeField.value(self.shot.pos)
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
      """
      Indended for rabbits. Run around randomly (slowly drifting towards waypoint).
      If HP decreases fast enough, flee in the other direction.
      """
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
      """
      Hunt actors in self.puppet.prey.
      Try to keep appropriate distance, fire Life magic balls, evade nearby
      balls and heal self with Life magic.
      """
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
          return "%s target=%s (%.1f) waypoint=%.1f" % \
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
              if self.shot:
                self.puppet.magic.release(self.shot)
                self.shot = False
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
              self.shot = self.puppet.magic.new(fields.LifeBall)
              self.puppet.magic.power(self.shot, 10.0)

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
              self.shot = self.puppet.magic.new(fields.LifeBall)
              self.puppet.magic.power(self.shot, -10.0)

            if self.shot.pos + self.shot.speed < self.puppet.pos:
              self.puppet.magic.move(self.shot, 1.0)
            else:
              self.puppet.magic.move(self.shot, -1.0)

class Planner(Controller):
      """
      Container for planning controller
      """
      control_interval = 0.01
      def __init__(self, *args):
          Controller.__init__(self, *args)
          self.mission = KillEnemies(self)
          self.goals   = {}

          self.move_propose = []
          self.move_pos   = self.puppet.pos
          self.move_score = 0
          self.move_time  = 0.0

          self.magic_propose = []

      def debug_info(self):
          return "Planner move to=%3.2f score=%3.2f time=%3.1f\n%s" % \
                 (self.move_pos, self.move_score, self.move_time, self.mission.debug_info())
      def update(self):
          # clear proposals
          self.move_propose  = []
          self.magic_propose = []

          for goal in self.goals.values():
            goal.prio = 0.0
          self.mission.prio = 1.0
          self.mission.dist_prio()
          self.mission.update()

          self.decide_movement()
          self.decide_magic()

      def propose_magic(self, goal, action):
          self.magic_propose.append((goal, action))
      def decide_magic(self):
          self.magic_propose.sort(lambda x, y: cmp(x[0].score, y[0].score))
          magics = self.magic_propose[:2]
          magics.reverse()

          for goal, action in magics:
            action, ball, value = action
            if action == "move":
              self.puppet.magic.move(ball, value)
            elif action == "power":
              self.puppet.magic.power(ball, value)
          
      def propose_movement(self, goal, pos):
          self.move_propose.append((goal, pos))
      def decide_movement(self):
          # time since last change
          move_time = self.puppet.world.get_time() - self.move_time

          # no proposals
          if len(self.move_propose) == 0:
            if move_time > 2.0:
              self.puppet.stop()
              self.move_time  = self.puppet.world.get_time()
              self.move_score = 0
              self.move_pos   = self.puppet.pos
            return

          # most important proposal
          self.move_propose.sort(lambda x, y: cmp(x[0].score, y[0].score))
          movement = self.move_propose[0]
 
          # should we change?
          if movement[0].score < self.move_score and move_time < 1.0:
            return

          # change direction!
          diff = movement[1] - self.puppet.pos
          if abs(diff) < 1.0:
            self.puppet.stop()
          elif diff > 0.0:
            self.puppet.move_right()
          else:
            self.puppet.move_left()
          self.move_time  = self.puppet.world.get_time()
          self.move_score = movement[0].score
          self.movement   = movement[1]

class Goal:
      # maximum total subgoal score
      maxscore = 2.0
      # maximum total subgoals
      maxgoals = 5

      def __init__(self, controller, *args):
          self.controller = controller
          self.subgoals = []
          self.parents  = []
          self.puppet = controller.puppet
          self.magic  = self.puppet.magic
          self.world  = self.puppet.world
          self.prio  = 0.1
          self.heat  = 0.1
          self.score = 0.01
          self.goal_args = args
          self.__init_goal__(*args)

      def __str__(self):
          return "%s(h=%3.2f, p=%3.2f, s=%3.2f)" % (str(self.__class__).split(".")[1], self.heat, self.prio, self.score)
      def debug_info(self, depth = 0):
          info = " " * depth + ">%s:\n" % (str(self))
          for subgoal in self.subgoals:
            info += subgoal.debug_info(depth + 1)
          return info

      def update(self):
          """
          Default update function for hierarchical goal

          Picks most interesting subgoal and passes execution forward
          """
          print "Entered: %s" % (self.debug_info())

          i = 0
          totalscore = 0.0
          for goal in self.subgoals:
            goal.heat  = goal.get_heat()
            goal.score = goal.heat * goal.prio
          self.subgoals.sort(lambda x, y: cmp(y.score, x.score))
          while i < len(self.subgoals):
            goal = self.subgoals[i]
            if totalscore > self.maxscore:
              print "maxscore: %s" % (goal)
              self.del_subgoal(goal, i)
            elif i > self.maxgoals:
              print "maxgoals: %s" % (goal)
              self.del_subgoal(goal, i)
            elif goal.score <= 0.0:
              print "low score: %s" % (goal)
              self.del_subgoal(goal, i)
            else:
              totalscore += goal.score
              i += 1
          
          # pass the goal action on
          acted = False
          for goal in self.subgoals:
            if random() < (goal.score / totalscore):
              acted = goal.update()
            if acted:
              break

          if not acted or len(self.subgoals) < 2:
            self.add_subgoals()
          return acted

      def add_subgoal(self, goaltype, *args):
          sig = (goaltype, args)
          if self.controller.goals.has_key(sig):
            goal = self.controller.goals[sig]
          else:
            goal = goaltype(self.controller, *args)
            self.controller.goals[sig] = goal
          self.subgoals.append(goal)
          goal.parents.append(self)
          return goal

      def del_subgoal(self, goal, indexhint = None):
          i = indexhint or self.subgoals.index(goal)
          self.subgoals.pop(i)
          i = goal.parents.index(self)
          goal.parents.pop(i)
          if not goal.parents:
            sig = (goal.__class__, goal.goal_args)
            self.controller.goals[sig] = None
            del self.controller.goals[sig]
      
      def __init_goal__(self):
          """
          Should be overloaded if there are meaningful arguments for the goal
          """
          pass
      def add_subgoals(self):
          """
          Called to create new subgoals when no current ones require attention
          """
          raise Exception(str(self.__class__))
      def get_heat(self):
          """
          Amount of attention required from parent

          close to 0 when goal is satisfied, no action required
          close to 1 when action is required to fulfill satisfy the goal
          """
          raise Exception(str(self.__class__))
      def dist_prio(self):
          """
          Distribute amount of attention between subgoals

          close to 0 when fulfilling the subgoal is not important at the moment
          close to 1 when fulfilling the subgoal is imperative at the moment
          """
          raise Exception(str(self.__class__))

      def scale_value(self, input, scale, smooth = False):
          """
          helper function, probably does not belong here

          takes a list of (input, output) pairs and calculates
          input -> output, possibly interpolating
          """
          # find the position on scale
          for i in xrange(len(scale)):
            if input <= scale[i][0]:
              break
          # handle edges
          if i == 0:
            return scale[0][1]
          elif input > scale[i][0]:
            return scale[i][1]
          else:
            # handle normal scale
            if smooth:
              dist = (input - scale[i - 1][0]) / (scale[i][0] - scale[i - 1][0])
              return scale[i - 1][1] + (scale[i][1] - scale[i - 1][1]) * dist
            else:
              return scale[i][1]

class MovementGoal:
      """
      Container for the movement-related methods
      """
      def move_to(self, pos):
          self.controller.propose_movement(self, pos)
      def move_away(self, pos):
          diff = pos - self.puppet.pos
          if diff > 0:
            self.controller.propose_movement(self, self.puppet.pos - 100.0)
          else:
            self.controller.propose_movement(self, self.puppet.pos + 100.0)
      def face(self, pos):
          diff = pos - self.puppet.pos
          if diff * self.puppet.direction > 0:
            self.move_to(self.puppet.pos)
          else:
            self.move_to(pos)

class KillEnemies(Goal):
      def add_subgoals(self):
          # find unhandled prey
          pos = self.puppet.pos
          # TODO: definitely don't just kill Dudes
          targets = self.world.get_actors(pos - 75.0, pos + 75.0, include = [Dude, Villager])
          for target in targets:
            targetting = False
            for goal in self.subgoals:
              if isinstance(goal, KillEnemy) and goal.target == target:
                targetting = True
                break
            if not targetting:
              self.add_subgoal(KillEnemy, target)

      def get_heat(self):
          if self.subgoals:
            return max([goal.get_heat() for goal in self.subgoals])
          else:
            return 0.01
      
      def dist_prio(self):
          if len(self.subgoals) == 0:
            return
          n_goals = len(self.subgoals)
          prios = []
          total = 0.0
          # dropping base multiplied by distance scale
          for i in xrange(n_goals):
            goal = self.subgoals[i]
            prios.append(0.25 + (float(n_goals - i) / n_goals) * 0.5)
            diff = abs(self.puppet.pos - goal.target.pos)
            prios[i] *= self.scale_value(diff, ((0, 0.3), (15, 0.3), (30, 0.9), (60, 0.7), (75, 0.1), (100, 0.0)))
            total += prios[i]
          coef = self.prio / total
          for i in xrange(n_goals):
            self.subgoals[i].prio += prios[i] * coef
            self.subgoals[i].dist_prio()

class TargetedGoal(Goal):
      def __init_goal__(self, target):
          self.target = target
      def __str__(self):
          return "%s: %s" % (Goal.__str__(self), self.target)

class KillEnemy(TargetedGoal):
      def add_subgoals(self):
          f = d = False
          for g in self.subgoals:
            if isinstance(g, PosField):
              f = True
            elif isinstance(g, FightingDistance):
              d = True
          if not f: 
            self.fireball = self.add_subgoal(PosField, self.target)
          if not d:
            self.distance = self.add_subgoal(FightingDistance, self.target)

      def get_heat(self):
          if self.target.dead:
            return 0.0
          if len(self.subgoals) == 0:
            return 1.0
          return max([g.get_heat() for g in self.subgoals])
      def dist_prio(self):
          if not self.subgoals:
            return
          if self.fireball.get_heat() > self.distance.get_heat():
            self.fireball.prio += self.prio * 0.7
            self.distance.prio += self.prio * 0.3
          else:
            self.fireball.prio += self.prio * 0.3
            self.distance.prio += self.prio * 0.7
          self.fireball.dist_prio()
          self.distance.dist_prio()

class FightingDistance(TargetedGoal, MovementGoal):
      def get_heat(self):
          diff = self.target.pos - self.puppet.pos
          return self.scale_value(abs(diff), ((0, 1.0), (10, 0.5), (35, 0.1), (65, 0.1), (75, 0.5), (90, 1.0)))
      def update(self):
          diff = abs(self.target.pos - self.puppet.pos)
          if 35.0 < diff < 65.0:
            self.face(self.target.pos)
          elif diff < 35.0:
            self.move_away(self.target.pos)
          else:
            self.move_to(self.target.pos)
      def dist_prio(self): pass

class PosField(TargetedGoal):
      def add_subgoals(self):
          pos = self.target.pos
          targets = self.world.get_actors(pos - 75.0, pos + 75.0, include = [fields.LifeBall])
          for target in targets:
            in_goal = False
            for goal in self.subgoals:
              if isinstance(goal, MoveBall) and goal.ball == target:
                # TODO: don't cheat like this
                in_goal = True
                break
            if not in_goal:
              self.add_subgoal(MoveBall, target, self.target)
              self.add_subgoal(PowerBall, target)

          if len(targets) == 0:
            self.add_subgoal(CreateBall, fields.LifeBall)
      def get_heat(self):
          if len(self.subgoals) == 0:
            return 1.0
          return max([g.get_heat() for g in self.subgoals])
      def dist_prio(self):
          if len(self.subgoals) == 0:
            return
          n_goals = len(self.subgoals)
          prios = []
          total = 0.0
          # dropping base multiplied by distance scale
          for i in xrange(n_goals):
            goal = self.subgoals[i]
            prios.append(0.25 + (float(n_goals - i) / n_goals) * 0.5)
            if isinstance(goal, CreateBall):
              prios[i] *= 3
            else:
              diff = abs(self.target.pos + self.target.speed - goal.ball.pos - goal.ball.speed)
              if isinstance(goal, MoveBall):
                prios[i] *= self.scale_value(diff, ((0, 0.1), (10, 2), (15, 1), (50, 0.7), (75, 0.01)))
              elif isinstance(goal, PowerBall):
                if goal.ball.mult < 1.0:
                  prios[i] *= 2
                else:
                  prios[i] *= self.scale_value(diff, ((0, 2), (10, 1), (25, 0.5), (75, 0.01)))
            total += prios[i]
          coef = self.prio / total
          for i in xrange(n_goals):
            self.subgoals[i].prio += prios[i] * coef
            self.subgoals[i].dist_prio()

class CreateBall(Goal):
      def __init_goal__(self, balltype):
          self.balltype = balltype
          self.created  = False
      def update(self):
          if not self.created:
            self.magic.new(fields.LifeBall)
            self.created = True
          return True
      def get_heat(self):
          if self.created: return 0.0
          else: return 1.0
      def dist_prio(self): pass

class MagicGoal:
      """
      Container for the magic-related methods
      """
      def move(self, ball, value):
          self.controller.propose_magic(self, ("move", ball, value))
      def power(self, ball, value):
          self.controller.propose_magic(self, ("power", ball, value))

class MoveBall(Goal, MagicGoal):
      def __init_goal__(self, ball, target):
          self.ball   = ball
          self.target = target
      def __str__(self):
          return "%s: %s -> %s" % (Goal.__str__(self), self.ball, self.target)
      def dest_pos(self):
          if isinstance(self.target, Actor): return self.target.pos + self.target.speed
          else: return self.target
      def update(self):
          ball = self.ball
          dest = self.dest_pos()
          diff = ball.pos + ball.speed - dest

          if abs(diff) < 1.0:
            self.move(ball, 0)
          elif diff > 0:
            self.move(ball, -10)
          else:
            self.move(ball, 10)
          return True
      def get_heat(self):
          if self.ball.dead:
            return 0.0
          diff = self.dest_pos() - (self.ball.pos + self.ball.speed)
          score = self.scale_value(abs(diff), ((0, 0.1), (1, 0.5), (5, 0.5), (10, 0.3), (90, 0.3), (150, 0.0)))
          print abs(diff), score
          return score
      def dist_prio(self): pass

class PowerBall(Goal, MagicGoal):
      def __init_goal__(self, ball):
          self.ball  = ball
      def __str__(self):
          return "%s: %s" % (Goal.__str__(self), self.ball)
      def update(self):
          self.power(self.ball, 10)
          return True
      def get_heat(self):
          if self.ball.dead:
            return 0.0
          diff = 10.0 - self.ball.mult
          return self.scale_value(abs(diff), ((0, 0.1), (5, 0.2), (10, 0.6)), smooth = True)
      def dist_prio(self): pass

class BehavingDragon(Dragon):
      control = Planner

class HuntingDragon(Dragon):
      control = HunterController
      prey    = [Dude, Rabbit, Guardian]
class HuntingVillager(Villager):
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
