from cStringIO import StringIO
import httplib

def spy(fileobj):
    """Returns a new file wrapper the records the contents of a file
    as someone is reading from it.
    """
    return SpyFile(fileobj)

class SpyFile:
    """File wrapper to record the contents of a file as someone is
    reading from it.
    """
    def __init__(self, fileobj):
        self.fileobj = fileobj
        self.buf = StringIO()

    def read(self, *a, **kw):
        text = self.fileobj.read(*a, **kw)
        self.buf.write(text)
        return text

    def readline(self, *a, **kw):
        text = self.fileobj.readline(*a, **kw)
        self.buf.write(text)
        return text
    
    def close(self):
        self.fileobj.close()
    
        

class SpyHTTPResponse(httplib.HTTPResponse):
    def __init__(self, *a, **kw):
        httplib.HTTPResponse.__init__(self, *a, **kw)
        self.fp = spy(self.fp)

def test():
    import httplib
    conn = httplib.HTTPConnection("openlibrary.org")
    conn.response_class = SpyHTTPResponse

    conn.request("GET", "/")
    res = conn.getresponse()
    fp = res.fp

    print fp.buf.getvalue()

    res.read()
    print fp.buf.getvalue()

if __name__ == "__main__":
    test()
