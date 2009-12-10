from random import random
import math, time, pygame
import fields

class MagicCaster:
      """
      Supplements an Actor

      It handles the list of magic particles controlled by an actor
      It manages how the actor influences the particles
      """
      magic_distance = 5.0

      def __init__(self, actor, magic_energy):
          self.actor   = actor
          self.energy  = magic_energy
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
          # register to influence it [speed, power]
          self.affects[particle] = [0.0, 10.0]
          particle.affect(self)
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
      def move_right(self, particle):
          if self.affects.has_key(particle):
            self.affects[particle][0] = 5.0
            self.balance_energy()
      def move_left(self, particle):
          if self.affects.has_key(particle):
            self.affects[particle][0] = -5.0
            self.balance_energy()
      def power_up(self, particle):
          if self.affects.has_key(particle):
            self.affects[particle][1] += 1.0
            self.balance_energy()
      def power_down(self, particle):
          if self.affects.has_key(particle):
            self.affects[particle][1] -= 1.0
            self.balance_energy()
      def stop(self, particle):
          if self.affects.has_key(particle):
            self.affects[particle][0] = 0
            self.balance_energy()

      def balance_energy(self):
          """
          go over the list of affects and make sure we stay within
          the energy consumption limit
          """
          used = 0.0
          for speed, power in self.affects.values():
            used += abs(speed) + abs(power)
          if used > self.energy:
            ratio = self.energy / used
            for affect in self.affects.keys():
              speed, power = self.affects[affect]
              speed *= ratio
              power *= ratio
              self.affects[affect] = [speed, power]
            corrected = 0.0
            for speed, power in self.affects.values():
              corrected += abs(speed) + abs(power)
            #print "used=%.1f > total=%.1f -> ratio=%.2f: corrected=%.1f" % (used, self.energy, ratio, corrected)

      # called by particles
      def affect_particle(self, particle):
          return self.affects[particle]
      def notify_destroy(self, particle):
          if self.affects.has_key(particle):
            del self.affects[particle]

class Actor:
      # movement
      const_speed    = 0.0
      const_accel    = 0.0

      # animation conf
      animate_stop = False
      anim_speed   = 1.0
      hover_height = 0.0
      directed     = True

      # char attributes
      initial_hp   = 100.0
      regeneration = 0.5
      magic_energy = 25.0
      
      # "puppetmaster"
      control        = None

      def __init__(self, world, pos):
          # movement params
          self.speed = 0.0
          self.accel = 0.0
          self.pos   = pos
          self.world = world
          # actor clock
          self.last_update = world.get_time()
          self.timediff    = 0.0

          # animation params
          self.start_time = time.time()
          self.direction  = -1
          self.animate    = self.animate_stop

          # character params
          self.hp     = self.initial_hp
          self.magic  = MagicCaster(self, self.magic_energy)

          # load images
          if self.directed:
            self.img_left  = world.sprites.get(self.sprite_names[0])
            self.img_right = world.sprites.get(self.sprite_names[1])
            self.img_count = len(self.img_left)
            self.img_w     = self.img_left[0].get_width()
            self.img_h     = self.img_left[0].get_height()
          else:
            self.img_list  = world.sprites.get(self.sprite_names[0])
            self.img_count = len(self.img_list)
            self.img_w     = self.img_list[0].get_width()
            self.img_h     = self.img_list[0].get_height()
          self.cur_img_idx = 0

          # controller init
          if self.control:
            self.controller = self.control(self)
          else:
            self.controller = None
      def destroy(self):
          self.world.del_actor(self)
          self.magic.release_all()

      def __str__(self):
          return "%s(0x%s)" % (str(self.__class__).split(".")[1], id(self))
      def debug_info(self):
          desc = "%s pos=%.1f speed=%.3f" % (str(self), self.pos, self.speed)
          if self.controller:
            desc += "\nController: %s" % (self.controller.debug_info())
          return desc

      # moving the actor
      def move_left(self):
          if not self.const_accel:
            self.speed   = -self.const_speed
          else:
            self.accel   = -self.const_accel
          self.animate   = True
          self.direction = -1
      def move_right(self):
          if not self.const_accel:
            self.speed   = self.const_speed
          else:
            self.accel   = self.const_accel
          self.animate   = True
          self.direction = 1
      def stop(self):
          if not self.const_accel:
            self.speed   = 0
          else:
            self.accel   = 0
          self.animate   = self.animate_stop

     # called every frame
      def update(self):
          # update actor clock
          now              = self.world.get_time()
          self.timediff    = now - self.last_update
          self.last_update = now
          # update movement
          if self.accel:
            self.speed += self.timediff * self.accel
          if self.speed:
            self.pos  += self.timediff * self.speed * (self.world.get_field(fields.QuickField).value(self.pos) + 1.0)
          # effects of magic
          self.hp -= self.timediff * self.damage()
          if self.hp < self.initial_hp:
            self.hp += self.timediff * self.regeneration
          # death
          if self.hp <= 0 and self.initial_hp:
            self.destroy()
          # controlled actors
          if self.controller:
            self.controller.update()
      # different Actors can implement their own way of changing their hp
      def damage(self):
          return self.world.fields.get(fields.FireField).value(self.pos) * 25.0
      
      # draw image, either left-right directed or unidirectional
      def draw(self, view, screen, draw_hp = False, draw_debug = False):
          # do not draw off-the screen actors
          if self.pos + self.img_w < self.world.view.pl_x1() or self.pos - self.img_w > self.world.view.pl_x2():
            return
          # facing direction
          if self.directed:
            if self.direction > 0:
              imglist = self.img_right
            else:
              imglist = self.img_left
          # unidirectional
          else:
            imglist = self.img_list

          # to animate or not to animate
          if self.animate:
            self.cur_img_idx = int(time.time() * self.img_count * self.anim_speed) % self.img_count
          else:
            self.cur_img_idx = 0

          # hovering in air (particles)
          if self.hover_height:
            hover = self.hover_height + self.hover_height * math.sin((time.time() - self.start_time) * 2) * 0.3
          else:
            hover = 0.0

          # actual drawing
          img = imglist[self.cur_img_idx]
          coords = (view.pl2sc_x(self.pos) - self.img_w / 2, view.sc_h() - self.img_h - hover)
          screen.blit(img, coords)

          # draw hp bar
          if draw_hp and self.initial_hp:
            hp_color   = (64, 255, 64)
            hp_border  = (view.pl2sc_x(self.pos), view.sc_h() - self.img_h - hover, 30, 3)
            hp_fill    = (view.pl2sc_x(self.pos), view.sc_h() - self.img_h - hover, 30 * (self.hp / self.initial_hp), 3)
            pygame.draw.rect(screen, hp_color, hp_border, 1)
            pygame.draw.rect(screen, hp_color, hp_fill, 0)

          if draw_debug:
            lines = self.debug_info().split("\n")
            txts  = []
            for line in lines:
              txts.append(self.world.font.render(line, False, (255, 255, 255)))
            i = 0
            for txt in txts:
              screen.blit(txt,(view.pl2sc_x(self.pos) - img.get_width() / 2, int(draw_debug) + 20 + i * 10))
              i += 1

