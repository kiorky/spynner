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

import pkg_resources

from PyQt4.QtCore import SIGNAL, QUrl, QString, Qt, QEvent
from PyQt4.QtCore import QSize, QDateTime, QPoint
from PyQt4.QtGui import QApplication, QImage, QPainter
from PyQt4.QtGui import QCursor, QMouseEvent, QKeyEvent
from PyQt4.QtNetwork import QNetworkCookie, QNetworkAccessManager
from PyQt4.QtNetwork import QNetworkCookieJar, QNetworkRequest, QNetworkProxy
from PyQt4.QtWebKit import QWebPage, QWebView


SpynnerQapplication = None

# Debug levels
ERROR, WARNING, INFO, DEBUG = range(4)
argv = ['dummy']

class Browser(object):
    """
    Stateful programmatic web browser class based upon QtWebKit.
    """
    errorCode = None
    errorMessage = None
    _javascript_directories = [
        pkg_resources.resource_filename('spynner', 'javascript'),
    ]
    _jquery = 'jquery-1.5.2.js'
    _jquery_simulate = 'jquery.simulate.js'

    def __init__(self,
                 qappargs=None,
                 debug_level=ERROR,
                 want_compat=False,
                 embed_jquery=False,
                 embed_jquery_simulate=False,
                 additional_js_files = None,
                 jslib = None,
                 download_directory = ".",
                 user_agent = None,
                 debug_stream = sys.stderr,
                 event_looptime = 0.01 ,
                 ignore_ssl_errors = True
                ):
        """
        Init a Browser instance.
        @param qappargs: Arguments for QApplication constructor.
        @param debug_level: Debug level logging (L{ERROR} by default)
        @param want_compat: set jquery compatiblity mode to "self.jslib"
        @param jslib:  IF True: Use jQuery.noConflict to "jslib", else just use '$'
        @param download_directory:  Directory where downloaded files will be stored.
        @param user_agent User agent for requests (see QWebPage::userAgentForUrl for details)
        @param event_looptime Event loop dispatcher loop delay (seconds).
        @apram ignore_ssl_errors  If True, ignore SSL certificate errors.
        @param debug_stream  File-like stream where debug output will be written.

        Important vars:

            - self.webpage: QwebPage object
            - self.application : QApplication object
            - self.webframe: active QWebFrame object
            - self.manager: QNetworkAccessManager object
            - self.files: represent a list of dicts tracking downloaded files where the download key
              is the path, each entry is in the form {'reply': replyobj, 'req': reqobj}
        """
        self.download_directory = download_directory
        import spynner
        if not spynner.SpynnerQapplication:
            spynner.SpynnerQapplication = QApplication(spynner.argv)
        self.application = spynner.SpynnerQapplication
        self.want_compat = want_compat
        self.embed_jquery = embed_jquery
        self.embed_jquery_simulate = embed_jquery_simulate
        self.debug_stream = debug_stream
        self.user_agent = user_agent
        self.additional_js_files = additional_js_files
        self.additional_js = ""
        self.event_looptime = event_looptime
        self.ignore_ssl_errors = ignore_ssl_errors
        self.webpage = QWebPage()
        if not self.additional_js_files:
            self.additional_js_files = []
        self.jslib = jslib
        if not self.want_compat:
            if jslib is None:
                self.jslib = '$'
            else:
                self.jslib = jslib
        else:
            self.jslib = 'spynnerjq'
        self.debug_level = debug_level
        """PyQt4.QtWebKit.QWebPage object."""
        self.webpage.userAgentForUrl = self._user_agent_for_url
        self.webframe = self.webpage.mainFrame()
        """PyQt4.QtWebKit.QWebFrame main webframe object."""
        self.webview = None
        """PyQt4.QtWebKit.QWebView object."""
        self._url_filter = None
        self._html_parser = None
        self.files = []
        # Javascript
        directory = _first(self._javascript_directories, os.path.isdir)
        if not directory:
            raise SpynnerError("Cannot find javascript directory: %s" %
                self._javascript_directories)
        self.jquery = open(os.path.join(directory, self._jquery)).read()
        self.jquery_simulate = open(os.path.join(directory, self._jquery_simulate)).read()
        for fn in self.additional_js_files:
            if not os.path.exists(fn):
                fn = os.path.join(directory, fn)
            self.additional_js += "\n%s" % open(fn).read()
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
        self._reply_status = not bool(reply.error())

        if reply.error():
            self._debug(WARNING, "Reply error: %s - %d (%s)" %
                (self._reply_url, reply.error(), reply.errorString()))
            self.errorCode = reply.error()
            self.errorMessage = reply.errorString()
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
        if getattr(self, 'webpage', None):
            self.webframe = self.webpage.mainFrame()
        self._load_status = successful
        status = {True: "successful", False: "error"}[successful]
        self._debug(INFO, "Page load finished (%d bytes): %s (%s)" %
            (len(self.html), self.url, status))

    def _get_filepath_for_url(self, url, reply=None):
        urlinfo = urlparse.urlsplit(url)
        path = os.path.join(os.path.abspath(self.download_directory), urlinfo.netloc)
        if urlinfo.path != '/':
            p = urlinfo.path
            if len(p) > 2:
                if p[0] == '/':
                    p = p[1:]
            path = os.path.join(path, p)
        if reply.hasRawHeader('content-disposition'):
            cd = '%s' % reply.rawHeader('content-disposition')
            pattern = 'attachment;filename=(.*)'
            if re.match(pattern, cd):
                filename = re.sub('attachment;filename=(.*)', '\\1', cd)
                path = os.path.join(path, filename)
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        if path is None:
            raise SpynnerError('Download mode is unknown, can\'t determine the final filename')
        return path

    def _start_download(self, reply, outfd):
        url = unicode(reply.url().toString())
        path = None
        if outfd is None:
            path = self._get_filepath_for_url(url, reply)
            outfd = open(path, "wb")
        def _on_ready_read():
            data = reply.readAll()
            if getattr(reply, 'downloaded_nbytes', None) is None:
                reply.downloaded_nbytes= 0
            reply.downloaded_nbytes += len(data)
            outfd.write(data)
            self._debug(DEBUG, "Read from download stream (%d bytes): %s"
                % (len(data), url))
        def _on_network_error():
            self.debug(ERROR, "Network error on download: %s" % url)
        def _on_finished():
            if path is not None:
                outfd.flush()
                dict(self.files)[path]['finished'] = True
            self._debug(INFO, "Download finished: %s" % url)
        if path is not None:
            self.files.append((path, {'reply':reply,'finished':False,}))
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
            self.load_js()
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
        if resmap[lenfield].type() == resmap[lenfield].Double:
            return int(resmap[lenfield].toDouble()[0])
        else:
            return resmap[lenfield].toInt()[0]

    def jslen(self, selector):
        res = self.runjs("%s('%s')" % (self.jslib, selector))
        return self.get_js_obj_length(res)

    def _runjs_on_jquery(self, name, code):
        res = self.runjs(code)
        if not isinstance(self.get_js_obj_length(res), int):
            raise SpynnerJavascriptError("error on %s: %s" % (name, code))
        return res

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

    def load(self, 
             url, 
             load_timeout=10,
             wait_callback = None,
             tries=None,
            ):
        """Load a web page and return status (a boolean).
        @param url url to open
        @param load_timeout timeout to load the page, or if you use wait_callback, time between retries
        @param wait_callback a callback to test if content is ready
        @param tries set to True for unlimited retries, to int for limited to tries, tries.

        eg:

            Open google

            >>> br.load('http://www.google.fr')

            Same thing except we will try to see if there is 'google' in the html, 
            thus with 3 wills at 10 seconds of interval

            >>> def wait_load(b):
            ...     return 'google' in b.html.lower()
            >>> br.load('http://www.google.fr', wait_callback=wait_load, tries=3)


        """
        self.webframe.load(QUrl(url))
        if wait_callback is None:
            return self._wait_load(timeout = load_timeout)
        else:
            return self.wait_for_content(wait_callback, tries=tries, delay=load_timeout)

    def is_jquery_loaded(self):
        return self.runjs('typeof(spynner_jquery_loaded);', debug=False).toString() != 'undefined'

    def is_jquery_simulate_loaded(self):
        return self.runjs('typeof(spynner_jquery_simulate_loaded);', debug=False).toString() != 'undefined'

    def is_additional_js_loaded(self):
        return self.runjs('typeof(spynner_additional_js_loaded);', debug=False).toString() != 'undefined'

    def load_jquery(self, force=False):
        """Load jquery in the current frame"""
        jscode = ''
        if self.embed_jquery or force:
            if not self.is_jquery_loaded():
                jscode += self.jquery
                if self.want_compat or (self.jslib != '$'):
                    jscode += "\nvar %s = jQuery.noConflict();" % self.jslib
                jscode += "var spynner_jquery_loaded = 1 ;"
                self.runjs(jscode, debug=False)

    def load_js(self):
        self.load_jquery()
        self.load_jquery_simulate()
        self.load_additional_js()

    def load_jquery_simulate(self, force=False):
        """Load jquery simulate in the current frame"""
        if self.embed_jquery_simulate or force:
            if not self.is_jquery_simulate_loaded():
                self.runjs(self.jquery_simulate, debug=False)
                self.runjs("var spynner_jquery_simulate_loaded = 1 ;", debug=False)

    def load_additional_js(self, force=False):
        """Load jquery in the current frame"""
        if not self.is_additional_js_loaded() or force:
            if len(self.additional_js.strip()) > 0:
                self.runjs(self.additional_js, debug=False)
            self.runjs("var spynner_additional_js_loaded = 1 ;", debug=False)

    def wait_a_little(br, timeout):
        try:
            br.wait_load(timeout)
        except SpynnerTimeout, e:
            pass

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

    def sendText(self, selector, text, keyboard_modifiers = Qt.NoModifier, wait_load=False, wait_requests=None, timeout=None):
        """
        Send text in any element (to fill it for example)

        @param selector: QtWebkit Selector
        @param keys to input in the QT way
        @param wait_load: If True, it will wait until a new page is loaded.
        @param timeout: Seconds to wait for the page to load before raising an exception.
        @param wait_requests: How many requests to wait before returning. Useful for AJAX requests.

        >>> br.sendText('#val_cel_dentifiant', 'fancy text')
        """
        element = self.webframe.findFirstElement(selector)
        element.setFocus()
        eventp = QKeyEvent(QEvent.KeyPress, Qt.Key_A, keyboard_modifiers, QString(text))
        self.application.sendEvent(self.webview, eventp)
        self._events_loop(timeout)
        self.wait_requests(wait_requests)
        if wait_load:
            return self._wait_load(timeout)

    def sendKeys(self, selector, keys, keyboard_modifiers = Qt.NoModifier, wait_load=False, wait_requests=None, timeout=None):
        """
        Click any clickable element in page.
        see http://www.riverbankcomputing.co.uk/static/Docs/PyQt4/html/qt.html#Key-enum

        @param selector: jQtWebkit Selector
        @param keys to input in the QT way
        @param wait_load: If True, it will wait until a new page is loaded.
        @param timeout: Seconds to wait for the page to load before
                                       raising an exception.
        @param wait_requests: How many requests to wait before returning. Useful
                              for AJAX requests.

        Send raw keys:
        >>> br.sendKeys('#val_cel_dentifiant', [Qt.Key_A,Qt.Key_A,Qt.Key_C,]
        """
        element = self.webframe.findFirstElement(selector)
        element.setFocus()
        for key in keys:
            eventp = QKeyEvent(QEvent.KeyPress, key, keyboard_modifiers)
            self.application.sendEvent(self.webview, eventp)
            self._events_loop(timeout)
        self.wait_requests(wait_requests)
        if wait_load:
            return self._wait_load(timeout)

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
        if not self.embed_jquery_simulate:
            return self.wk_click(selector,
                                 wait_load=wait_load,
                                 wait_requests=wait_requests,
                                 timeout=timeout)
        jscode = "%s('%s').simulate('click');" % (self.jslib, selector)
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

    def moveMouse(self, where, timeout=1, real=False):
        """Move the mouse to a relative to the window point."""
        if not real:
            where = self.getRealPosition(where)
        cursorw = QCursor()
        cursorw.setPos(where)
        self.webview.grabMouse()
        self.wait(1)
        self.webview.setCursor(cursorw)
        self.wait(timeout)
        self.webview.releaseMouse()

    def getRealPosition(self, point):
        """Compute the coordinates by merging with the containing frame.
        @param point: (QPoint)
        """
        rect = self.webframe.geometry()
        where = QPoint(rect.x() + point.x(), rect.y() + point.y())
        where = self.webview.mapToGlobal(where)
        return where

    def nativeClickAt(self, where, timeout, real=False):
        """Click on an arbitrar location of the browser.
        @param where: where to click (QPoint)
        @param real: if not true coordinates are relative to the window instead of the screen
        @timeout seconds: seconds to wait after click
        """
        if not real:
            where = self.getRealPosition(where)
        self.webview.grabMouse()
        self.moveMouse(where, real=True)
        eventp = QMouseEvent(QEvent.MouseButtonPress,   where, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        eventl = QMouseEvent(QEvent.MouseButtonRelease, where, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        self.application.sendEvent(self.application.focusWidget(), eventp)
        self.application.sendEvent(self.application.focusWidget(), eventl)
        self._events_loop(timeout)
        self._events_loop(timeout)
        self.webview.releaseMouse()

    def getPosition(self, selector):
        """Get the position QPoint(x,y) of a css selector.
        @param selector: The css Selector to query against
        """
        jscode = "off = %s('%s').offset(); off.left+','+off.top" % (self.jslib, selector)
        self._replies = 0
        try:
            x, y = ("%s" % self.runjs(jscode, debug=False).toString()).split(',')
            twhere = QPoint(int(x), int(y))
            where = self.webview.mapToGlobal(twhere)
            if where == twhere:
                where = self.webview.mapToGlobal(where)
        except Exception, e:
            #try also using qt
            try:
                item = self.webframe.findFirstElement(selector)
                geo = item.geometry()
                twhere = geo.topLeft()
                where = self.webview.mapToGlobal(twhere)
                if where == twhere:
                    where = self.webview.mapToGlobal(where)
            except:
                raise  SpynnerError('Cant find %s (%s)' % (selector, e))
        return where

    def wk_click_element(self, element, wait_load=False, wait_requests=None, timeout=None):
        """
        Click on an element by using raw javascript WebKit.click() method.

        @param element: QWebElement object
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
        #element.evaluateJavaScript("this.click()")
        jscode = (
            "var e = document.createEvent('MouseEvents');"
            "e.initEvent( 'click', true, true );"
            "this.dispatchEvent(e);"
        )
        element.evaluateJavaScript(jscode)
        time.sleep(0.5)
        self.wait_requests(wait_requests)
        if wait_load:
            return self._wait_load(timeout)

    def wk_click_element_link(self, element, timeout=None):
        """Click a link and wait for the page to load.
        @param selector: WebKit xpath selector to an element
        @param: timeout timeout to wait in seconds
        """
        return self.wk_click_element(element, wait_load=True, timeout=timeout)

    def wk_click_element_ajax(self, element, wait_requests=1, timeout=None):
        """Click a AJAX link and wait for the request to finish.
        @param selector: WebKit xpath selector to an element
        @param wait_requests: How many requests to wait before returning. Useful
                              for AJAX requests.
        @param: timeout timeout to wait in seconds
        """
        return self.wk_click_element(element, wait_requests=wait_requests, timeout=timeout)

    def wk_click(self, selector, wait_load=False, wait_requests=None, timeout=None):
        """
        Select an element with a CSS2 selector and then click by using raw javascript WebKit.click() method.
        See the wk_click_element functions for additional documentation

        @param selector: WebKit selector.
        @param wait_load: If True, it will wait until a new page is loaded.
        @param timeout: Seconds to wait for the page to load before
                                       raising an exception.
        @param wait_requests: How many requests to wait before returning. Useful
                              for AJAX requests.
        """
        element = self.webframe.findFirstElement(selector)
        return self.wk_click_element(element, wait_load=wait_load, wait_requests=wait_requests, timeout=timeout)

    def wk_click_link(self, selector, timeout=None):
        """Click a link and wait for the page to load.
        See the wk_click_element_link functions for additional documentation
        @param selector: WebKit xpath selector to an element
        @param: timeout timeout to wait in seconds
        """
        element = self.webframe.findFirstElement(selector)
        return self.wk_click_element_link(element, timeout=timeout)

    def wk_click_ajax(self, selector, wait_requests=1, timeout=None):
        """Click a AJAX link and wait for the request to finish.
        See the wk_click_element_ajax functions for additional documentation
        @param selector: WebKit xpath selector to an element
        @param wait_requests: How many requests to wait before returning. Useful
                              for AJAX requests.
        @param: timeout timeout to wait in seconds
        """
        element = self.webframe.findFirstElement(selector)
        return self.wk_click_element_ajax(element, wait_requests=wait_requests, timeout=timeout)

    # XXX: TODO: this method do not work by now, event seems not posted, strange
    def native_click(self, selector, wait_load=False, wait_requests=None, timeout=None, offsetx = 0, offsety = 0):
        """
        Click any clickable element in page by sending a raw QT mouse event.

        @param selector: jQuery selector.
        @param wait_load: If True, it will wait until a new page is loaded.
        @param timeout: Seconds to wait for the page to load before
                                       raising an exception.
        @param wait_requests: How many requests to wait before returning. Useful
                              for AJAX requests.

        @param offsetx: offset to click on the widget to the top left of it on the X axis (left to right)
        @param offsety: offset to click on the widget to the top left of it on the Y axix (top to bottom)
        """
        where = self.getPosition(selector)
        item = self.webframe.findFirstElement(selector)
        item.setFocus()
        where = QPoint(where.x() + offsetx, where.y() + offsety)
        self.nativeClickAt(where, timeout, real=True)
        self.wait_requests(wait_requests)
        if wait_load:
            return self._wait_load(timeout)

    # XXX: TODO: this method do not work by now, event seems not posted, strange
    def native_click_link(self, selector, timeout=None, offsetx = 0, offsety = 0):
        """Click a link and wait for the page to load using a real mouse event.
        @param selector: jQuery selector.
        @param timeout: Seconds to wait for the page to load before
                        raising an exception.
        @param offsetx: offset to click on the widget to the top left of it on the X axis (left to right)
        @param offsety: offset to click on the widget to the top left of it on the Y axix (top to bottom)
        """
        return self.native_click(selector, wait_load=True, timeout=timeout, offsetx=offsetx, offsety=offsety)

    # XXX: TODO: this method do not work by now, event seems not posted, strange
    def native_click_ajax(self, selector, wait_requests=1, timeout=None, offsetx = 0, offsety = 0):
        """Click a AJAX link using a raw mouse click and wait for the request to finish.
        @param selector: jQuery selector.
        @param timeout: Seconds to wait for the page to load before
                        raising an exception.
        @param offsetx: offset to click on the widget to the top left of it on the X axis (left to right)
        @param offsety: offset to click on the widget to the top left of it on the Y axix (top to bottom)
        """
        return self.native_click(selector, wait_requests=wait_requests, timeout=timeout, offsetx=offsetx, offsety=offsety)

    def wait_load(self, timeout=None):
        """
        Wait until the page is loaded.

        @param timeout: Time to wait (seconds) for the page load to complete.
        @return: Boolean state
        @raise SpynnerTimeout: If timeout is reached.
        """
        return self._wait_load(timeout)

    def wait_for_content(self, callback, tries=None, error_message=None, delay=5):
        """
        Wait until the page is loaded.

        @param content: callback that takes the browser as input must return true when suceed
        @param timeout: number of retries / True for no limit
        @param delay: delay between retries
        @param error_message: additional message to set in the error message
        @return: Boolean state
        @raise SpynnerTimeout: If timeout is reached.

        >>> def wait_toto(browser):
        ...     if 'toto' in browser.html:
        ...         return True
        ...     return False
        >>> br.wait_for_content(wait_toto)
        """
        ref_tries = tries
        ret = None
        found = False
        loaded = False
        if not tries:
            tries = True
        while bool(tries) and not found:
            if isinstance(tries, int) and not isinstance(tries, bool):
                if tries > 0:
                    tries -= 1
            if callback(self):
                found = True
            if not found:
                if not loaded:
                    try:
                        loaded = self._wait_load(timeout=delay)
                        self._debug(DEBUG, 'SPYNNER waitload: content loaded, waiting for content to mach the callback')
                    except SpynnerTimeout, e:
                        self._debug(DEBUG, 'SPYNNER waitload: content not loaded, fallback by waiting')
                else:
                    self._debug(DEBUG, 'SPYNNER waitload: content loaded, waiting for content to mach the callback')
                    time.sleep(delay)
        if not found:
            if not isinstance(ref_tries, int):
                ref_tries = 'unlimited'
            msg = u"SPYNNER waitload: Timeout reached: %d retries for %ss delay." % (ref_tries, delay)
            if error_message:
                msg += u'\n%s' % error_message
            raise SpynnerTimeout(msg)
        else:
            self._debug(DEBUG, 'SPYNNER waitload: The callback found what it was waiting for in its contents!')
        load_status = self._load_status
        self._load_status = None
        return load_status

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
        if self.manager:
            del self.manager
        if self.webpage:
            del self.webpage
        if self.webview:
            self.destroy_webview()
        self.application.exit()

    def search_element_text(self, search_text, element='a', case_sensitive=False, match_exactly=True):
        """
        Search all elements on a page for the specified text, returns a list of elements that contain it.

        @param search_text: The text to search for.
        @param element: The type of element to search, defaults to anchor tag.
        @param case_sensitive: If true the search will be case sensitive.
        @param match_exactly: If true will match the element's content exactly.
        @return: A list of elements
        """
        if not case_sensitive:
            search_text=search_text.lower()
        all_elements=self.webframe.findAllElements(element).toList()
        result=[]
        for e in all_elements:
            text=e.toPlainText().__str__()
            if not case_sensitive:
                text=text.lower()
            if match_exactly is True and search_text == text:
                result.append(e)
            elif match_exactly is False and search_text in text:
                result.append(e)
        return result

    #}

    #{ Webview

    def create_webview(self, show=False):
        """Create a QWebView object and insert current QWebPage."""
        if self.webview is not None: return
        self.webview = QWebView()
        self.webview.setPage(self.webpage)
        window = self.webview.window()
        window.setAttribute(Qt.WA_DeleteOnClose)
        window.connect(
            window, SIGNAL('destroyed(QObject *)'),
            self._on_webview_destroyed)
        if show:
            self.show()
        else:
            self.hide()

    def destroy_webview(self):
        """Destroy current QWebView."""
        if not self.webview:
            return
        self.webview.close()
        del self.webview

    def show(self, maximized=True):
        """Show webview browser."""
        self.create_webview(show=False)
        self.webview.show()
        if maximized:
            self.webview.setWindowState(Qt.WindowMaximized) 

    def hide(self):
        """Hide webview browser."""
        if self.webview is not None:
            self.webview.hide()
        else:
            self._debug(DEBUG, "Webview is not initialized")

    def browse(self):
        """Let the user browse the current page (infinite loop)."""
        if self.webview is None:
            self.create_webview()
        self.show()
        while self.webview:
            self._events_loop()

    #}

    #{ Webframe

    def set_webframe_to_default(self):
        self.webframe = self.webpage.mainFrame()

    def setframe_obj(self, frame):
        try:
           self.webframe = frame
        except:
            raise SpynnerError("childframe does not exist")
        self.load_js()

    def set_webframe(self, framenumber):
        cf = self.webframe.childFrames()
        f = cf[int(framenumber)]
        self.setframe_obj(f)

    #}

    #{ Form manipulation

    def fill(self, selector, value):
        """Fill an input text with a string value using a jQuery selector."""
        escaped_value = value.replace("'", "\\'")
        jscode = "%s('%s').val('%s')" % (self.jslib, selector, escaped_value)
        self._runjs_on_jquery("fill", jscode)

    def wk_fill(self, selector, value):
        """Fill an input text with a string value using a WebKit selector and using the webkit webframe object."""
        element = self.webframe.findFirstElement(selector)
        element.evaluateJavaScript("this.value = '%s'" % value)

    def wk_check_elem(self, element):
        """check an input checkbox using a webkit element."""
        jscode = "this.checked=true;"
        if not isinstance(element, list):
            element = [element]
        for e in element:
            e.evaluateJavaScript(jscode)

    def wk_uncheck_elem(self, element):
        """uncheck input checkbox using a Webkit element"""
        jscode = "this.checked=false;"
        if not isinstance(element, list):
            element = [element]
        for e in element:
            e.evaluateJavaScript(jscode)

    def wk_check(self, selector):
        """check an input checkbox using a css selector."""
        if not isinstance(selector, list):
            selector = [selector]
        elems = []
        for s in selector:
            es = self.webframe.findAllElements(s).toList()
            elems.extend(es)
        return self.wk_check_elem(elems)

    def wk_uncheck(self, selector):
        """uncheck input checkbox using a css selector"""
        if not isinstance(selector, list):
            selector = [selector]
        elems = []
        for s in selector:
            es = self.webframe.findAllElements(s).toList()
            elems.extend(es)
        return self.wk_uncheck_elem(elems)

    def check(self, selector):
        """Check an input checkbox using a jQuery selector."""
        if not isinstance(selector, list):
            selector = [selector]
        for s in selector:
            jscode = "%s('%s').attr('checked', true)" % (self.jslib, s)
            self._runjs_on_jquery("check", jscode)

    def uncheck(self, selector):
        """Uncheck input checkbox using a jQuery selector"""
        if not isinstance(selector, list):
            selector = [selector]
        for s in selector:
            jscode = "%s('%s').attr('checked', false)" % (self.jslib, s)
            self._runjs_on_jquery("uncheck", jscode)

    def radio(self, selector):
        """Choose a radio button a jQuery selector.
        Selector can be a single selector of a list of selectors
        """
        if not isinstance(selector, list):
            selector = [selector]
        jscode = ''
        for s in selector:
            jscode += "%s('%s').attr('checked', 'checked');\n" % (
                self.jslib, s)
        self._runjs_on_jquery("radio", jscode)

    def select(self, selector, remove=True):
        """Choose a option in a select using a jQuery selector.
        Selector can be a single selector of a list of selectors
        """
        if not isinstance(selector, list):
            selector = [selector]
        rjscode = ''
        jscode = ''
        for s in selector:
            if remove:
                rjscode += ("%s('option:selected', "
                            "%s('%s').parents('select')[0])"
                            ".removeAttr('selected');\n" )% (
                                self.jslib, self.jslib, s) 
            jscode += "%s('%s').attr('selected', 'selected');\n" % (
                self.jslib, s)
        jscode = rjscode + jscode
        self._runjs_on_jquery("select", jscode)

    def wk_radio(self, selector):
        """Choose a option in a select using  WebKit API.
        @param selector: list of  css selector or css selector  to get the select item.
        """
        if not isinstance(selector, list):
            selector = [selector] 
        for s in selector:
            element = self.webframe.findFirstElement(s)
            element.evaluateJavaScript('this.checked = true;') 

    def wk_select_elem(self, element, values, remove=True):
        """Choose a option in a select using  WebKit API.
        @param element: webkit WebElemement
        """
        toselect = []
        notselect = []
        all_options = []
        for option in element.findAll('option'):
            if not option in all_options:
                all_options.append(option)
            if values:
                for v in values:
                    if option.attribute('value') == v:
                        if not option in toselect:
                            toselect.append(option)
            else:
                toselect.append(option)
            if (not option in toselect) and remove:
                notselect.append(option)
        for option in toselect:
            option.evaluateJavaScript('this.selected = true;') 
        for option in notselect:
            option.evaluateJavaScript('this.selected = false;') 
 

    def wk_select(self, selector, values=None, remove=True):
        """Choose a option in a select using  WebKit API.
        @param selector: css selector to get the select item.
        @param values: string/list of string of values to set pass a single value for a single value.
        """
        element = self.webframe.findFirstElement(selector)
        if not isinstance(values, list) and (values is not None):
            values = [values]
        return self.wk_select_elem(element, values, remove)


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
        use C{jq(...)} instead of of C{jQuery} or the common {$(...)}
        shortcut.

        @note: You can change the jq alias (see L{jslib}).
        """
        if debug:
            self._debug(DEBUG, "Run Javascript code: %s" % jscode)

        #XXX evaluating JS twice must be wrong but finding the bug is proving tricky...
        #JavaScriptCore/interpreter/Interpreter.cpp and JavaScriptCore/runtime/Completion.cpp
        #JavaScriptCore/runtime/Completion.cpp is catching an exception (sometimes) and
        #returning "TypeError: Type error" - BUT it looks like the JS does complete after
        #the function has already returned
        res = self.webframe.evaluateJavaScript(jscode)
        js_has_runned_successfully = res.isValid() or res.isNull()
        if not js_has_runned_successfully:
            # try another time
            res = self.webframe.evaluateJavaScript(jscode)
        return res

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

    #{ Proxies

    def get_proxy(self):
        """Return string containing the current proxy."""
        return self.manager.proxy()

    def set_proxy(self, string_proxy):
        """Set proxy [http|socks5]://username:password@hostname:port"""
        urlinfo = urlparse.urlparse(string_proxy)

        proxy = QNetworkProxy()
        if urlinfo.scheme == 'socks5' :
                proxy.setType(1)
        elif urlinfo.scheme == 'http' :
                proxy.setType(3)
        else :
                proxy.setType(2)
                self.manager.setProxy(proxy)
                return self.manager.proxy()

        proxy.setHostName(urlinfo.hostname)
        proxy.setPort(urlinfo.port)
        if urlinfo.username != None :
                proxy.setUser(urlinfo.username)
        else :
                proxy.setUser('')

        if urlinfo.password != None :
                proxy.setPassword(urlinfo.password)
        else :
                proxy.setPassword('')

        self.manager.setProxy(proxy)
        return self.manager.proxy()

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
        # create a copy of the cookies jar to prevent
        # CJ to be garbage collected
        cj = _ExtendedNetworkCookieJar()
        cj.setAllCookies(self.cookiesjar.allCookies())
        manager.setCookieJar(cj)
        reply = manager.get(request)
        if reply.error():
            raise SpynnerError("Download error: %s" % reply.errorString())
        reply.downloaded_nbytes = 0
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
        lines = [get_line(cookie) for cookie in self.allCookies()]
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

