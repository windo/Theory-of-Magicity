#!/usr/bin/python
import pstats

s = pstats.Stats("game.stats")
s = s.sort_stats('time')
s.print_stats(0.1)
s.print_callees("opengl_blit")
#s = s.sort_stats('cumulative')
#s.print_stats(0.1)
