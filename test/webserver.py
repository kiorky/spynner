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

import os
import re
import cgi
import base64

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        self.basedir = kwargs.pop("basedir")    
        self.verbose = kwargs.pop("verbose")
        self.protected = kwargs.pop("protected")
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)
        
    def _debug_headers(self, headers):
        if self.verbose:
            for header in headers.headers:
                print header,
            
    def do_GET(self):
        request_headers = self.headers.headers[:]
        self._debug_headers(request_headers)        
        path = re.sub("\?.*$", "", self.path.strip("/"))
        filepath = os.path.join(self.basedir, path)
        if not os.path.isfile(filepath):
            self.send_error(404, 'File Not Found: %s' % path)
            return
        if self.protected and self.path in self.protected:
            correct = base64.b64encode('myuser:mypassword')
            authorization = self.headers.getheader('authorization')
            if not authorization or not authorization.split()[1] == correct:
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm="webserver"')
                self.end_headers()
                return
        self.send_response(200)
        extension = os.path.splitext(filepath)
        if extension in ("html", "htm"):
            self.send_header('Content-type', 'text/html')
        self.end_headers()
        sheaders = "<br />".join(request_headers)
        html = open(filepath).read().replace("$headers", sheaders)         
        self.wfile.write(html)
     
    def do_POST(self):
        ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
        self.send_response(200)        
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write("<html></html>");

    def log_message(self, *args):
        if self.verbose:
            BaseHTTPRequestHandler.log_message(self, *args)
        
def get_handler_factory(basedir, verbose, protected):
    def factory(*args):
        return Handler(*args, basedir=basedir, verbose=verbose, protected=protected)
    return factory
        
def get_server(host, port, basedir, verbose=False, protected=None):
    return HTTPServer((host, port), get_handler_factory(basedir, verbose, protected))

def main():
    basedir = os.path.join(os.path.dirname(__file__), "fixtures")
    server = get_server('', 8081, basedir, True, ("/protected.html",))
    print 'started HTTP server'
    server.serve_forever()

if __name__ == '__main__':
    main()
