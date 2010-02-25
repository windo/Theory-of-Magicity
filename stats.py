#!/usr/bin/python
import pstats, sys

s = pstats.Stats("game.stats")
s = s.sort_stats('time')
s.print_stats(0.1)
s = s.sort_stats('cumulative')
s.print_stats(0.1)

if len(sys.argv) > 1:
  s.print_callees(sys.argv[1])
  s.print_callers(sys.argv[1])
