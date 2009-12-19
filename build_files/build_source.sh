#!/bin/sh

magicdir=$(dirname $0)/..
cd $magicdir

version=$(cat VERSION)
d="magicity-$version"

mkdir $d
cp -r img sound music font $d
cp game.py actors.py fields.py effects.py stories.py $d
cp *.txt $d

tar czf magicity-src-$version.tar.gz $d
rm -rf $d
