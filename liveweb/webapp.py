"""The webapp for arc proxy.
"""

import arc_proxy
import gzip
from cStringIO import StringIO

class application:
    """WSGI application for liveweb proxy.
    """
    def __init__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response
        
    def parse_request(self):
        self.method = self.environ['REQUEST_METHOD']
        self.url = self.environ['PATH_INFO']
        
    def __iter__(self):
        self.parse_request()
        
        status = '200 OK'
        response_headers = [
            ('Content-type', 'application/x-arc-record')
        ]
        
        record = arc_proxy.get(self.url)
        self.start_response(status, response_headers)
        
        f = StringIO()
        
        gz = gzip.GzipFile(fileobj=f, mode="wb")
        record.write_to(gz, version=1)
        gz.close()
        
        yield f.getvalue()