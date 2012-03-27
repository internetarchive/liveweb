"""The webapp for arc proxy.
"""

import arc_proxy

class application:
    """WSGI application for liveweb proxy.
    """
    def __init__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response
        
    def __iter__(self):
        status = '200 OK'
        response_headers = [('Content-type', 'text/plain')]
        self.start_response(status, response_headers)
        yield "hello world!\n"