#!/bin/sh
PACKAGE="spynner"
URL="http://code.google.com/p/spynner"
OUTPUT="docs/api"
SOURCE="spynner/browser.py"

epydoc --html --no-private --no-sourcecode -n $PACKAGE \
    -u "$URL" -o $OUTPUT $SOURCE
