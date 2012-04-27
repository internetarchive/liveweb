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
import sys

from warc import arc
from warc.utils import FilePart
from . import filetools
from . import config

MEG = 1024 * 1024

EMPTY_BUFFER = filetools.MemFile()

ERR_INVALID_URL = 10, "invalid URL"
ERR_INVALID_DOMAIN = 20, "invalid domain"
ERR_DNS_TIMEOUT = 21, "dns timeout"
ERR_CONN_REFUSED = 30, "connection refused"
ERR_CONN_DROPPED = 31, "connection dropped"
ERR_CONN_MISC = 39, "connection error"
ERR_TIMEOUT_CONNECT = 40, "timeout when connecting"
ERR_TIMEOUT_HEADERS = 41, "timeout when reading headers"
ERR_TIMEOUT_BODY = 42, "timeout when reading body"

class ProxyError(Exception):
    def __init__(self, error, cause=None):
        self.errcode, self.errmsg = error

        msg = "E%02d: %s (%s)" % (self.errcode, self.errmsg, cause)
        Exception.__init__(self, msg)

class Record:
    """A class to hold together the filepath, content_length, and iterator over content.
    """
    def __init__(self, filename, offset=0, content_length=None, content_iter=None):
        """Creates a new record instance.

        :param filename: Relative or absolute path to the file that has this record.
        :param offset: The offset in the file where this record started.
        :param content_length: The total length of the record.
        :param content_iter: An iterator over content.
        """
        self.filename = filename
        self.offset = offset
        self.content_length = content_length
        self.content_iter = content_iter

        if self.content_length is None:
            self.content_length = os.stat(filepath).st_size

        if self.content_iter is None:
            f = open(self.filename, 'rb')
            f.seek(self.offset)
            self.content_iter = filetools.fileiter(f, self.content_length)

    def read_all(self):
        """Reads all the data from content_iter and reinitializes the
        content_iter with the data read.

        Since this reads all the data into memory, this should be used
        only when content_length is not very big.
        """
        data = "".join(self.content_iter)
        self.content_iter = iter([data])
        return data

    def __iter__(self):
        return iter(self.content_iter)

def split_type_host(url):
    """Returns (type, host, selector) from the url.
    """
    type, rest = urllib.splittype(url)
    host, selector = urllib.splithost(rest)
    return type, host, selector


def log_error(err):
    code, msg = err
    exc_type, exc_value, _ = sys.exc_info()
    logging.error("E%02d - %s (%s)", code, msg, str(exc_value))

def urlopen(url):
    """Works like urllib.urlopen, but returns a ProxyHTTPResponse object instead.
    """
    logging.info("urlopen %s", url)
 
    try:
        return _urlopen(url)
    except ProxyError, e:
        logging.error("%s - %s", str(e), url)
        response = ProxyHTTPResponse(url, None, method="GET")
        response.error_bad_gateway()
        return response

def _urlopen(url):
    """urlopen without the exception handling.
    
    Called by urlopen and test cases.
    """
    headers = {
        "User-Agent": config.user_agent,
        "Connection": "close"
    }
    type, host, selector = split_type_host(url)

    conn = ProxyHTTPConnection(host, url=url, timeout=config.timeout)
    conn.request("GET", selector, headers=headers)
    return conn.getresponse()

class _FakeSocket:
    """Faking a socket with makefile method.
    """
    def __init__(self, fileobj=None):
        self.fileobj = fileobj or StringIO()

    def makefile(self, mode="rb", bufsize=0):
        return self.fileobj
    
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
            self.header_offset = self.buf.tell()
        except socket.error, e:
            raise ProxyError(ERR_TIMEOUT_HEADERS, str(e))

        try:
            # This will read the whole payload, taking care of content-length,
            # chunked transfer-encoding etc.. The spy file will record the real
            # HTTP payload.
            self.read()
        except httplib.IncompleteRead:
            # XXX: Should this be a new error code?
            raise ProxyError(ERR_CONN_DROPPED)
        except socket.error, e:
            raise ProxyError(ERR_TIMEOUT_BODY, str(e))
        
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
        self.header_offset = 0
    
    def write_arc(self, pool):
        record = self._make_arc_record()

        # if small enough, store in memory
        if record.header.length < MEG: 
            # write ARC record into memory
            buf = StringIO()
            begin, record_size = self._write_arc_record(record, buf)
                        
            # write the ARC record data in memory into file
            with pool.get_file() as f:
                logging.info("writing arc record to file %s", f.name)
                f.write(buf.getvalue())
                filename = f.name
                
            return Record(filename, offset=0, content_length=record_size, content_iter=iter([buf.getvalue()]))
        else:
            with pool.get_file() as f:
                logging.info("writing arc record to file %s", f.name)
                filename = f.name
                begin, record_size = self._write_arc_record(record, f)

            return Record(filename, offset=begin, content_length=record_size)
                
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
                        
    def _make_arc_record(self):
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
    
        headers = dict(url = self.url,
                       date = self._utcnow(),
                       content_type = self.content_type,
                       ip_address = self.remoteip,
                       length = payload_length)
        return arc.ARCRecord(headers = headers, 
                             payload = payload,
                             version = 1)

    def _utcnow(self):
        """Returns datetime.datetime.utcnow(). 

        Provided as a method here so that it is easy to monkeypatch for testing.
        """
        return datetime.datetime.utcnow()
    
    def write_warc(self, pool):
        raise NotImplementedError()
        
    def get_arc(self):
        """Returns size and fileobj to read arc data.
        
        This must be called only after calling write_arc method.
        """
        if self.arc_data is None:
            self.write_arc()
        return self.arc_size, self.arc_data
    
    def get_warc(self):
        """Returns size and fileobj to read warc data."""
        raise NotImplementedError()
        
    def get_payload(self):
        """Returns size and fileobj to read HTTP payload.
        """
        # go to the end find the filesize
        self.buf.seek(0, 2)
        size = self.buf.tell() - self.header_offset

        # go to the beginning
        self.buf.seek(self.header_offset)
        return filetools.fileiter(self.buf, size)


class ProxyHTTPConnection(httplib.HTTPConnection):
    """HTTPConnection wrapper to add extra hooks to handle errors.
    """

    def __init__(self, host, url, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        try:
            httplib.HTTPConnection.__init__(self, host, timeout=timeout)
        except httplib.InvalidURL, e:
            raise ProxyError(ERR_INVALID_URL, str(e))

        self.url = url
        self.response_class = lambda *a, **kw: ProxyHTTPResponse(self.url, *a, **kw)

    def connect(self):
        try:
            # Add . to the hostname to tell the DNS server to not use the search domain
            ip = socket.gethostbyname(self.host + ".")
            self.sock = socket.create_connection((ip, self.port), self.timeout)
        except socket.gaierror, e:
            raise ProxyError(ERR_INVALID_DOMAIN, str(e))
        except socket.timeout, e:
            raise ProxyError(ERR_TIMEOUT_CONNECT, str(e))
        except socket.error, e:
            msg = e.strerror or ""
            if msg.lower() == "connection refused":
                raise ProxyError(ERR_CONN_REFUSED, str(e))
            else:
                raise ProxyError(ERR_CONN_MISC, str(e))

    def request(self, method, url, body=None, headers={}):
        try:
            httplib.HTTPConnection.request(self, method, url, body=body, headers=headers)
        except socket.error, e:
            raise ProxyError(ERR_CONN_MISC, str(e))