class FSMController:
      states = [ "idle" ]
      start_state = "idle"

      class InvalidState(Exception):
            def __init__(self, state):
                self.state = state
            def __str__(self):
                return "Invalid state change to: %s" % (self.state)

      def __init__(self, puppet):
          self.puppet  = puppet
          self.last_hp = puppet.hp
          self.state   = False
          self.switch(self.start_state)
      def __str__(self):
          return "%s" % (str(self.__class__).split(".")[1])
      def debug_info(self):
          return "%s: [%s]" % (str(self), self.state)

      def switch(self, newstate):
          if not newstate in self.states:
            raise self.InvalidState(newstate)
          if newstate != self.state:
            self.state       = newstate
            self.switch_time = time.time()

      def state_time(self):
          return time.time() - self.switch_time

      def update(self):
          self.state_change()
          self.last_hp = self.puppet.hp
          self.state_action()
      def state_change(self):
          pass
      def state_action(self):
          pass


class MagicParticle(Actor):
      # Actor params
      const_accel  = 5.0
      animate_stop = True
      anim_speed   = 3.0
      hover_height = 25.0
      initial_hp   = 0
      directed     = False

      # Particle params
      base_dev     = 5.0
      base_mult    = 10.0
      mult_speed   = 0.25  # percentage change per second

      def __init__(self, world, pos):
          Actor.__init__(self, world, pos)
          self.field     = world.get_field(self.fieldtype)
          self.dev       = self.base_dev
          self.mult      = 1.0
          self.deadtimer = False
          self.field.add_particle(self)

          # actors who are influencing this particle
          self.affects = []

      def debug_info(self):
          desc = Actor.debug_info(self)
          desc += "\nAffecting: %s" % (", ".join([str(aff.actor) for aff in self.affects]))
          return desc

      # MagicCasters register to influence the particle
      def affect(self, caster):
          self.affects.append(caster)
      def release(self, caster):
          self.affects.pop(self.affects.index(caster))

      # particle params (position, normal distribution params) for field calculation
      def get_params(self):
          return [self.pos, self.dev, self.mult]

      def destroy(self):
          # no more field effects
          self.field.del_particle(self)
          # remove from world
          self.world.del_actor(self)
          # notify casters that the particle is gone now
          for caster in self.affects:
            caster.notify_destroy(self)
