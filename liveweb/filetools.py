from cStringIO import StringIO
import httplib
import tempfile
import logging
import os

def spy(fileobj, spyobj = None):
    """Returns a new file wrapper the records the contents of a file
    as someone is reading from it.
    """
    return SpyFile(fileobj, spyobj)

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
    def __init__(self, fileobj, spy = None):
        self.fileobj = fileobj
        self.buf = spy or StringIO()

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

    def change_spy(self, fileobj):
        "Changes the file which recives the spied upon data to fileobj"
        self.buf.flush()
        self.buf.close()
        self.buf = fileobj
        

class SpyHTTPResponse(httplib.HTTPResponse):
    def __init__(self, *a, **kw):
        httplib.HTTPResponse.__init__(self, *a, **kw)
        self.fp = spy(self.fp)


class MemFile:
    """Something like StringIO, but switches to a temp file when the maxsize is crossed.
    """
    def __init__(self, maxsize=1024*1024, tmpdir=None, prefix="memfile-", suffix=".tmp"):
        self.maxsize = maxsize
        
        self.tmpdir = tmpdir
        self.prefix = prefix
        self.suffix = suffix

        self._fileobj = StringIO()
        
    def in_memory(self):
        """Returns True if the file is in memory."""
        return not isinstance(self._fileobj, file)
        
    def __getattr__(self, name):
        return getattr(self._fileobj, name)
        
    def _open_tmpfile(self):
        filename = tempfile.mktemp(dir=self.tmpdir, prefix=self.prefix, suffix=self.suffix)
        logging.info("creating temp file %s", filename)
        # w+ mode open file for both reading and writing
        return open(filename, "w+")
        
    def _switch_to_disk(self):
        content = self._fileobj.getvalue()
        self._fileobj = self._open_tmpfile()
        self._fileobj.write(content)
        
    def write(self, data):
        if self.in_memory() and self.tell() + len(data) > self.maxsize:
            self._switch_to_disk()
        self._fileobj.write(data)
        
    def writelines(self, lines):
        for line in lines:
            self.write(line)
            
    def close(self):
        """Deletes the temp file if created.
        """
        if self._fileobj and not self.in_memory():
            logging.info("removing temp file %s", self._fileobj.name)
            os.unlink(self._fileobj.name)

class DummyFilePool:
    """Simple implementation of FilePool.
    """
    counter = 0
    
    def get_file(self):
        filename = "/tmp/record-%d.arc.gz" % self.counter
        while os.path.exists(filename):
            self.counter += 1
            filename = "/tmp/record-%d.arc.gz" % self.counter
        return open(filename, "w")

def fileiter(file, size, chunk_size=1024*10):
    """Returns an iterator over the file for specified size.
    
    The chunk_size specified the amount of data read in each step.
    """
    completed = 0
    while completed < size:
        nbytes = min(size-completed, chunk_size)
        content = file.read(nbytes)
        if not content:
            break
        yield content
        completed += len(content)
        
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
