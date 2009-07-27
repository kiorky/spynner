#!/bin/sh
PACKAGE="spynner"
URL="http://code.google.com/p/spynner"
OUTPUT="docs/api"
SOURCE="spynner/browser.py"

mkdir -p "$OUTPUT"
epydoc -v --html --no-private --no-sourcecode -n $PACKAGE \
    -u "$URL" -o $OUTPUT $SOURCE
[ "$1" = upload ] && { 
  DEST="tokland.freehostia.com/googlecode/spynner/api"
  echo -e "set ftp:passive-mode on\nmirror -R $OUTPUT $DEST" | \
    lftp -d armsam7:1477456@tokland.freehostia.com
}
