#!/bin/sh
set -e
export PYTHONPATH=. 

PYQT_VERSION=$(echo "from PyQt4.QtCore import PYQT_VERSION_STR as version; print version" | python)

echo "System: $(uname -s -r -m -i -o)"
echo "Python: $(python --version 2>&1 | awk '{print $2}')"
echo "PyQT: $PYQT_VERSION"
echo
python test/test_browser.py -vv
