from random import random
from base import Controller
from lib import fields
from mainchars import *
from magicballs import *

class Planner(Controller):
      """
      Container for planning controller
      """
      control_interval = 0.1
      def __init__(self, *args):
          Controller.__init__(self, *args)
          self.goals   = {}
          self.mission = Operate(self)

          self.move_propose = []
          self.move_pos   = self.puppet.pos
          self.move_score = 0
          self.move_time  = 0.0

          self.magic_propose = []

          self.waypoint = self.puppet.pos
      def set_waypoint(self, waypoint):
          self.waypoint = waypoint

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
            self.puppet.magic.capture(ball)
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
      def __init__(self, controller, *args):
          self.controller = controller
          self.puppet = controller.puppet
          self.magic  = self.puppet.magic
          self.world  = self.puppet.world

          self.subgoals = []
          self.parents  = []
          self.prio  = 0.1
          self.heat  = 0.1
          self.score = 0.01

          self.goal_args = args
          self.__init_goal__(*args)

      def __str__(self):
          return "%s(%s: h=%1.3f, p=%1.3f, s=%1.3f)" % (str(self.__class__).split(".")[1], self.goal_args, self.heat, self.prio, self.score)
      def debug_info(self, depth = 0):
          info = " " * depth + ">%s\n" % (str(self))
          for subgoal in self.subgoals:
            info += subgoal.debug_info(depth + 1)
          return info

      def __init_goal__(self, *args):
          """
          Should be overloaded if there are meaningful arguments for the goal
          """
          pass
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
          pass

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

class TreeGoal(Goal):
      # maximum total subgoal score
      maxscore = 2.0
      # maximum total subgoals
      maxgoals = 5
      def __init__(self, *args):
          Goal.__init__(self, *args)

      def update(self):
          """
          Default update function for hierarchical goal

          Picks most interesting subgoal and passes execution forward
          """
          #print "Entered: %s" % (self.debug_info())

          for goal in self.subgoals:
            goal.heat  = goal.get_heat()
            goal.score = goal.heat * goal.prio
          self.subgoals.sort(lambda x, y: cmp(y.score, x.score))
          totalscore = self.del_subgoals()

          # pass the goal action on
          acted = False
          for goal in self.subgoals:
            if goal.score == 0.0:
              continue
            elif random() < (goal.score / totalscore):
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

      def del_subgoal(self, goal):
          i = self.subgoals.index(goal)
          self.subgoals.pop(i)
          i = goal.parents.index(self)
          goal.parents.pop(i)
          if not goal.parents:
            sig = (goal.__class__, goal.goal_args)
            self.controller.goals[sig] = None
            del self.controller.goals[sig]

      def add_subgoals(self):
          pass
      def del_subgoals(self):
          return sum([g.score for g in self.subgoals])

      def dist_prio(self):
          raise Exception(str(self.__class__))

      # useful implementations
      def get_heat_maxchild(self):
          if self.subgoals:
            return max([goal.get_heat() for goal in self.subgoals] + [0.01])
          else:
            return 0.01
      def del_subgoals_limiting(self):
          i = 0
          totalscore = 0.0
          while i < len(self.subgoals):
            goal = self.subgoals[i]
            if totalscore > self.maxscore:
              #print "maxscore: %s" % (goal)
              self.del_subgoal(goal)
            elif i > self.maxgoals:
              #print "maxgoals: %s" % (goal)
              self.del_subgoal(goal)
            elif goal.score <= 0.0:
              #print "low score: %s" % (goal)
              self.del_subgoal(goal)
            else:
              totalscore += goal.score
              i += 1
          return totalscore

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

