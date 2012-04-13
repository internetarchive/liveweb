"""The webapp for arc proxy.
"""

from cStringIO import StringIO
import gzip
import logging

from . import arc_proxy
from . import errors


class application:
    """WSGI application for liveweb proxy.
    """
    def __init__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response
        
    def parse_request(self):
        self.method = self.environ['REQUEST_METHOD']
        if 'REQUEST_URI' in self.environ: # This is for uwsgi
            self.url = self.environ['REQUEST_URI'] #TODO: Is this a valid environment variable always?
        if 'RAW_URI' in self.environ: # This is for gunicorn
            self.url = self.environ['RAW_URI'] #TODO: Is this a valid environment variable always?
            
        

        # Allow accessing the proxy using regular URL so that we can use
        # tools like ab.
        if self.url.startswith("/_web/"):
            self.url = self.url[len("/_web/"):]
            
        # Since this is a proxy, the URL is always of the form http://hostname/path
        # nginx is stripping the http://host from the passed URL and just passing the /path here.
        # This is a work-around for that issue.
        if self.url.startswith("/"):
            self.url = "http://" + self.environ['HTTP_HOST'] + self.url
            
    def __iter__(self):
        try:
            self.parse_request()
            size, fileobj = arc_proxy.get(self.url)
            return self.success(size, fileobj)
        except errors.BadURL:
            logging.error("bad url %r", self.url)
            return self.error("400 Bad Request")
        except errors.ConnectionFailure:
            logging.error("Connection failure", exc_info=True)
            return self.error("502 Bad Gateway")
        except:
            logging.error("Internal Error", exc_info=True)
            return self.error("500 Internal Server Error")
            
    def success(self, clen, data):
        status = '200 OK'
        response_headers = [
            ('Content-type', 'application/x-arc-record'),
            ('Content-Length', str(clen))
        ]
        self.start_response(status, response_headers)
        return iter(data)
        
    def error(self, status, headers=None):
        if headers is None:
            headers = [
                ('Content-Type', 'text/plain'),
                ('Content-Length', '0'),
            ]
        self.start_response(status, headers)
        return iter([])
