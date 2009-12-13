#!/bin/sh

wine 'C:\Python25\python.exe' build_win32_pygame2exe.py py2exe
cp /home/siim/.wine/drive_c/Python25/Lib/site-packages/pygame/*.dll dist/
#cp /home/siim/.wine/drive_c/windows/system32/python25.dll dist/
#wine dist/game.exe
#cat dist/game.exe.log

version=$(cat VERSION)
mv dist/game.exe dist/magicity.exe
mv dist magicity-$version
zip -r magicity-win32-$version.zip magicity-$version
rm -rf magicity-$version
