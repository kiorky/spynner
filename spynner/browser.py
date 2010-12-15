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
"""
Spynner is a stateful programmatic web-browser module for Python with 
Javascript/AJAX support. It is build upon the PyQtWebKit framework.   
"""

import itertools
import cookielib
import tempfile
import urlparse
import urllib2
import time
import sys
import re
import os
from StringIO import StringIO

from PyQt4.QtCore import SIGNAL, QUrl, QEventLoop, QString, Qt, QCoreApplication
from PyQt4.QtCore import QSize, QDateTime, QVariant
from PyQt4.QtGui import QApplication, QImage, QPainter, QRegion, QAction
from PyQt4.QtNetwork import QNetworkCookie, QNetworkAccessManager, QNetworkReply
from PyQt4.QtNetwork import QNetworkCookieJar, QNetworkRequest
from PyQt4.QtWebKit import QWebPage, QWebView, QWebFrame

# Debug levels
ERROR, WARNING, INFO, DEBUG = range(4)

class Browser:
    """
    Stateful programmatic web browser class based upon QtWebKit.   
    
    >>> browser = Browser()
    >>> browser.load("http://www.wordreference.com")
    >>> browser.runjs("console.log('I can run Javascript!')")
    >>> browser.runjs("_jQuery('div').css('border', 'solid red')") # and jQuery!
    >>> browser.select("#esen")
    >>> browser.fill("input[name=enit]", "hola")
    >>> browser.click("input[name=b]", wait_load=True)
    >>> print browser.url, len(browser.html)
    >>> browser.close()
    """
    ignore_ssl_errors = True
    """@ivar: If True, ignore SSL certificate errors."""
    user_agent = None
    """@ivar: User agent for requests (see QWebPage::userAgentForUrl for details)"""
    jslib = "jq"
    """@ivar: Library name for jQuery library injected by default to pages."""
    download_directory = "."
    """@ivar: Directory where downloaded files will be stored."""    
    debug_stream = sys.stderr
    """@ivar: File-like stream where debug output will be written."""
    debug_level = ERROR
    """@ivar: Debug verbose level (L{ERROR}, L{WARNING}, L{INFO} or L{DEBUG})."""    
    event_looptime = 0.01
    """@ivar: Event loop dispatcher loop delay (seconds)."""
    
    _javascript_files = ["jquery.min.js", "jquery.simulate.js"]

    _javascript_directories = [
        os.path.join(os.path.dirname(__file__), "../javascript"),
        os.path.join(sys.prefix, "share/spynner/javascript"),
    ]
    
    def __init__(self, qappargs=None, debug_level=None):
        """        
        Init a Browser instance.
        
        @param qappargs: Arguments for QApplication constructor.
        @param debug_level: Debug level logging (L{ERROR} by default)
        """ 
        self.application = QApplication(qappargs or [])
        """PyQt4.QtGui.Qapplication object."""
        if debug_level is not None:
            self.debug_level = debug_level
        self.webpage = QWebPage()
        """PyQt4.QtWebKit.QWebPage object."""
        self.webpage.userAgentForUrl = self._user_agent_for_url
        self.webframe = self.webpage.mainFrame()
        """PyQt4.QtWebKit.QWebFrame main webframe object."""
        self.webview = None
        """PyQt4.QtWebKit.QWebView object."""        
        self._url_filter = None
        self._html_parser = None
            
        # Javascript
        directory = _first(self._javascript_directories, os.path.isdir)
        if not directory:
            raise SpynnerError("Cannot find javascript directory: %s" %
                self._javascript_directories)           
        self.javascript = "".join(open(os.path.join(directory, fn)).read() 
            for fn in self._javascript_files)

        self.webpage.javaScriptAlert = self._javascript_alert                
        self.webpage.javaScriptConsoleMessage = self._javascript_console_message
        self.webpage.javaScriptConfirm = self._javascript_confirm
        self.webpage.javaScriptPrompt = self._javascript_prompt
        self._javascript_confirm_callback = None
        self._javascript_confirm_prompt = None
        
        # Network Access Manager and cookies
        self.manager = QNetworkAccessManager()
        """PyQt4.QtNetwork.QTNetworkAccessManager object."""
        self.manager.createRequest = self._manager_create_request 
        self.webpage.setNetworkAccessManager(self.manager)            
        self.cookiesjar = _ExtendedNetworkCookieJar()
        """PyQt4.QtNetwork.QNetworkCookieJar object."""
        self.manager.setCookieJar(self.cookiesjar)
        self.manager.connect(self.manager, 
            SIGNAL("sslErrors(QNetworkReply *, const QList<QSslError> &)"),
            self._on_manager_ssl_errors)
        self.manager.connect(self.manager, 
            SIGNAL('finished(QNetworkReply *)'),
            self._on_reply)
        self.manager.connect(self.manager,
            SIGNAL('authenticationRequired(QNetworkReply *, QAuthenticator *)'),
            self._on_authentication_required)   
        self._operation_names = dict(
            (getattr(QNetworkAccessManager, s + "Operation"), s.lower()) 
            for s in ("Get", "Head", "Post", "Put"))
        
        # Webpage slots         
        self._load_status = None
        self._replies = 0
        self.webpage.setForwardUnsupportedContent(True)
        self.webpage.connect(self.webpage,
            SIGNAL('unsupportedContent(QNetworkReply *)'), 
            self._on_unsupported_content)
        self.webpage.connect(self.webpage, 
            SIGNAL('loadFinished(bool)'),
            self._on_load_finished)            
        self.webpage.connect(self.webpage, 
            SIGNAL("loadStarted()"),
            self._on_load_started)

    def _events_loop(self, wait=None):
        if wait is None:
            wait = self.event_looptime
        self.application.processEvents()
        time.sleep(wait)        
                        
    def _on_load_started(self):
        self._load_status = None
        self._debug(INFO, "Page load started")            
    
    def _on_manager_ssl_errors(self, reply, errors):
        url = unicode(reply.url().toString())
        if self.ignore_ssl_errors:
            self._debug(WARNING, "SSL certificate error ignored: %s" % url)
            reply.ignoreSslErrors()
        else:
            self._debug(WARNING, "SSL certificate error: %s" % url)

    def _on_authentication_required(self, reply, authenticator):
        url = unicode(reply.url().toString())
        realm = unicode(authenticator.realm())
        self._debug("HTTP auth required: %s (realm: %s)" % (url, realm))
        if not self._http_authentication_callback:
            self._debug(WARNING, "HTTP auth required, but no callback defined")
            return        
        credentials = self._http_authentication_callback(url, realm)        
        if credentials:            
            user, password = credentials
            self._debug(INFO, "callback returned HTTP credentials: %s/%s" % 
                (user, "*"*len(password)))
            authenticator.setUser(user)
            authenticator.setPassword(password)
        else:
            self._debug(WARNING, "HTTP auth callback returned no credentials")
        
    def _manager_create_request(self, operation, request, data):
        url = unicode(request.url().toString())
        operation_name = self._operation_names[operation].upper()
        self._debug(INFO, "Request: %s %s" % (operation_name, url))
        for h in request.rawHeaderList():
            self._debug(DEBUG, "  %s: %s" % (h, request.rawHeader(h)))
        if self._url_filter:
            if self._url_filter(self._operation_names[operation], url) is False:
                self._debug(INFO, "URL filtered: %s" % url)
                request.setUrl(QUrl("about:blank"))
            else:
                self._debug(DEBUG, "URL not filtered: %s" % url)
        reply = QNetworkAccessManager.createRequest(self.manager, 
            operation, request, data)        
        return reply

    def _on_reply(self, reply):
        self._replies += 1
        self._reply_url = unicode(reply.url().toString())
        if reply.error():
            self._debug(WARNING, "Reply error: %s - %d (%s)" % 
                (self._reply_url, reply.error(), reply.errorString()))
        else:
            self._debug(INFO, "Reply successful: %s" % self._reply_url)
        for header in reply.rawHeaderList():
            self._debug(DEBUG, "  %s: %s" % (header, reply.rawHeader(header)))

    def _on_unsupported_content(self, reply, outfd=None):
        if not reply.error():
            self._start_download(reply, outfd)
        else:            
            self._debug(ERROR, "Error on unsupported content: %s" % reply.errorString())
                             
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

    def _javascript_confirm(self, webframe, message):
        smessage = unicode(message)
        url = webframe.url()
        self._debug(INFO, "Javascript confirm (webframe url = %s): %s" % 
            (url, smessage))
        if self._javascript_confirm_callback:
            value = self._javascript_confirm_callback(url, smessage)
            self._debug(INFO, "Javascript confirm callback returned %s" % value)
            return value 
        return QWebPage.javaScriptConfirm(self.webpage, webframe, message)

    def _javascript_prompt(self, webframe, message, defaultvalue, result):
        url = webframe.url()
        smessage = unicode(message)
        self._debug(INFO, "Javascript prompt (webframe url = %s): %s" % 
            (url, smessage))
        if self._javascript_prompt_callback:
            value = self._javascript_prompt_callback(url, smessage, defaultvalue)
            self._debug(INFO, "Javascript prompt callback returned: %s" % value)
            if value in (False, None):
                return False
            result.clear()
            result.append(value)
            return True
        return QWebPage.javaScriptPrompt(self.webpage, webframe, message,
            defaultvalue, result)
        
    def _on_webview_destroyed(self, window):
        self.webview = None
                                             
    def _on_load_finished(self, successful):        
        self._load_status = successful  
        status = {True: "successful", False: "error"}[successful]
        self._debug(INFO, "Page load finished (%d bytes): %s (%s)" % 
            (len(self.html), self.url, status))

    def _get_filepath_for_url(self, url):
        urlinfo = urlparse.urlsplit(url)
        path = os.path.join(self.download_directory,
            urlinfo.netloc + urlinfo.path)
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        return path

    def _start_download(self, reply, outfd):
        def _on_ready_read():
            data = reply.readAll()
            reply.downloaded_nbytes += len(data)
            outfd.write(data)
            self._debug(DEBUG, "Read from download stream (%d bytes): %s" 
                % (len(data), url))
        def _on_network_error():
            self.debug(ERROR, "Network error on download: %s" % url)
        def _on_finished():
            self._debug(INFO, "Download finished: %s" % url)
        url = unicode(reply.url().toString())
        if outfd is None:
            path = self._get_filepath_for_url(url)
            outfd = open(path, "wb")            
        reply.connect(reply, SIGNAL("readyRead()"), _on_ready_read)
        reply.connect(reply, SIGNAL("NetworkError()"), _on_network_error)
        reply.connect(reply, SIGNAL("finished()"), _on_finished)
        self._debug(INFO, "Start download: %s" % url)

    def _wait_load(self, timeout=None):
        self._events_loop(0.0)
        if self._load_status is not None:
            load_status = self._load_status
            self._load_status = None
            return load_status        
        itime = time.time()
        while self._load_status is None:
            if timeout and time.time() - itime > timeout:
                raise SpynnerTimeout("Timeout reached: %d seconds" % timeout)
            self._events_loop()
        self._events_loop(0.0)
        if self._load_status:
            jscode = "var %s = jQuery.noConflict();" % self.jslib
            self.runjs(self.javascript + jscode, debug=False)
            self.webpage.setViewportSize(self.webpage.mainFrame().contentsSize())            
        load_status = self._load_status
        self._load_status = None
        return load_status        

    def _debug(self, level, *args):
        if level <= self.debug_level:
            kwargs = dict(outfd=self.debug_stream)
            _debug(*args, **kwargs)

    def _user_agent_for_url(self, url):
        if self.user_agent:
            return self.user_agent
        return QWebPage.userAgentForUrl(self.webpage, url)

    def get_js_obj_length(self, res):
        if res.type() != res.Map:
            return False
        resmap = res.toMap()
        lenfield = QString(u'length')
        if lenfield not in resmap:
            return False
        return resmap[lenfield].toInt()[0]
    
    def jslen(self, selector):
        res = self.runjs("%s('%s')" % (self.jslib, selector))
        return self.get_js_obj_length(res)
    
    def _runjs_on_jquery(self, name, code):
        res = self.runjs(code)
        if self.get_js_obj_length(res) < 1:
            raise SpynnerJavascriptError("error on %s: %s" % (name, code))

    def _get_html(self):
        return unicode(self.webframe.toHtml())

    def _get_soup(self):
        if not self._html_parser:
            raise SpynnerError("Cannot get soup with no HTML parser defined")
        return self._html_parser(self.html)

    def _get_url(self):
        return unicode(self.webframe.url().toString())

    # Properties
                 
    url = property(_get_url)
    """Current URL."""        
                 
    html = property(_get_html)
    """Rendered HTML in current page."""
                 
    soup = property(_get_soup)
    """HTML soup (see L{set_html_parser})."""
               
    #{ Basic interaction with browser

    def load(self, url):
        """Load a web page and return status (a boolean)."""
        self.webframe.load(QUrl(url))
        return self._wait_load()

    def wait_requests(self, wait_requests = None, url = None, url_regex = None):
        if wait_requests:
            while self._replies < wait_requests:
                self._events_loop()
            self._events_loop(0.0)
        if url_regex or url:
            last_replies = self._replies
            while True:
                if last_replies != self._replies:
                    if url_regex:
                        if re.search(url_regex, self._reply_url):
                            break
                    elif url:
                        if url == self._reply_url:
                            break
                self._events_loop()
            self._events_loop(0.0)
    
    def click(self, selector, wait_load=False, wait_requests=None, timeout=None):
        """
        Click any clickable element in page.
        
        @param selector: jQuery selector.
        @param wait_load: If True, it will wait until a new page is loaded.
        @param timeout: Seconds to wait for the page to load before 
                                       raising an exception.
        @param wait_requests: How many requests to wait before returning. Useful
                              for AJAX requests.
    
        By default this method will not wait for a page to load. 
        If you are clicking a link or submit button, you must call this
        method with C{wait_load=True} or, alternatively, call 
        L{wait_load} afterwards. However, the recommended way it to use 
        L{click_link}.
                        
        When a non-HTML file is clicked this method will download it. The 
        file is automatically saved keeping the original structure (as 
        wget --recursive does). For example, a file with URL 
        I{http://server.org/dir1/dir2/file.ext} will be saved to  
        L{download_directory}/I{server.org/dir1/dir2/file.ext}.                 
        """
        jscode = "%s('%s').simulate('click')" % (self.jslib, selector)
        self._replies = 0
        self._runjs_on_jquery("click", jscode)
        self.wait_requests(wait_requests)
        if wait_load:
            return self._wait_load(timeout)

    def click_link(self, selector, timeout=None):
        """Click a link and wait for the page to load."""
        return self.click(selector, wait_load=True, timeout=timeout)

    def click_ajax(self, selector, wait_requests=1, timeout=None):
        """Click a AJAX link and wait for the request to finish."""
        return self.click(selector, wait_requests=wait_requests, timeout=timeout)
    
    def wait_load(self, timeout=None):
        """
        Wait until the page is loaded.
        
        @param timeout: Time to wait (seconds) for the page load to complete.
        @return: Boolean state
        @raise SpynnerTimeout: If timeout is reached.
        """
        return self._wait_load(timeout)

    def wait(self, waittime):
        """
        Wait some time.
        
        @param waittime: Time to wait (seconds).
        
        This is an active wait, the events loop will be run, so it
        may be useful to wait for synchronous Javascript events that
        change the DOM.
        """   
        itime = time.time()
        while time.time() - itime < waittime:
            self._events_loop()        

    def close(self):
        """Close Browser instance and release resources."""        
        if self.webview:
            self.destroy_webview()
        if self.webpage:
            del self.webpage

    #}
                      
    #{ Webview
    
    def create_webview(self, show=False):
        """Create a QWebView object and insert current QWebPage."""
        if self.webview:
            raise SpynnerError("Cannot create webview (already initialized)")
        self.webview = QWebView()
        self.webview.setPage(self.webpage)
        window = self.webview.window()
        window.setAttribute(Qt.WA_DeleteOnClose)
        window.connect(window, SIGNAL('destroyed(QObject *)'),
            self._on_webview_destroyed)
        if show:
            self.show()

    def destroy_webview(self):
        """Destroy current QWebView."""
        if not self.webview:
            raise SpynnerError("Cannot destroy webview (not initialized)")
        del self.webview 

    def show(self):
        """Show webview browser."""
        if not self.webview:
            raise SpynnerError("Webview is not initialized")
        self.webview.show()

    def hide(self):
        """Hide webview browser."""
        if not self.webview:
            raise SpynnerError("Webview is not initialized")
        self.webview.hide()

    def browse(self):
        """Let the user browse the current page (infinite loop).""" 
        if not self.webview:
            raise SpynnerError("Webview is not initialized")
        self.show()
        while self.webview:
            self._events_loop()

    #}
                        
    #{ Form manipulation
    
    def fill(self, selector, value):
        """Fill an input text with a string value using a jQuery selector."""
        escaped_value = value.replace("'", "\\'")
        jscode = "%s('%s').val('%s')" % (self.jslib, selector, escaped_value)
        self._runjs_on_jquery("fill", jscode)

    def check(self, selector):
        """Check an input checkbox using a jQuery selector."""
        jscode = "%s('%s').attr('checked', true)" % (self.jslib, selector)
        self._runjs_on_jquery("check", jscode)

    def uncheck(self, selector):
        """Uncheck input checkbox using a jQuery selector"""
        jscode = "%s('%s').attr('checked', false)" % (self.jslib, selector)
        self._runjs_on_jquery("uncheck", jscode)

    def choose(self, selector):        
        """Choose a radio input using a jQuery selector."""
        jscode = "%s('%s').simulate('click')" % (self.jslib, selector)
        self._runjs_on_jquery("choose", jscode)

    def select(self, selector):        
        """Choose a option in a select using a jQuery selector."""
        jscode = "%s('%s').attr('selected', 'selected')" % (self.jslib, selector)
        self._runjs_on_jquery("select", jscode)
    
    submit = click_link
      
    #}
    
    #{ Javascript 
    
    def runjs(self, jscode, debug=True):
        """
        Inject Javascript code into the current context of page.

        @param jscode: Javascript code to injected.
        @param debug: Set to False to disable debug output for this injection.
        
        You can call Jquery even if the original page does not include it 
        as Spynner injects the library for every loaded page. You must 
        use C{_jQuery(...)} instead of of C{jQuery} or the common {$(...)} 
        shortcut. 
        
        @note: You can change the _jQuery alias (see L{jslib}).        
        """
        if debug:
            self._debug(DEBUG, "Run Javascript code: %s" % jscode)
        r = self.webpage.mainFrame().evaluateJavaScript(jscode)
        if r.isValid() == False:
            r = self.webpage.mainFrame().evaluateJavaScript(jscode)
        return r

    def set_javascript_confirm_callback(self, callback):
        """
        Set function callback for Javascript confirm pop-ups.
        
        By default Javascript confirmations are not answered. If the webpage
        you are working pops Javascript confirmations, be sure to set a callback
        for them. 
        
        Calback signature: C{javascript_confirm_callback(url, message)}
        
            - url: Url where the popup was launched.        
            - param message: String message.
        
        The callback should return a boolean (True meaning 'yes', False meaning 'no')
        """
        self._javascript_confirm_callback = callback

    def set_javascript_prompt_callback(self, callback):
        """
        Set function callback for Javascript prompt.
        
        By default Javascript prompts are not answered. If the webpage
        you are working pops Javascript prompts, be sure to set a callback
        for them. 
        
        Callback signature: C{javascript_prompt_callback(url, message, defaultvalue)}
        
            - url: Url where the popup prompt was launched.
            - message: String message.
            - defaultvalue: Default value for prompt answer
            
        The callback should return a string with the answer or None to cancel the prompt.
        """
        self._javascript_prompt_callback = callback

    #}
    
    #{ Cookies
    
    def get_cookies(self):
        """Return string containing the current cookies in Mozilla format.""" 
        return self.cookiesjar.mozillaCookies()

    def set_cookies(self, string_cookies):
        """Set cookies from a string with Mozilla-format cookies.""" 
        return self.cookiesjar.setMozillaCookies(string_cookies)

    #}
    
    #{ Download files
                
    def download(self, url, outfd=None):
        """
        Download a given URL using current cookies.
        
        @param url: URL or path to download
        @param outfd: Output file-like stream. If None, return data string.
        @return: Bytes downloaded (None if something went wrong)
        @note: If url is a path, the current base URL will be pre-appended.        
        """
        def _on_reply(reply):
            url = unicode(reply.url().toString())
            self._download_reply_status = not bool(reply.error())
        self._download_reply_status = None
        if not urlparse.urlsplit(url).scheme:
            url = urlparse.urljoin(self.url, url) 
        request = QNetworkRequest(QUrl(url))
        # Create a new manager to process this download        
        manager = QNetworkAccessManager()
        reply = manager.get(request)
        if reply.error():
            raise SpynnerError("Download error: %s" % reply.errorString())
        reply.downloaded_nbytes = 0
        manager.setCookieJar(self.manager.cookieJar())
        manager.connect(manager, SIGNAL('finished(QNetworkReply *)'), _on_reply)
        outfd_set = bool(outfd)
        if not outfd_set:
            outfd = StringIO()            
        self._start_download(reply, outfd)
        while self._download_reply_status is None:
            self._events_loop()
        if outfd_set:
            return (reply.downloaded_nbytes if not reply.error() else None)
        else:
            return outfd.getvalue()  
    
    #}
            
    #{ HTML and tag soup parsing
    
    def set_html_parser(self, parser):
        """
        Set HTML parser used to generate the HTML L{soup}.
        
        @param parser: Callback called to generate the soup.
        
        When a HTML parser is set for a Browser, the property L{soup} returns
        the parsed HTML.        
        """
        self._html_parser = parser

    def html_contains(self, regexp):
        """Return True if current HTML contains a given regular expression."""
        return bool(re.search(regexp, self.html))

    #}

    #{ HTTP Authentication
     
    def set_http_authentication_callback(self, callback):
        """
        Set HTTP authentication request callback.
        
        The callback must have this signature: 
        
        C{http_authentication_callback(url, realm)}: 
                        
            - C{url}: URL where the requested was made.
            - C{realm}: Realm requiring authentication.
            
        The callback should return a pair of string containing (user, password) 
        or None if you don't want to answer.
        """
        self._http_authentication_callback = callback
    
    #}
             
    #{ Miscellaneous
    
    def snapshot(self, box=None, format=QImage.Format_ARGB32):
        """        
        Take an image snapshot of the current frame.
        
        @param box: 4-element tuple containing box to capture (x1, y1, x2, y2).
                    If None, capture the whole page.
        @param format: QImage format (see QImage::Format_*).
        @return: A QImage image.
        
        Typical usage:
        
        >>> browser.load(url)
        >>> browser.snapshot().save("webpage.png") 
        """
        if box:
            x1, y1, x2, y2 = box        
            w, h = (x2 - x1), (y2 - y1)
            image0 = QImage(QSize(x2, y2), format)
            painter = QPainter(image0)
            self.webpage.mainFrame().render(painter)
            painter.end()
            image = image0.copy(x1, y1, w, h)
        else:
            image = QImage(self.webpage.viewportSize(), format)
            painter = QPainter(image)                        
            self.webpage.mainFrame().render(painter)
            painter.end()
        return image
            
    def get_url_from_path(self, path):
        """Return the URL for a given path using the current URL as base."""
        return urlparse.urljoin(self.url, path)

    def set_url_filter(self, url_filter):
        """
        Set function callback to filter URL.
        
        By default all requested elements of a page are loaded. That includes 
        stylesheets, images and many other elements that you may not need at all.         
        Use this method to define the callback that will be called every time 
        a new request is made. The callback must have this signature: 
        
        C{my_url_filter(operation, url)}: 
                        
            - C{operation}: string with HTTP operation: C{get}, C{head}, 
                            C{post} or C{put}.
            - C{url}: requested item URL.
            
        It should return C{True} (proceed) or C{False} (reject).
        """
        self._url_filter = url_filter

    #}

