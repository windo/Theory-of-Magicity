#!/bin/sh

magicdir=$(dirname $0)/..
cd $magicdir

# the cherade with the file path do satisfy library loading
ln -s build_files/build_win32_pygame2exe.py .
wine 'C:\Python25\python.exe' build_win32_pygame2exe.py py2exe
rm build_win32_pygame2exe.py
cp /home/siim/.wine/drive_c/Python25/Lib/site-packages/pygame/*.dll dist/
cp build_files/msvcr71.dll dist/
#cp /home/siim/.wine/drive_c/windows/system32/python25.dll dist/
#wine dist/game.exe
#cat dist/game.exe.log

version=$(cat VERSION)
mv dist/game.exe dist/magicity.exe
mv dist magicity-$version
zip -r magicity-win32-$version.zip magicity-$version
rm -rf magicity-$version
