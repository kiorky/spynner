#!/usr/bin/python
#
# Copyright (c) 2008-2009 Arnau Sanchez <tokland@gmail.com>

# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>

import itertools
import cookielib
import tempfile
import urlparse
import urllib2
import time
import sys
import os

from PyQt4.QtCore import SIGNAL, QUrl, QEventLoop, QString, Qt
from PyQt4.QtGui import QApplication
from PyQt4.QtNetwork import QNetworkCookieJar, QNetworkAccessManager, QNetworkReply
from PyQt4.QtWebKit import QWebPage, QWebView

# Debug level
ERROR, WARNING, INFO, DEBUG = range(4)

JSCODE_EXTRA = """
    jQuery.noConflict();
"""

def first(iterable, pred=bool):
    """Return first item in iterator that matches the predicate"""
    for item in iterable:
        if pred(item):
            return item

def debug(obj, linefeed=True, outfd=sys.stderr):
    """Print a debug info line to standard error channel"""
    strobj = str(obj) + ("\n" if linefeed else "")
    outfd.write(strobj)
    outfd.flush()

def load_files(directories, files):
    """Look for and existing directory in 'directories' and 
    return concatenation of 'files' contents."""
    directory = first(directories, os.path.isdir)
    if directory:
        return [open(os.path.join(directory, fn)).read() for fn in files]
     
def get_opener(mozilla_cookies):
    """Open a cookies file and return a urllib2 opener object"""
    if not mozilla_cookies:
        return urllib2.build_opener()
    cookies = cookielib.MozillaCookieJar()
    temp_cookies = tempfile.NamedTemporaryFile()
    temp_cookies.write(mozilla_cookies)
    temp_cookies.flush()
    cookies.load(temp_cookies.name)
    return urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
   
def download(url, opener, outfd=None, bufsize=4096):
    """Download a URL using a urllib2.opener (which may contain cookies).
    
    Returns data read if outfd is None, total bytes downloaded otherwise."""
    infd = opener.open(url)
    output = []
    while 1:
        data = infd.read(bufsize)
        if not data:
            break
        if outfd:
            outfd.write(data)
            output.append(len(data))
        else: 
            output.append(data)
    return sum(output) if outfd else "".join(output)

class SpynnerError(Exception):
    pass

class SpynnerTimeoutError(Exception):
    pass

class SpynnerJavascriptError(Exception):
    pass
                   
class NetworkCookieJar(QNetworkCookieJar):
    def mozillaCookies(self, domain_flag=False):
        """
        Return string containing all cookies in cookie jar in
        text Mozilla cookies format:
        
        # domain domain_flag path secure_connection expiration name value
        .firefox.com     TRUE   /  FALSE  946684799   MOZILLA_ID  100103        
        """
        header = ["# Netscape HTTP Cookie File"]        
        def bool2str(value):
            return {True: "TRUE", False: "FALSE"}[value]
        def get_line(cookie):
            return "\t".join([
                str(cookie.domain()),
                bool2str(domain_flag),
                str(cookie.path()),
                bool2str(cookie.isSecure()),
                str(cookie.expirationDate().toTime_t()),
                str(cookie.name()),
                str(cookie.value()),
            ])
        lines = [get_line(cookie) for cookie in self.allCookies() 
          if not cookie.isSessionCookie()]
        return "\n".join(header + lines)

class Browser:
    javascript_files = [
        "jquery.min.js", 
        "jquery.simulate.js"
    ]

    javascript_directories = [
        os.path.join(os.path.dirname(__file__), "../javascript"), 
        "/usr/share/spynner/javascript",
    ]
    
    def __init__(self, webview=False, jqueryfiles=None, qappargs=None,
            verbose_level=ERROR, debugfd=sys.stderr):
        self.verbose_level = verbose_level
        self.debugfd = debugfd
        self.app = QApplication(qappargs or [])
        self.webpage = QWebPage()
        self.webframe = self.webpage.mainFrame()
        if webview:
            self.webview = QWebView()
            self.webview.setPage(self.webpage)
            window = self.webview.window()
            window.setAttribute(Qt.WA_DeleteOnClose)
            window.connect(window, SIGNAL('destroyed(QObject *)'),
                self._on_webview_destroyed)
        else:
            self.webview = None
            
        # Javascript
        self.javascript = "".join(load_files(self.javascript_directories, 
            self.javascript_files))
        if self.javascript is None:
            raise SpynnerError("Cannot find javascript directory: %s" %
                directories) 

        self.webpage.javaScriptAlert = self._javascript_alert                
        self.webpage.javaScriptConsoleMessage = self._javascript_console_message
        
        # Manager and cookies
        self.manager = QNetworkAccessManager()
        self.manager.createRequest = self._manager_create_request 
        self.webpage.setNetworkAccessManager(self.manager)            
        self.cookiesjar = NetworkCookieJar()
        self.manager.setCookieJar(self.cookiesjar)
        self.operation_names = dict((getattr(QNetworkAccessManager, s+"Operation"),
            s.lower()) for s in ("Get", "Head", "Post", "Put"))
        
       # Webpage signals
        self.webpage.setForwardUnsupportedContent(True)
        self.webpage.connect(self.webpage,
            SIGNAL('unsupportedContent(QNetworkReply *)'), 
            self._on_unsupported_content)
        self.webpage.connect(self.webpage, SIGNAL('loadFinished(bool)'),
            self._on_finished_loading)
        self.manager.connect(self.manager, SIGNAL('finished(QNetworkReply *)'),
            self._on_reply)

    def _debug(self, level, *args):
        if level <= self.verbose_level:
            debug(*args, outfd=self.debugfd)

    def _manager_create_request(self, operation, request, data):
        url = str(request.url().toString())
        operation_name = self.operation_names[operation].upper()
        self._debug(INFO, "Request: %s %s" % (operation_name, url))
        for h in request.rawHeaderList():
            self._debug(DEBUG, "  %s: %s" % (h, request.rawHeader(h)))
        return QNetworkAccessManager.createRequest(self.manager, operation, 
            request, data)

    def _on_unsupported_content(self, reply):
        url = str(reply.url().toString())
        urlinfo = urlparse.urlsplit(url)
        path = urlinfo.netloc + urlinfo.path
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))        
        self.download(url, outfd=open(path, "wb"))

    def _on_reply(self, reply):
        url = str(reply.url().toString())
        if reply.error():
            self._debug(INFO, "Reply error: %s - %d (%s)" % (url, reply.error(),
                reply.errorString()))
            # raise Exception on error?
        else: 
            self._debug(INFO, "Reply successful: %s" % url)
        for header in reply.rawHeaderList():
            self._debug(DEBUG, "  %s: %s" % (header, reply.rawHeader(header)))
                             
    def _javascript_alert(self, webframe, message):
        self._debug(ERROR, "Javascript alert: %s" % message)
        
    def _javascript_console_message(self, message, linenumber, sourceid):
        if linenumber:
            self._debug(ERROR, "Javascript console (%s:%d): %s" %
                (sourceid, linenumber, message))
        else:
            self._debug(ERROR, "Javascript console: %s" % message)
                                             
    def _on_webview_destroyed(self, window):
        self.webview = None
                                             
    def _on_finished_loading(self, successful):        
        self._finished_loading = True  
        status = {True: "successful", False: "error"}[successful]
        self._debug(DEBUG, "Page load finished (%d bytes): %s (%s)" % 
            (len(self.get_html()), self.get_url(), status))

    def _process(self, timeout=None, looptime=0.01):
        self._finished_loading = False
        itime = time.time()
        while not self._finished_loading:
            if timeout and time.time() - itime > timeout:
                raise SpynnerTimeoutError("Timeout reached: %d seconds" % timeout)
            time.sleep(looptime)
            self.app.processEvents(QEventLoop.AllEvents)
        self.runjs(self.javascript+JSCODE_EXTRA, debug=False)
        return self.get_html()

    def _runjs_on_jquery(self, name, code):
        """Check input checkbox to value (True by default)."""
        def _get_js_obj_length(res):
            if res.type() != res.Map:
                return False
            resmap = res.toMap()
            lenfield = QString(u'length')
            if lenfield not in resmap:
                return False
            return resmap[lenfield].toInt()[0]
        res = self.runjs(code)
        if _get_js_obj_length(res) < 1:
            raise SpynnerJavascriptError("error on %s: %s" % (name, code))
        
    # Public interface

    def load(self, url):
        """Load a page from its URL and return rendered HTML."""
        self.webframe.load(QUrl(url))
        return self._process()

    def show(self):
        """Show web-browser window."""
        self.webview.show()

    def hide(self):
        """Hide web-browser window."""
        self.webview.hide()

    def close(self):
        """Close browser object."""
        if self.webview:
            del self.webview
        if self.webpage:
            del self.webpage
        
    def wait(self, waitime, looptime=0.01):
        """Wait 'waitime' seconds and return.
        
        The page rendering loop is enabled, so you can call this function
        to wait for DOM changes (due to syncronous Javascript events)."""   
        itime = time.time()
        while time.time() - itime < waitime:
            self.app.processEvents()
            time.sleep(looptime)        

    def wait_redirect(self, timeout=None):
        """Click link or button."""
        return self._process(timeout)
                
    def browse(self, looptime=0.01):
        """Let the user browse the current page (infinite loop).""" 
        if not self.webview:
            raise SpynnerError("Cannot browse with webview disabled")
        self.show()
        while self.webview:
            self.app.processEvents()
            time.sleep(looptime)

    def get_html(self):
        """Get current HTML for this web frame."""
        return unicode(self.webframe.toHtml())
    
    def get_url(self):
        """Get current URL for this web frame."""
        return unicode(self.webframe.url().toString())

    def fill(self, selector, value):
        """Fill an input text with value."""
        JSCODE_EXTRA = "jQuery('%s').val('%s')" % (selector, value)
        self._runjs_on_jquery("fill", JSCODE_EXTRA)

    def click(self, selector):
        """Click link or button."""
        JSCODE_EXTRA = "jQuery('%s').simulate('click')" % selector
        #JSCODE_EXTRA = "jQuery('%s')[0].dispatchEventy(evObj)" % selector
        self._runjs_on_jquery("click", JSCODE_EXTRA)
        return self._process()         

    def check(self, selector):
        """Check input checkbox to value (True by default)."""
        JSCODE_EXTRA = "jQuery('%s').attr('checked', true)" % selector
        self._runjs_on_jquery("check", JSCODE_EXTRA)

    def uncheck(self, selector):
        """Check input checkbox."""
        JSCODE_EXTRA = "jQuery('%s').attr('checked', false)" % selector
        self._runjs_on_jquery("uncheck", JSCODE_EXTRA)

    def choose(self, selector):        
        """Choose a radio input."""
        JSCODE_EXTRA = "jQuery('%s').simulate('click')" % selector
        self._runjs_on_jquery("choose", JSCODE_EXTRA)

    def select(self, selector, value):        
        """Choose a radio input."""
        JSCODE_EXTRA = "jQuery('%s option[value=%s]').attr('selected', 'selected')" \
            % (selector, value)
        self._runjs_on_jquery("select", JSCODE_EXTRA)
        
    def runjs(self, JSCODE_EXTRA, debug=True):
        """Run arbitrary Javascript code into the current frame."""
        if debug:
            self._debug(DEBUG, "Run Javascript code: %s" % JSCODE_EXTRA)
        return self.webpage.mainFrame().evaluateJavaScript(JSCODE_EXTRA)

    def get_mozilla_cookies(self):
        """Return string with current cookies in Mozilla format.""" 
        return self.cookiesjar.mozillaCookies()
    
    def download(self, url, outfd=None, bufsize=4096*16, cookies=None):
        """Download given URL using current cookies."""        
        if cookies is None:
            cookies = self.get_mozilla_cookies()
        self._debug(INFO, "Downloading URL: %s" % url)        
        self._debug(DEBUG, "Using cookies: %s" % cookies)
        opener = get_opener(cookies)
        return download(url, opener, outfd, bufsize)

    def get_url_from_path(self, path):
        """Return the URL for a given path using current URL as base."""
        return urlparse.urljoin(self.get_url(), path.lstrip('/'))
