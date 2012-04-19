from cStringIO import StringIO
import httplib
import logging

from . import config

class SizeLimitExceeded(IOError): pass


def spy(fileobj, spyobj = None, max_size = None):
    """Returns a new file wrapper the records the contents of a file
    as someone is reading from it.
    """
    return SpyFile(fileobj, spyobj, max_size)

class SpyFile:
    """File wrapper to record the contents of a file as someone is
    reading from it.

    If the "spy" parameter is passed, it will be the stream to which
    the read data is written.

    SpyFile works like a "tee"
                          
                        -------------
     Actual client <--- SpyFileObject <--- Data Source
                        ____     ____
                            \ | /    
                              |      
                              V      
                             spy     
                         (spy object) 
    
                              
    """
    def _check_size(self):
        """Raises SizeLimitExceeded if the SpyFile has seen more data
        than the specified limit"""
        if self.max_size:
            if self.current_size > int(self.max_size):
                raise SizeLimitExceeded("Spy file limit exceeded %d (max size : %d)"%(self.current_size, self.max_size))

    def __init__(self, fileobj, spy = None, max_size = None):
        self.fileobj = fileobj
        self.buf = spy or StringIO()
        self.max_size = max_size
        self.current_size = 0

    def read(self, *a, **kw):
        text = self.fileobj.read(*a, **kw)
        self.buf.write(text)
        self.current_size += len(text)
        self._check_size()
        return text

    def readline(self, *a, **kw):
        text = self.fileobj.readline(*a, **kw)
        self.buf.write(text)
        self.current_size += len(text)
        self._check_size()
        return text
    
    def close(self):
        self.fileobj.close()

    def change_spy(self, fileobj):
        "Changes the file which recives the spied upon data to fileobj"
        self.buf.flush()
        self.buf.close()
        self.buf = fileobj
    
        

class SpyHTTPResponse(httplib.HTTPResponse):
    def __init__(self, *a, **kw):
        httplib.HTTPResponse.__init__(self, *a, **kw)
        from . import config
        self.fp = spy(self.fp, None, config.max_payload_size)

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
