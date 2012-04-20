"""The proxy functionality.
"""

import datetime
import gzip
import httplib
import logging
import socket
import urllib
from cStringIO import StringIO
import tempfile

from warc import arc
from warc.utils import FilePart
from . import filetools
from . import config

MEG = 1024 * 1024

EMPTY_BUFFER = filetools.MemFile()

def split_type_host(url):
    """Returns (type, host, selector) from the url.
    """
    type, rest = urllib.splittype(url)
    host, selector = urllib.splithost(rest)
    return type, host, selector

def urlopen(url):
    """Works like urllib.urlopen, but returns a ProxyHTTPResponse object instead.
    """
    logging.info("urlopen %s", url)
    type, host, selector = split_type_host(url)
    
    try:
        conn = httplib.HTTPConnection(host, timeout=config.timeout)
    except httplib.InvalidURL, e:
        logging.error("Invalid URL (%s)", str(e))
        response = ProxyHTTPResponse(url, None, method="GET")
        response.error_bad_url()
        return response
    
    headers = {
        "User-Agent": config.user_agent
    }
    
    try:
        conn.request("GET", selector, headers=headers)
    except socket.error, e:
        logging.error("Connection failed, considering as bad gateway. (%s)", str(e))
        response = ProxyHTTPResponse(url, None, method="GET")
        response.error_bad_gateway()
        return response
    
    conn.response_class = lambda *a, **kw: ProxyHTTPResponse(url, *a, **kw)
    return conn.getresponse()
    
class _FakeSocket:
    """Faking a socket with makefile method.
    """
    def makefile(self, mode="rb", bufsize=0):
        return StringIO()
    
    def getpeername(self):
        return ("0.0.0.0", 80)
    
class ProxyHTTPResponse(httplib.HTTPResponse):
    """HTTPResponse wrapper to record the HTTP payload.
    
    Provides utility methods to write ARC and WARC files.
    """
    DEFAULT_CONTENT_TYPE = "unk"
    
    def __init__(self, url, sock, *a, **kw):
        sock = sock or _FakeSocket()
        httplib.HTTPResponse.__init__(self, sock, *a, **kw)
        self.pool = filetools.DummyFilePool()
        
        self.url = url
        self.remoteip = sock.getpeername()[0]
        self.content_type = self.DEFAULT_CONTENT_TYPE
        self.buf = EMPTY_BUFFER
        
        # Length of header data
        self.header_offset = 0
        
        self.arc_size = None
        self.arc_data = None

    def begin(self):
        self.fp = filetools.SpyFile(self.fp, spy=filetools.MemFile())
        self.buf = self.fp.buf
        
        try:
            httplib.HTTPResponse.begin(self)
            self.content_type = self.getheader("content-type", self.DEFAULT_CONTENT_TYPE).split(';')[0]
        except socket.error:
            self.error_bad_gateway()
            
        self.header_offset = self.buf.tell()
        self._read_all()
        
    def _read_all(self):
        try:
            # This will read the while payload, taking care of content-length,
            # chunked transfer-encoding etc.. The spy file will record the real
            # HTTP payload.
            self.read()
        except socket.error:
            self.error_bad_gateway()
            
    def cleanup(self):
        self.buf.close()
        
    def error_bad_gateway(self):
        """Resets the status code to "502 Bad Gateway" indicating that there was 
        some network error when trying to accessing the server.
        """
        self._error(502, "Bad Gateway")
        
    def error_bad_url(self):
        """Resets the status code to "400 Bad Request" indicating that the URL provided is bad.
        """
        self._error(400, "Bad Request")
        
    def _error(self, status, reason):
        self.version = "HTTP/1.1"
        self.status = status
        self.reason = reason
        self.content_type = self.DEFAULT_CONTENT_TYPE
        
        # close file
        if self.fp:
            self.fp.close()
            self.fp = None
            
        self.buf = EMPTY_BUFFER
    
    def write_arc(self):
        record = self._make_arc_record(self.url)

        # if small enough, store in memory
        if record.header.length < MEG: 
            # write ARC record into memory
            buf = StringIO()
            begin, record_size = self._write_arc_record(record, buf)
                        
            # write the ARC record data in memory into file
            with self.pool.get_file() as f:
                logging.info("writing arc record to file %s", f.name)
                f.write(buf.getvalue())
                
            # use the memory buffer as fileobj
            fileobj = buf
        else:
            with self.pool.get_file() as f:
                logging.info("writing arc record to file %s", f.name)
                filename = f.name
                begin, record_size = self._write_arc_record(record, f)
            fileobj = open(filename)
        
        fileobj.seek(begin)
        self.arc_size = record_size
        self.arc_data = filetools.fileiter(fileobj, record_size)
                
    def _write_arc_record(self, record, fileobj):
        """Writes the give ARC record into the given fileobj as gzip data and returns the start offset in the file and and record size.
        """
        begin = fileobj.tell()
        
        zfile = gzip.GzipFile(fileobj=fileobj, filename=None, mode="w")
        record.write_to(zfile)
        zfile.close()
        fileobj.flush()
        
        end = fileobj.tell()
        return begin, end-begin
        
                        
    def _make_arc_record(self, url):
        if self.status == 502:
            # Match the response of liveweb 1.0 incase of gateway errors.
            payload = "HTTP 502 Bad Gateway\n\n"
            payload_length = len(payload)
            content_type = "unk"
            remoteip = "0.0.0.0"
        else:
            # We've finished writing to the buf. The file-pointer will be at 
            # the end of the file. Calling tell should give the file size.
            payload_length = self.buf.tell()
            
            # move the file pointer to the beginning of the file, so that we can read
            self.buf.seek(0) 
            payload =  self.buf
            remoteip = self.remoteip
            content_type = self.content_type
    
        headers = dict(url = url,
                       date = datetime.datetime.utcnow(),
                       content_type = self.content_type,
                       ip_address = self.remoteip,
                       length = payload_length)
        return arc.ARCRecord(headers = headers, 
                             payload = payload,
                             version = 1)
        
    def write_warc(self, pool):
        raise NotImplementedError()
        
    def get_arc(self):
        """Returns size and fileobj to read arc data."""
        if self.arc_data is None:
            self.write_arc()
        return self.arc_size, self.arc_data
    
    def get_warc(self):
        """Returns size and fileobj to read warc data."""
        raise NotImplementedError()
        
    def get_payload(self):
        """Returns size and fileobj to read HTTP payload.
        """
        if self.arc_data is None:
            self.write_arc()

        # go to the end find the filesize
        self.buf.seek(0, 2)
        size = self.buf.tell() - self.header_offset

        # go to the beginning
        self.buf.seek(self.header_offset)
        return filetools.fileiter(self.buf, size)
