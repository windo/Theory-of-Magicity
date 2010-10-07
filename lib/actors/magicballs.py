from lib import effects, fields
from base import Actor

class MagicParticle(Actor):
      # Actor params
      const_accel  = 5.0
      animate_stop = True
      anim_speed   = 3.0
      hover_height = 100.0
      initial_hp   = 0
      directed     = False
      stacking     = 26
      in_dev_mode  = False

      # Particle params
      base_dev     = 5.0
      base_mult    = 10.0
      base_coeff   = 0.8  # seems that this is the maximum output with dev=5 and mult=10, used to normalize the mult
      mult_speed   = 0.25 # percentage change per second

      def __init__(self, world, pos):
          Actor.__init__(self, world, pos)
          self.field     = world.get_field(self.fieldtype)
          self.dev       = self.base_dev
          self.mult      = 0.0
          self.accel     = 0.0
          self.deadtimer = False
          self.dead      = False
          self.field.add_particle(self)

          # animation
          if len(self.effectors) == 1:
            fx = self.effectors[0](self)
            self.particle_effects = [fx]
          else:
            fxpos = self.effectors[0](self)
            fxneg = self.effectors[1](self)
            self.particle_effects = [fxpos, fxneg]

          # MagicCaster objects of actors who are influencing this particle
          self.affects  = []
          # selected in game UI
          self.selected = False

      def debug_info(self):
          desc  = Actor.debug_info(self)
          desc += "\nState: acc=%.1f mult=%.1f\n" % (self.accel, self.mult)
          desc += "Affecting:\n"
          for aff in self.affects:
            acc, mult = aff.affect_particle(self).get()
            desc += "%s: acc=%.2f, mult=%.2f\n" % (aff.actor, acc, mult)
          return desc

      # MagicCasters register to influence the particle
      def affect(self, caster):
          self.affects.append(caster)
      def release(self, caster):
          self.affects.pop(self.affects.index(caster))

      # particle params (position, normal distribution params) for field calculation
      def get_params(self):
          return [self.pos, self.dev, self.mult / self.base_coeff]

      def destroy(self):
          # no more field effects
          self.field.del_particle(self)
          # remove from world
          self.world.del_actor(self)
          # notify casters that the particle is gone now
          for caster in self.affects:
            caster.notify_destroy(self)

      def update(self):
          Actor.update(self)

          # update fancy graphics
          #value = self.field.value(self.pos)
          value = self.mult / 10.0
          if len(self.particle_effects) == 1:
            self.particle_effects[0].update(value)
          else:
            if value > 0:
              self.particle_effects[0].update(value)
              self.particle_effects[1].update(0)
            else:
              self.particle_effects[0].update(0)
              self.particle_effects[1].update(abs(value))
         
          # each caster can effect the particle
          acc = 0.0
          mult  = 0.0
          for caster in self.affects:
            affects = caster.affect_particle(self)
            acc += affects.acc
            mult += affects.mult
          # smooth changing of multiplier
          multdiff = (mult - self.mult)
          self.mult += self.timediff * multdiff * self.mult_speed
          # acceleration is immediate 
          self.accel = acc * 3.0

          # if the power drops too low, terminate itself
          if abs(self.mult) < 0.1:
            if self.deadtimer:
              if self.deadtimer + 1.0 < self.world.get_time():
                self.dead = True
                self.destroy()
            else:
              self.deadtimer = self.world.get_time()
          else:
            self.deadtimer = False

      def draw(self):
          cam = self.world.camera
          if not Actor.draw(self):
            return False
          # draw magic "ball"
          radius = 25 
          x      = cam.pl2sc_x(self.pos)
          y      = cam.sc_h() - self.hover_height
          s = effects.get_circle((255, 255, 255, 64), radius, cam.graphics, blur = 15)
          cam.graphics.blit(s, (x - radius, y - radius))

          # draw field effects
          for fx in self.particle_effects:
            fx.draw(cam.graphics)
            
          # if it's selected
          if self.selected:
            radius = 50
            s = effects.get_circle((255, 255, 255, 16), radius, cam.graphics)
            cam.graphics.blit(s, (x - radius, y - radius))
            # affects
            s = effects.get_circle((255, 255, 255, 64), 5, cam.graphics, 2)
            for caster in self.affects:
              acc, mult = caster.affect_particle(self).get()
              for i in xrange(5):
                xdiff = acc * 55.0 / 10 / 5 * i
                ydiff = mult  * 55.0 / 10 / 5 * i
                cam.graphics.blit(s, (x - 5 + xdiff, y - 5 - ydiff))
          return True

class TimeBall(MagicParticle):
      sprite_names = []
      effectors    = [ effects.Energy ]
      fieldtype    = fields.TimeField
class WindBall(MagicParticle):
      sprite_names = []
      effectors    = [ effects.Wind ]
      fieldtype    = fields.WindField
      snd_move     = ["wind1", "wind2", "wind3"]
class LifeBall(MagicParticle):
      sprite_names = []
      effectors    = [ effects.Fire, effects.Nature ]
      fieldtype    = fields.LifeField

def field2ball(field):
    return {fields.TimeField: TimeBall, fields.WindField: WindBall, fields.LifeField: LifeBall }[field.__class__]