def _first(iterable, pred=bool):
    """Return the first element in iterator that matches the predicate"""
    for item in iterable:
        if pred(item):
            return item

def _debug(obj, linefeed=True, outfd=sys.stderr, outputencoding="utf8"):
    """Print a debug info line to stream channel"""
    if isinstance(obj, unicode):
        obj = obj.encode(outputencoding)
    strobj = str(obj) + ("\n" if linefeed else "")
    outfd.write(strobj)
    outfd.flush()
     
class SpynnerError(Exception):
    """General Spynner error."""

class SpynnerPageError(Exception):
    """Error loading page."""

class SpynnerTimeout(Exception):
    """A timeout (usually on page load) has been reached."""

class SpynnerJavascriptError(Exception):
    """Error on the injected Javascript code.""" 
                   
class _ExtendedNetworkCookieJar(QNetworkCookieJar):
    def mozillaCookies(self):
        """
        Return all cookies in Mozilla text format:
        
        # domain domain_flag path secure_connection expiration name value
        
        .firefox.com     TRUE   /  FALSE  946684799   MOZILLA_ID  100103        
        """
        header = ["# Netscape HTTP Cookie File", ""]        
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

    def setMozillaCookies(self, string_cookies):
        """Set all cookies from Mozilla test format string.
        .firefox.com     TRUE   /  FALSE  946684799   MOZILLA_ID  100103        
        """
        def str2bool(value):
            return {"TRUE": True, "FALSE": False}[value]
        def get_cookie(line):
            fields = map(str.strip, line.split("\t"))
            if len(fields) != 7:
                return
            domain, domain_flag, path, is_secure, expiration, name, value = fields
            cookie = QNetworkCookie(name, value)
            cookie.setDomain(domain)
            cookie.setPath(path)
            cookie.setSecure(str2bool(is_secure))
            cookie.setExpirationDate(QDateTime.fromTime_t(int(expiration)))
            return cookie
        cookies = [get_cookie(line) for line in string_cookies.splitlines() 
          if line.strip() and not line.strip().startswith("#")]
        self.setAllCookies(filter(bool, cookies))
