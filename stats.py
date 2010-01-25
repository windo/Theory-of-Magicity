#!/usr/bin/python
import pstats

s = pstats.Stats("game.stats")
s = s.sort_stats('time')
s.print_stats(0.1)
s.print_callers("get_")
#s = s.sort_stats('cumulative')
#s.print_stats(0.1)
