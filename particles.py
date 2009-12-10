from core import MagicParticle
import fields

class FireBall(MagicParticle):
      sprite_names = ["fireball"]
      fieldtype    = fields.FireField
      fieldeffect  = +1
class IceBall(MagicParticle):
      sprite_names = ["iceball"]
      fieldtype    = fields.FireField
      fieldeffect  = -1
class QuickBall(MagicParticle):
      sprite_names = ["quickball"]
      fieldtype    = fields.QuickField
      fieldeffect  = +1
      anim_speed   = 6
class SlowBall(MagicParticle):
      sprite_names = ["quickball"]
      fieldtype    = fields.QuickField
      fieldeffect  = -1
      anim_speed   = 1
class LifeBall(MagicParticle):
      sprite_names = ["lifeball"]
      fieldtype    = fields.LifeField
      fieldeffect  = +1
class DeathBall(MagicParticle):
      sprite_names = ["deathball"]
      fieldtype    = fields.LifeField
      fieldeffect  = -1
