import pygame, time, math

import actors
from fields import all as fieldtypes

import pygame
from pygame.locals import *

class GameControl:
      def __init__(self, world, player):
          self.world = world
          self.player = player

          self.draw_debug = False

      def handle(self, event):
          player = self.player
          world = self.world
          cam = world.camera

          # keyboard
          if event.type == KEYDOWN:
            if event.key == K_p:
              world.pause()
            elif event.key == K_o:
              world.set_speed(world.get_speed() - 0.1)
            elif event.key == K_i:
              world.set_speed(world.get_speed() + 0.1)

            # explicit camera control
            elif event.key == K_j:
              cam.pan_x(-25.0)
            elif event.key == K_k:
              cam.follow(player)
            elif event.key == K_l:
              cam.pan_x(+25.0)

            # mode switching
            elif event.key == K_TAB:
              self.draw_debug = not self.draw_debug

          elif event.type == MOUSEBUTTONDOWN:
            if event.button == 3:
              pos = cam.sc2pl_x(event.pos[0])
              candidates = world.get_actors(pos - 5, pos + 5)
              if candidates:
                # find the closest particle
                closest = 5
                select  = False
                for actor in candidates:
                  dist = abs(actor.pos - pos)
                  if dist < closest:
                    closest = dist
                    select = actor
                if select:
                  select.debug_me ^= 1

class CharacterControl:
      def __init__(self, world, player):
          self.world = world
          self.player = player

          # boolean: capture magic balls
          self.get_magic = False
          self.local_balls = []
          # reference to selected magic ball or False
          self.sel_magic = False
          # boolean: currently ball selected with mouse
          self.mouse_control = False
          # boolean: use 'a' and 'd' to control player
          self.mouse_mode = False
          
      def handle(self, event):
          player = self.player
          world = self.world
          cam = world.camera

          if self.get_magic:
            self.local_balls = world.get_actors(player.pos - 100, player.pos + 100, include = [ actors.MagicParticle ])

          if event.type == KEYDOWN:
            # player moving
            if event.key == K_LEFT:
              player.move_left()
            elif event.key == K_RIGHT:
              player.move_right()
            # mouse_mode player moving
            elif self.mouse_mode and event.key == K_a:
              player.move_left()
            elif self.mouse_mode and event.key == K_d:
              player.move_right()
  
            # mode switching
            elif event.key == K_LCTRL or event.key == K_RCTRL:
              self.get_magic  = True
              if self.sel_magic:
                self.sel_magic.selected = False
                self.sel_magic = False
            elif event.key == K_m:
              self.mouse_mode = not self.mouse_mode
            
            # cast magic balls
            elif event.key == K_z:
              if self.sel_magic:
                self.sel_magic.selected = False
              self.sel_magic = player.magic.new(actors.TimeBall)
              self.sel_magic.selected = True
            elif event.key == K_x:
              if self.sel_magic:
                self.sel_magic.selected = False
              self.sel_magic = player.magic.new(actors.WindBall)
              self.sel_magic.selected = True
            elif event.key == K_c:
              if self.sel_magic:
                self.sel_magic.selected = False
              self.sel_magic = player.magic.new(actors.LifeBall)
              self.sel_magic.selected = True
  
            # recapture existing particles
            elif self.get_magic and event.key >= K_1 and event.key <= K_9:
              idx = event.key - K_1
              if len(self.local_balls) > idx:
                if self.sel_magic:
                  self.sel_magic.selected = False
                self.sel_magic = self.local_balls[idx]
                self.sel_magic.selected = True
                player.magic.capture(self.sel_magic)
            elif self.get_magic and (event.key == K_a or event.key == K_d):
              # select ball with arrow keys
              if self.sel_magic:
                refpos = self.sel_magic.pos
              else:
                refpos = player.pos
              # look for ball in right direction
              captured_ball = False
              for ball in self.local_balls:
                if event.key == K_a:
                  if ball.pos < refpos:
                    captured_ball = ball
                elif event.key == K_d:
                  if ball.pos > refpos:
                    captured_ball = ball
                    break
              if captured_ball:
                if self.sel_magic:
                  self.sel_magic.selected = False
                self.sel_magic = captured_ball
                self.sel_magic.selected = True
                player.magic.capture(self.sel_magic)
  
            # magic moving
            elif self.sel_magic and event.key == K_a:
              player.magic.move(self.sel_magic, diff = -3.0)
            elif self.sel_magic and event.key == K_d:
              player.magic.move(self.sel_magic, diff = 3.0)
            elif self.sel_magic and event.key == K_w:
              player.magic.power(self.sel_magic, diff = 3.0)
            elif self.sel_magic and event.key == K_s:
              player.magic.power(self.sel_magic, diff = -3.0)
  
            # release magic
            elif self.sel_magic and event.key == K_r:
              if self.sel_magic:
                player.magic.release(self.sel_magic)
                self.sel_magic.selected = False
                self.sel_magic = False
            elif event.key == K_r:
              player.magic.release_all()
              if self.sel_magic:
                self.sel_magic.selected = False
                self.sel_magic = False
  
          # key releases
          elif event.type == KEYUP:
            # movement
            if event.key == K_LEFT:
              player.stop()
            elif event.key == K_RIGHT:
              player.stop()
            elif self.mouse_mode and event.key == K_a:
              player.stop()
            elif self.mouse_mode and event.key == K_d:
              player.stop()
  
            # magic movement
            elif self.sel_magic and event.key == K_a:
              player.magic.move(self.sel_magic, 0.0)
            elif self.sel_magic and event.key == K_d:
              player.magic.move(self.sel_magic, 0.0)
  
            # input modes
            elif event.key == K_LCTRL or event.key == K_RCTRL:
              self.get_magic = False
  
          ## mouse
          elif event.type == MOUSEBUTTONDOWN:
            if event.button == 1:
              pos = cam.sc2pl_x(event.pos[0])
              particles = world.get_actors(pos - 5, pos + 5, include = [actors.MagicParticle])
              if particles:
                # find the closest particle
                closest = 5
                for particle in particles:
                  dist = abs(particle.pos - pos)
                  if dist < closest:
                    closest = dist
                    new_particle = particle
                # deselect old
                if self.sel_magic:
                  self.sel_magic.selected = False
                # capture, select
                self.sel_magic = new_particle
                player.magic.capture(self.sel_magic)
                self.sel_magic.selected = True
                self.mouse_control      = True
                pygame.mouse.set_visible(False)
  
          elif event.type == MOUSEBUTTONUP:
            if event.button == 1:
              self.mouse_control = False
              pygame.mouse.set_visible(True)
              if self.sel_magic:
                player.magic.move(self.sel_magic, 0)
  
          elif event.type == MOUSEMOTION and self.mouse_control and self.sel_magic:
            x, y = event.rel
            player.magic.move(self.sel_magic, diff = x / 2)
            player.magic.power(self.sel_magic, diff = -y / 2)
