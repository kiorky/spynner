#!/usr/bin/python
import string
import cgi
import time
import os
import re

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
        if ctype == 'multipart/form-data':
            query=cgi.parse_multipart(self.rfile, pdict)
        self.send_response(301)        
        self.end_headers()
        upfilecontent = query.get('upfile')
        #print "filecontent", upfilecontent[0]
        self.wfile.write("<HTML>POST OK.<BR><BR>");
        self.wfile.write(upfilecontent[0]);

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