class Operate(TreeGoal):
      def __init_goal__(self):
          self.kill  = self.add_subgoal(KillEnemies)
          self.heal  = self.add_subgoal(SetField, self.puppet, fields.LifeField, "-")
          self.dance = self.add_subgoal(AvoidFireballs)
          self.wayp  = self.add_subgoal(GotoWaypoint)
          self.band  = self.add_subgoal(FormBand)
          self.walk  = self.add_subgoal(WanderAround)
      def dist_prio(self):
          hp = self.puppet.hp / self.puppet.initial_hp
          healprio  = self.scale_value(hp, ((0, 1.0), (0.1, 1.0), (0.3, 0.3), (0.8, 0.1), (1.0, 0.01)), smooth = True)
          fightprio = (1 - healprio) * 0.8
          walkprio  = (1 - healprio) * 0.2
          # healing first
          self.heal.prio  += healprio * self.prio * 0.5
          self.dance.prio += healprio * self.prio * 0.5
          # then fighting
          self.kill.prio  += fightprio * self.prio
          # then other movements
          self.wayp.prio += walkprio * self.prio * 0.45
          self.band.prio += walkprio * self.prio * 0.45
          self.walk.prio += walkprio * self.prio * 0.1
          for g in self.subgoals:
            g.dist_prio()
      get_heat = TreeGoal.get_heat_maxchild

class KillEnemies(TreeGoal):
      del_subgoals = TreeGoal.del_subgoals_limiting
      def add_subgoals(self):
          # find unhandled prey
          pos = self.puppet.pos
          targets = self.world.get_actors(pos - 75.0, pos + 75.0, include = self.puppet.prey)
          for target in targets:
            targetting = False
            for goal in self.subgoals:
              if isinstance(goal, KillEnemy) and goal.target == target:
                targetting = True
                break
            if not targetting:
              self.add_subgoal(KillEnemy, target)

      get_heat = TreeGoal.get_heat_maxchild
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
          if total == 0:
            coef = 0.0
          else:
            coef = self.prio / total
          for i in xrange(n_goals):
            self.subgoals[i].prio += prios[i] * coef
            self.subgoals[i].dist_prio()

class KillEnemy(TreeGoal):
      def __init_goal__(self, target):
          self.target = target
          self.fireball = self.add_subgoal(SetField, self.target, fields.LifeField, "+")
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

class FightingDistance(Goal, MovementGoal):
      def __init_goal__(self, target):
          self.target = target
      def get_heat(self):
          diff = abs(self.target.pos - self.puppet.pos)
          return self.scale_value(diff, ((0, 1.0), (10, 0.5), (35, 0.1), (65, 0.1), (75, 0.5), (90, 1.0)))
      def update(self):
          diff = abs(self.target.pos - self.puppet.pos)
          if 35.0 < diff < 65.0:
            self.face(self.target.pos)
          elif diff < 35.0:
            self.move_away(self.target.pos)
          else:
            self.move_to(self.target.pos)

class GotoWaypoint(Goal, MovementGoal):
      def get_heat(self):
          diff = abs(self.controller.waypoint - self.puppet.pos)
          return self.scale_value(diff, ((0, 0.01), (5, 0.1), (15, 0.2), (50, 0.5), (75, 1.0)))
      def update(self):
          self.move_to(self.controller.waypoint)

class WanderAround(Goal, MovementGoal):
      def get_heat(self):
          return 0.5
      def update(self):
          self.move_to(self.puppet.pos + random() * 50 - 25)

class FormBand(Goal, MovementGoal):
      def band_pos(self):
          pos = self.puppet.pos
          avg     = 0.0
          closest = pos + 75.0
          friends = self.world.get_actors(pos - 75.0, pos + 75.0, include = [self.puppet.__class__])
          for friend in friends:
            avg += friend.pos / len(friends)
            diff = friend.pos - pos
            if abs(diff) < abs(closest):
              closest = friend.pos

          # do not get too tight
          diff = closest - pos
          if abs(diff) < 10.0:
            return pos - (10.0 - diff)

          # band together
          if avg == 0:
            return pos
          else:
            return avg
          
      def get_heat(self):
          diff = abs(self.band_pos() - self.puppet.pos)
          return self.scale_value(diff, ((0, 0.01), (2, 0.1), (10, 0.5), (25, 1.0)))
      def update(self):
          self.move_to(self.band_pos())

