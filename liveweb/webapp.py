"""The webapp for arc proxy.
"""


from cStringIO import StringIO
import gzip
import logging

import arc_proxy

logging.basicConfig(level = logging.DEBUG)

class application:
    """WSGI application for liveweb proxy.
    """
    def __init__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response
        
    def parse_request(self):
        self.method = self.environ['REQUEST_METHOD']
        self.url = self.environ['REQUEST_URI'] #TODO: Is this a valid environment variable always?

        # Allow accessing the proxy using regular URL so that we can use
        # tools like ab.
        if self.url.startswith("/_web/"):
            self.url = self.url[len("/_web/"):]

    def __iter__(self):
        try:
            self.parse_request()
            
            status = '200 OK'
            response_headers = [
                ('Content-type', 'application/x-arc-record')
            ]
            logging.debug("Fetching and archiving %s",self.url)

            size, fileobj = arc_proxy.get(self.url)
            self.start_response(status, response_headers)
            return iter(fileobj)
        except:
            logging.error("Internal Error", exc_info=True)
