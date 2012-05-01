"""Really simple wsgi framework. 
"""

import re
import traceback

class wsgiapp:
    """Simple WSGI web framework.
    
        class applicaiton(wsgiapp):
            urls = [
                ("/", "index")
            ]
            def GET_index(self):
                self.header("Content-Type", "text/plain")
                return "hello, world!"
    """
    def __init__(self, environ, start_response):
        self.start = start_response
        self.environ = environ
        
        self.status = "200 OK"
        self._headers = {}
        
    def header(self, name, value):
        self._headers[name.title()] = value

    def __iter__(self):
        try:
            x = self.delegate()
            self.start(self.status, self._headers.items())
            return iter(x)
        except:
            headers = {"Content-Type": "text/plain"}
            self.start("500 Internal Error", headers.items())
            out = "Internal Error:\n\n"
            exc = traceback.format_exc()
            return iter([out, exc])

    def delegate(self):
        """Delegates the request to appropriate method.
        """
        path = self.environ['PATH_INFO']
        method = self.environ['REQUEST_METHOD']

        # Try each pattern and dispatch to the right method
        for pattern, name in self.urls:
            m = re.match('^' + pattern + '$', path)
            if m:
                funcname = method.upper() + "_" + name
                f = getattr(self, funcname)
                return f(*m.groups())
                
        # give "404 Not Found" if all the patterns are exhausted
        return self.notfound()

    def notfound(self):
        self.start("404 Not Found", {"Content-Type": "text/html"}.items())
        return ["Not Found"]

