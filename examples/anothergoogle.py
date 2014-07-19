#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
__docformat__ = 'restructuredtext en'

import logging
import os
import re
import tempfile

from lxml.html import document_fromstring
from spynner import browser
from PyQt4 import QtCore


FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)
logging.getLogger('test scrapper').debug("start")
re_flags = re.M|re.U|re.S|re.X
os.environ['DISPLAY'] = os.environ.get('GMB_DISPLAY', ':1')

def get_tree(h):
    """h can be either a zc.testbrowser.Browser or a string."""
    if isinstance(h, file):
        h = h.read()
    if isinstance(h, browser.Browser):
        h = h.html
    if not isinstance(h, basestring):
        h = h.contents
    return document_fromstring(h)


def getQtBrowser(download_directory=None):
    debug=4
    br = browser.Browser(embed_jquery=True,
                         debug_level=debug,)
    br.download_directory = download_directory
    return br

def get_url(url, path):
    if not (path.startswith('http://')
            or path.startswith('https://')):
            path = '%s/%s' % (url, path)
    return path


def main(download_directory=None):
    logger = logging.getLogger('scrapper.test')
    if not download_directory:
        download_directory = tempfile.mkdtemp()
    br = getQtBrowser(download_directory)
    br.create_webview()
    br.webview.show()
    br.webview.setWindowState(QtCore.Qt.WindowMaximized)
    br.load('http://www.google.com')
    def can_continuea(abrowser):
        t = get_tree(abrowser)
        return len(t.xpath("//input[@name='q']")) > 0
    br.wait_for_content(can_continuea, 60, u'Timeout while loading account data')
    br.fill('input[name="q"]', 'kiorky')
    t = get_tree(br)
    name = [a.attrib['name']
            for a in  t.xpath('//input[@type="submit"]')
            if 'google' in a.value.lower()][0]
    # search for the search input control which can change id
    input_sel = "input[name='%s']" % name
    # remodve the search live query ...
    br.native_click('input[name="q"]')
    br.click(input_sel)
    def can_continueb(abrowser):
        t = get_tree(abrowser)
        return len( t.xpath('//*[@id="ires"]')) > 0
    br.wait_for_content(can_continueb, 60, u'Timeout while loading account data')
    assert 'cryptelium.net' in br.html


if __name__ == '__main__':
    print(main())

# vim:set et sts=4 ts=4 tw=80:
