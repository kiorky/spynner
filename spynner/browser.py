#!/usr/bin/python

# Copyright (c) Arnau Sanchez <tokland@gmail.com>

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
import re
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
    """Return first element in iterator that matches the predicate"""
    for item in iterable:
        if pred(item):
            return item

def debug(obj, linefeed=True, outfd=sys.stderr, outputencoding="utf8"):
    """Print a debug info line to stream channel"""
    if isinstance(obj, unicode):
        obj = obj.encode(outputencoding)
    strobj = str(obj) + ("\n" if linefeed else "")
    outfd.write(strobj)
    outfd.flush()
     
def get_opener(mozilla_cookies=None):
    """Return a urllib2 opener object using (optional) mozilla cookies string"""
    if not mozilla_cookies:
        return urllib2.build_opener()
    cookies = cookielib.MozillaCookieJar()
    temp_cookies = tempfile.NamedTemporaryFile()
    temp_cookies.write(mozilla_cookies)
    temp_cookies.flush()
    cookies.load(temp_cookies.name)
    return urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
   
def download(url, opener, outfd=None, bufsize=4096):
    """Download a URL using a urllib2.opener.
    
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

class SpynnerPageError(Exception):
    pass

class SpynnerTimeout(Exception):
    pass

class SpynnerJavascriptError(Exception):
    pass
                   
class NetworkCookieJar(QNetworkCookieJar):
    def mozillaCookies(self):
        """
        Return string containing all cookies in cookie jar in
        text Mozilla cookies format:
        
        # domain domain_flag path secure_connection expiration name value
        
        .firefox.com     TRUE   /  FALSE  946684799   MOZILLA_ID  100103        
        """
        header = ["# Netscape HTTP Cookie File"]        
        def bool2str(value):
            return {True: "TRUE", False: "FALSE"}[value]
        def byte2str(value):            
            return str(value)        
        def get_line(cookie):
            domain_flag = str(cookie.domain()).startswith(".")
            return "\t".join([
                byte2str(cookie.domain()),
                bool2str(domain_flag),
                byte2str(cookie.path()),
                bool2str(cookie.isSecure()),
                byte2str(cookie.expirationDate().toTime_t()),
                byte2str(cookie.name()),
                byte2str(cookie.value()),
            ])
        lines = [get_line(cookie) for cookie in self.allCookies() 
          if not cookie.isSessionCookie()]
        return "\n".join(header + lines)

class Browser:  
    ignore_ssl_errors = True
    """@ivar: If True, ignore SSL certificate errors."""
    debug_stream = sys.stderr
    """@ivar: Stream where debug output will be written."""
    debug_level = ERROR
    """@ivar: Debug verbose level."""
    
    javascript_files = [
        "jquery.min.js", 
        "jquery.simulate.js"
    ]

    javascript_directories = [
        os.path.join(os.path.dirname(__file__), "../javascript"),
        os.path.join(sys.prefix, "share/spynner/javascript"),
    ]
    
    def __init__(self, qappargs=None, debug_level=None):
        self.event_looptime = 0.01
        self.app = QApplication(qappargs or [])
        if debug_level is not None:
            self.debug_level = debug_level
        self.webpage = QWebPage()
        self.webframe = self.webpage.mainFrame()
        self.webview = None
        self.reply = None
            
        # Javascript
        directory = first(self.javascript_directories, os.path.isdir)
        if not directory:
            raise SpynnerError("Cannot find javascript directory: %s" %
                self.javascript_directories)           
        self.javascript = "".join(open(os.path.join(directory, fn)).read() 
            for fn in self.javascript_files)

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
        self.manager.connect(self.manager, 
            SIGNAL("sslErrors (QNetworkReply *, const QList<QSslError> &)"),
            self._on_manager_ssl_errors)
        
       # Webpage signals
        self.webpage.setForwardUnsupportedContent(True)
        self.webpage.connect(self.webpage,
            SIGNAL('unsupportedContent(QNetworkReply *)'), 
            self._on_unsupported_content)
        self.webpage.connect(self.webpage, 
            SIGNAL('loadFinished(bool)'),
            self._on_load_status)
        self.manager.connect(self.manager, 
            SIGNAL('finished(QNetworkReply *)'),
            self._on_reply)

    def _debug(self, level, *args):
        if level <= self.debug_level:
            kwargs = dict(outfd=self.debug_stream)
            debug(*args, **kwargs)

    def _on_manager_ssl_errors(self, reply, errors):
        if self.ignore_ssl_errors:
            url = unicode(reply.url().toString())
            self._debug(WARNING, "SSL certificate error ignored: %s" % url)
            reply.ignoreSslErrors()

    def _manager_create_request(self, operation, request, data):
        url = unicode(request.url().toString())
        operation_name = self.operation_names[operation].upper()
        self._debug(INFO, "Request: %s %s" % (operation_name, url))
        for h in request.rawHeaderList():
            self._debug(DEBUG, "  %s: %s" % (h, request.rawHeader(h)))
        return QNetworkAccessManager.createRequest(self.manager, operation, 
            request, data)

    def _on_unsupported_content(self, reply):
        url = unicode(reply.url().toString())
        urlinfo = urlparse.urlsplit(url)
        if urlinfo.scheme == "http":
            path = urlinfo.netloc + urlinfo.path
            if not os.path.isdir(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            self.download(url, outfd=open(path, "wb"))            

    def _on_reply(self, reply):
        self.reply = reply 
        url = unicode(reply.url().toString())
        if reply.error():
            self._debug(WARNING, "Reply error: %s - %d (%s)" % 
                (url, reply.error(), reply.errorString()))
            #raise SpynnerPageError("Error on reply: %s" % reply.errorString())
        else:
            self._debug(INFO, "Reply successful: %s" % url)
        for header in reply.rawHeaderList():
            self._debug(DEBUG, "  %s: %s" % (header, reply.rawHeader(header)))
                             
    def _javascript_alert(self, webframe, message):
        self._debug(INFO, "Javascript alert: %s" % message)
        if self.webview:
            QWebPage.javaScriptAlert(self.webpage, webframe, message)
        
    def _javascript_console_message(self, message, line, sourceid):
        if line:
            self._debug(INFO, "Javascript console (%s:%d): %s" %
                (sourceid, line, message))
        else:
            self._debug(INFO, "Javascript console: %s" % message)
                                             
    def _on_webview_destroyed(self, window):
        self.webview = None
                                             
    def _on_load_status(self, successful):        
        self._load_status = successful  
        status = {True: "successful", False: "error"}[successful]
        self._debug(INFO, "Page load finished (%d bytes): %s (%s)" % 
            (len(self.get_html()), self.get_url(), status))

    def _wait_page_load(self, timeout=None):
        self._load_status = None
        itime = time.time()
        while self._load_status is None:
            if timeout and time.time() - itime > timeout:
                raise SpynnerTimeout("Timeout reached: %d seconds" % timeout)
            time.sleep(self.event_looptime)
            self.app.processEvents(QEventLoop.AllEvents)
        if self._load_status:
            self.runjs(self.javascript + JSCODE_EXTRA, debug=False)
        return self._load_status

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

    def _get_protocol(self, url):
        match = re.match("^(\w+)://", url)
        return (match.group(1) if match else None)
        
    # Public interface

    def load(self, url):
        """Load a web page and return status boolean."""
        self.webframe.load(QUrl(url))
        return self._wait_page_load()

    def create_webview(self):
        """Create a QWebView object and insert current QWebPage."""
        self.webview = QWebView()
        self.webview.setPage(self.webpage)
        window = self.webview.window()
        window.setAttribute(Qt.WA_DeleteOnClose)
        window.connect(window, SIGNAL('destroyed(QObject *)'),
            self._on_webview_destroyed)

    def destroy_webview(self):
        """Destroy current QWebView."""
        if not self.webview:
            raise SpynnerError("Cannot remove webview (not initialized)")
        del self.webview 

    def show(self):
        """Show browser window."""
        if not self.webview:
            raise SpynnerError("Cannot show window when webview disabled")
        self.webview.show()

    def hide(self):
        """Hide browser window."""
        if not self.webview:
            raise SpynnerError("Cannot hide window when webview disabled")
        self.webview.hide()

    def close(self):
        """Close Browser instance and release resources."""
        if self.webview:
            del self.webview
        if self.webpage:
            del self.webpage
        
    def wait(self, waitime):
        """Wait some time.
        
        The event and rendering loop is enabled, so you can call this function
        to wait for DOM changes (due to syncronous Javascript events)."""   
        itime = time.time()
        while time.time() - itime < waitime:
            self.app.processEvents()
            time.sleep(self.event_looptime)        

    def wait_page_load(self, timeout=None):
        """Wait until a new page is loaded."""
        return self._wait_page_load(timeout)
                
    def browse(self):
        """Let the user browse the current page (infinite loop).""" 
        if not self.webview:
            raise SpynnerError("Cannot browse with webview disabled")
        self.show()
        while self.webview:
            self.app.processEvents()
            time.sleep(self.event_looptime)

    def get_html(self):
        """Get the current HTML for this webframe."""
        return unicode(self.webframe.toHtml())
    
    def get_url(self):
        """Get the current URL for this webframe."""
        return unicode(self.webframe.url().toString())

    def fill(self, selector, value):
        """Fill an input text with a strin value using a jQuery selector."""
        JSCODE_EXTRA = "jQuery('%s').val('%s')" % (selector, value)
        self._runjs_on_jquery("fill", JSCODE_EXTRA)

    def click(self, selector):
        """Click link or button using a jQuery selector."""
        JSCODE_EXTRA = "jQuery('%s').simulate('click')" % selector
        self._runjs_on_jquery("click", JSCODE_EXTRA)
        return self._wait_page_load()         

    def check(self, selector):
        """Check an input checkbox using a jQuery selector."""
        JSCODE_EXTRA = "jQuery('%s').attr('checked', true)" % selector
        self._runjs_on_jquery("check", JSCODE_EXTRA)

    def uncheck(self, selector):
        """Check input checkbox using a jQuery selector"""
        JSCODE_EXTRA = "jQuery('%s').attr('checked', false)" % selector
        self._runjs_on_jquery("uncheck", JSCODE_EXTRA)

    def choose(self, selector):        
        """Choose a radio input using a jQuery selector."""
        JSCODE_EXTRA = "jQuery('%s').simulate('click')" % selector
        self._runjs_on_jquery("choose", JSCODE_EXTRA)

    def select(self, selector):        
        """Choose a radio input using a jQuery selector."""
        JSCODE_EXTRA = "jQuery('%s').attr('selected', 'selected')" % selector
        self._runjs_on_jquery("select", JSCODE_EXTRA)
        
    def runjs(self, JSCODE_EXTRA, debug=True):
        """Run arbitrary Javascript code into the current frame."""
        if debug:
            self._debug(DEBUG, "Run Javascript code: %s" % JSCODE_EXTRA)
        return self.webpage.mainFrame().evaluateJavaScript(JSCODE_EXTRA)

    def get_mozilla_cookies(self):
        """Return string containing the current cookies in Mozilla format.""" 
        return self.cookiesjar.mozillaCookies()
            
    def download(self, url, outfd=None, bufsize=4096*16, cookies=None):
        """Download given URL using current cookies.
        
        If url is a path, pre-ppend the current base url."""        
        if cookies is None:
            cookies = self.get_mozilla_cookies()
        if url.startswith("/"):
            url = self.get_url_from_path(url)
        if self._get_protocol(url) != "http": 
            raise SpynnerError("Only http downloads are supported")            
        self._debug(INFO, "Start download: %s" % url)        
        self._debug(DEBUG, "Using cookies: %s" % cookies)
        return download(url, get_opener(cookies), outfd, bufsize)

    def get_url_from_path(self, path):
        """Return the URL for a given path using current URL as base url."""
        return urlparse.urljoin(self.get_url(), path)
