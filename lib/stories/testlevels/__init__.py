from testbed import TestBed, KillTest
from mass import MassBehaving, MassHunting
all    = [TestBed, KillTest, MassBehaving, MassHunting]
byname = {}
for s in all: byname[s.__name__] = s
