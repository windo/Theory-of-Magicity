#!/bin/sh

magicdir=$(dirname $0)/..
cd $magicdir

version=$(cat VERSION)
d="magicity-$version"

mkdir $d
cp -r img sound music font lib doc $d
cp game.py $d

tar czf magicity-src-$version.tar.gz $d
rm -rf $d
