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

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

class MyHandler(BaseHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        self.basedir = kwargs.pop("basedir")    
        self.verbose = kwargs.pop("verbose")
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)
        
    def do_GET(self):        
        path = re.sub("\?.*$", "", self.path.strip("/"))
        filepath = os.path.join(self.basedir, path)
        if not os.path.isfile(filepath):
            self.send_error(404, 'File Not Found: %s' % path)
            return
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(open(filepath).read())
     
    def do_POST(self):
        ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
        self.send_response(200)        
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write("<html></html>");

    def log_message(self, *args):
        if self.verbose:
            BaseHTTPRequestHandler.log_message(self, *args)
        
def get_handler_factory(basedir, verbose):
    def factory(*args):
        return MyHandler(*args, basedir=basedir, verbose=verbose)
    return factory
        
def get_server(host, port, basedir, verbose=False):
    return HTTPServer((host, port), get_handler_factory(basedir, verbose))

def main():
    server = get_server('', 8081)
    print 'started HTTP server'
    server.serve_forever()

if __name__ == '__main__':
    main()
