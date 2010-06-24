#!/bin/bash

./gprof2dot.py -f pstats game.stats | dot -Tpng -o output.png
display output.png
