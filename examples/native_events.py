#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'

from PyQt4 import QtCore
from spynner import browser
from time import sleep

br = browser.Browser(
#    debug_level=4
)
br.load('http://pypi.python.org/pypi')
try:
    br.wait_load(5)
except:
    pass
br.create_webview()
br.show()

br.wk_fill('input[id=term]', 'spynner') 
br.native_click('input[id=submit]', offsetx=5, offsety=5)
print "Saw the mouse on the logo move & click on the search input"
sleep(3)
print "press any key"
raw_input()

br.sendText('input[id=term]', 'spynner') 
#print "Noticed spynner in the input ?"    vim:set et sts=4 ts=4 tw=80:
sleep(3)                                 
