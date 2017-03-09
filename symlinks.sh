#!/usr/bin/env bash

##
## Script for replacing git symlinks with real symlinks
## git ls-files -s | %{ if ($_.Split(' ')[0] -match "120000") { $_; } } (Windows)
##

for FILENAME in $(git ls-files -s | awk '/120000/{print $4}')
do
  FULLPATH=$(readlink --canonicalize $(dirname $FILENAME)/$(cat $FILENAME))
  rm -Rf $FILENAME
  ln -s $FULLPATH $FILENAME
  git update-index --assume-unchanged $FILENAME
  echo $FILENAME "=>" $FULLPATH
done