class AvoidFireballs(Goal, MovementGoal):
      def best_move(self):
          pos  = self.puppet.pos
          base = self.puppet.LifeField.value(pos)
          values = [(ofs, self.puppet.LifeField.value(pos + ofs) - base) for ofs in [-15, -7, -3, +3, +7, +15]]
          best   = pos
          worth  = 0.0
          for ofs, diff in values:
            new_worth = -diff / abs(ofs / 15.0)
            if new_worth > worth:
              best  = pos + ofs
              worth = new_worth
          #print "base=%1.3f best=%u worth=%1.3f values=[%s]" % (base, int(best - pos), worth, " ".join(["%1.3f@%u" % (pair[1], pair[0]) for pair in values]))
          return worth, best
      def get_heat(self):
          worth, pos = self.best_move()
          return self.scale_value(worth, ((0, 0.01), (0.5, 0.3), (1, 1.0)), smooth = True)
      def update(self):
          worth, pos = self.best_move()
          self.move_to(pos)

class SetField(TreeGoal):
      def __init_goal__(self, target, field, value):
          self.target = target
          self.field  = field
          self.balls  = [ field2ball[field] ]
          self.value  = value
      def target_pos(self):
          if isinstance(self.target, Actor): return self.target.pos + self.target.speed
      def add_subgoals(self):
          pos = self.target.pos
          targets = self.world.get_actors(pos - 75.0, pos + 75.0, include = self.balls)
          for target in targets:
            m = p = False
            for goal in self.subgoals:
              if isinstance(goal, MoveBall) and goal.ball == target:
                m = True
              elif isinstance(goal, PowerBall) and goal.ball == target and goal.value == self.value:
                p = True
            if not m:
              self.add_subgoal(MoveBall, target, self.target)
            if not p:
              self.add_subgoal(PowerBall, target, self.value)

          if len(targets) == 0:
            self.add_subgoal(CreateBall, LifeBall)
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
            prios.append(0.9 + (float(n_goals - i) / (n_goals)) * 0.2)
            if isinstance(goal, CreateBall):
              prios[i] *= 3
            else:
              diff = abs(self.target.pos + self.target.speed - goal.ball.pos - goal.ball.speed)
              if isinstance(goal, MoveBall):
                prios[i] *= self.scale_value(diff, ((0, 0.1), (15, 2), (25, 1), (50, 0.7), (100, 0.0)), smooth = True)
              elif isinstance(goal, PowerBall):
                if abs(goal.ball.mult) < 1.0:
                  prios[i] *= 2
                else:
                  prios[i] *= self.scale_value(diff, ((0, 3), (15, 1), (25, 0.5), (100, 0.0)), smooth = True)
            total += prios[i]
          if total == 0.0:
            return
          coef = self.prio / total
          for i in xrange(n_goals):
            self.subgoals[i].prio += prios[i] * coef
            self.subgoals[i].dist_prio()
      del_subgoals = TreeGoal.del_subgoals_limiting

class CreateBall(Goal):
      def __init_goal__(self, balltype):
          self.balltype = balltype
          self.created  = False
      def update(self):
          if not self.created:
            self.magic.new(LifeBall)
            self.created = True
          return True
      def get_heat(self):
          if self.created: return 0.0
          else: return 1.0

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
      def target_pos(self):
          if isinstance(self.target, Actor): return self.target.pos + self.target.speed
          else: return self.target
      def update(self):
          ball = self.ball
          dest = self.target_pos()
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
          diff = self.target_pos() - (self.ball.pos + self.ball.speed)
          score = self.scale_value(abs(diff), ((0, 0.1), (1, 0.5), (5, 0.5), (10, 0.3), (90, 0.3), (150, 0.0)))
          return score

class PowerBall(Goal, MagicGoal):
      def __init_goal__(self, ball, value):
          self.ball  = ball
          self.value = value
      def dest_value(self):
          if self.value == "+":
            return self.puppet.magic_energy
          elif self.value == "-":
            return -self.puppet.magic_energy
          else:
            return self.value
      def update(self):
          self.power(self.ball, self.dest_value())
          return True
      def get_heat(self):
          if self.ball.dead:
            return 0.0
          diff = abs(self.dest_value() - self.ball.mult)
          return self.scale_value(abs(diff), ((0, 0.01), (3, 0.2), (10, 0.6)), smooth = True)
      def dist_prio(self): pass

class BehavingDragon(Dragon):
      prey    = [Dude, Rabbit, Guardian]
      control = Planner
class BehavingVillager(Villager):
      prey    = [Dragon]
      control = Planner
