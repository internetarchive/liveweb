"""Really simple implememtation of wayback machine web-interface. 

Written to test the liveweb proxy implementation.
"""

import sys
import httplib
import gzip
import re
import traceback
from StringIO import StringIO

import warc

# We expect that liveweb host:port is passed as argument to this script.
liveweb = sys.argv[1]

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

class application(wsgiapp):
    """WSGI application for wayback machine prototype.
    """
    urls = [
        ("/", "index"),
        ("/web/(.*)", "web")
    ]
        
    def GET_index(self):
        self.header("content-type", "text/html")
        return ["Welcome\n"]

    def GET_web(self, url):
        record = self.fetch_arc_record(url)
        f = StringIO(record.payload)
        f.makefile = lambda *a: f
        
        response = httplib.HTTPResponse(f)
        response.begin()
        h = dict(response.getheaders())
        
        self.header("Content-Type", h.get("content-type", "text/plain"))

        if 'content-length' in h:
            self.header('Content-Length', h['content-length'])
        return [response.read()]

    def fetch_arc_record(self, url):
        """Fetchs the ARC record data from liveweb proxy.
        """
        conn = httplib.HTTPConnection(liveweb)
        conn.request("GET", url)
        content = conn.getresponse().read()

        gz = gzip.GzipFile(fileobj=StringIO(content), mode="rb")

        f = warc.ARCFile(fileobj=gz, version=1)
        f.header_read = True
        record = f.read_record()
        return record
