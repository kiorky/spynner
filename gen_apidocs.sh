#!/bin/sh
set -e

PACKAGE="spynner"
URL="http://code.google.com/p/spynner"
OUTPUT="docs/api"
SOURCE="spynner/browser.py"

mkdir -p $OUTPUT
epydoc -v --html --fail-on-docstring-warning --no-private --no-sourcecode \
  -n $PACKAGE -u "$URL" -o $OUTPUT $SOURCE
