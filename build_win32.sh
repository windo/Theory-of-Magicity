#!/bin/sh
wineconsole build_win32.bat
cat build.log
cp /home/siim/.wine/drive_c/Python25/Lib/site-packages/pygame/*.dll dist/
#cp /home/siim/.wine/drive_c/windows/system32/python25.dll dist/
wine dist/game.exe
cat dist/game.exe.log
