--[ Theory of Magicity ]--

For windows distribution, you should be able to just run the magicity.exe
and the game should run. If you want to build the windows binary, you need
python, pygame, py2exe, numpy and python-opengl.

For real operating systems, you should make sure that you have pygame
installed, for example, on Debian:
apt-get install python-pygame

and then you can run:
./game.py

--[ Authorship ]--

This is a game written for games and interactive systems development course
(IDX5060) in the autumn of 2009 in Tallinn University of Technology. All of the
game and it's resources are written/composed/drawn by Siim Poder for this
course, except for:
 * the fonts in font/ directory, they have their own licenses there
 * python, pygame, SDL, py2exe, pygame2exe.py - all GPL I believe

--[ Game Idea ]--

The idea of the game is to take magic out of it's usual canned role, where
a single "spell" has strictly specified effects (although often complex) and
rather try to treat magic as physics is treated in games.

That is, try to invent a physics-like system that would cover (some part of)
what magic usually does in games.

To this end, a few "magic fields" are used in this game. Since this game is
basically a one-dimensional side-scroller, a magic field is also a one-
dimensional continuous value: For each position in the game world, the value
of magic field can be calculated into a value of that field at that position.

Each field can be affected by "magic balls". When a game inhabitant makes a
magic ball, it will appear next to them and either increase or decrease the
field value around itself (inversely proportionally to the distance from the
ball).

Each field has one or more effects on the inhabitants of the game world.
Currently (at the time of writing) the effects are such:
 * Regenerate HP fast <-> decrease HP fast
 * Add more magic energy <-> Subtract magic energy
 * Increase moving speed by a multiplier <-> Decrease moving speed by a multiplier
 * Add a value to moving speed <-> Subtract a value from moving speed

Other ideas:
 * Make objects appear closer <-> Hide objects from sight

To be more compatible with "usual" magic, elemental (fire, earth, water, air,
life, undead, etc) fields could be used, although for this game, it seemed to
be a good idea to keep the number of different fields low, 3 currently.

Also, currently each magic ball affects just one field, but more interesting
results may be possible if they would affect various fields at once, would have
different value distribtions (currently close to normal distribution).

The initial idea was to build normal spells such as "fireball", "haste",
"invisibility" and so forth upon this physics-like system. However, it was too
complex task for this small game (and the course deadline).

--[ Levels ]--

Currently just 2 levels are implemented:

Firstly, a tutorial level where the player is instructed how the magic controls
work and an objective to defeat 3 (small) dragons slaughtering cute bunnies.

Secondly, a level where dragons keep appearing and the objective being getting
past two "guardians" who try to block your path by using the "decrease moving
speed by a multiplier" field to stop all movement past them.
