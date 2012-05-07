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
import errno
import time

from warc import arc
from warc.utils import FilePart
from . import filetools
from . import config

MEG = 1024 * 1024

EMPTY_BUFFER = filetools.MemFile()

# 1x - bad input
ERR_INVALID_URL = 10, "invalid URL"

# 2x - DNS errors 
ERR_INVALID_DOMAIN = 20, "invalid domain"
ERR_DNS_TIMEOUT = 21, "dns timeout"

# 3x - connction errors
ERR_CONN_REFUSED = 30, "connection refused"
ERR_CONN_TIMEOUT = 31, "connection timedout"
ERR_INITIAL_DATA_TIMEOUT = 32, "initial data timeout"
ERR_READ_TIMEOUT = 33, "read timeout"
ERR_CONN_DROPPED = 34, "connection dropped"
ERR_CONN_MISC = 39, "unexpected connection error"

# 4x - resource errors
ERR_RESPONSE_TOO_BIG = 40, "response too big"
ERR_REQUEST_TIMEOUT = 41, "request took too long to finish"

class ProxyError(Exception):
    def __init__(self, error, cause=None, data=None):
        self.errcode, self.errmsg = error

        if isinstance(cause, socket.error) and cause.errno:
            cause_msg = "%s: %s" % (errno.errorcode.get(cause.errno, cause.errno), cause.strerror)
        else:
            cause_msg = cause and str(cause)

        msg = "E%02d: %s" % (self.errcode, self.errmsg)

        if cause_msg:
            msg += " " + cause_msg

        if data:
            msg += " %s" % data

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

    conn = ProxyHTTPConnection(host, url=url)
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

    def settimeout(self, timeout):
        pass

class SocketWrapper:
    """The socket.socket class doesn't have a way to enforce max-time and max-size limits.

    This extends the socket functionality by adding those constraints.
    """
    def __init__(self, sock, max_time=None, max_size=None):
        self._sock = sock
        self._max_time = max_time
        self._max_size = max_size
        
        self._start_time = time.time()
        self._bytes_read = 0

    def __getattr__(self, name):
        return getattr(self._sock, name)

    def recv(self, bufsize):
        data = self._sock.recv(bufsize)
        self._bytes_read += len(data)

        # TODO: optimize this
        # Each time.time() call takes about 0.35 ns. 
        # For reading headers, this function is called once of each byte.
        # Assuming that the headers is 1000 bytes long, it will add an overhead of 0.35ms.
        # We should optimize this if we care about half-a-milli-second.
        
        if self._max_time is not None and time.time() - self._start_time > self._max_time:
            raise ProxyError(ERR_REQUEST_TIMEOUT, data={"max_time": self._max_time})

        if self._max_size is not None and self._bytes_read > self._max_size:
            raise ProxyError(ERR_RESPONSE_TOO_BIG, data={"max_size": self._max_size})

        return data

    def makefile(self, mode='r', bufsize=-1):
        return socket._fileobject(self, mode, bufsize)

class ProxyHTTPResponse(httplib.HTTPResponse):
    """HTTPResponse wrapper to record the HTTP payload.
    
    Provides utility methods to write ARC and WARC files.
    """
    DEFAULT_CONTENT_TYPE = "unk"
    
    def __init__(self, url, sock, *a, **kw):
        self.sock = sock or _FakeSocket()
        httplib.HTTPResponse.__init__(self, self.sock, *a, **kw)
        
        self.url = url
        self.remoteip = self.sock.getpeername()[0]
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
            self.sock.settimeout(config.get_initial_data_timeout())
            httplib.HTTPResponse.begin(self)
            self.content_type = self.getheader("content-type", self.DEFAULT_CONTENT_TYPE).split(';')[0]
            self.header_offset = self.buf.tell()
        except socket.error, e:
            raise ProxyError(ERR_INITIAL_DATA_TIMEOUT, str(e), {"initial_data_timeout": config.get_initial_data_timeout()})

        try:
            # This will read the whole payload, taking care of content-length,
            # chunked transfer-encoding etc.. The spy file will record the real
            # HTTP payload.
            self.sock.settimeout(config.get_read_timeout())
            self.read()
        except httplib.IncompleteRead:
            # XXX: Should this be a new error code?
            raise ProxyError(ERR_CONN_DROPPED)
        except socket.error, e:
            raise ProxyError(ERR_READ_TIMEOUT, str(e), data={"read_timeout": config.get_read_timeout()})
        
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

    def __init__(self, host, url):
        try:
            httplib.HTTPConnection.__init__(self, host)
        except httplib.InvalidURL, e:
            raise ProxyError(ERR_INVALID_URL, e)

        self.url = url
        self.response_class = lambda *a, **kw: ProxyHTTPResponse(self.url, *a, **kw)

    def connect(self):
        try:
            sock = socket.create_connection((self.host, self.port), config.get_connect_timeout())
            self.sock = SocketWrapper(sock, config.max_request_time, config.max_response_size)
        except socket.gaierror, e:
            # -3: Temporary failure in name resolution
            # Happens when DNS request is timeout
            if e.errno == -3:
                raise ProxyError(ERR_DNS_TIMEOUT, e, data={"dns_timeout": config.dns_timeout})
            else:
                raise ProxyError(ERR_INVALID_DOMAIN, e)
        except socket.timeout, e:
            raise ProxyError(ERR_CONN_TIMEOUT, e, data={"conn_timeout": config.get_connect_timeout()})
        except socket.error, e:
            msg = e.strerror or ""
            if e.errno == errno.ECONNREFUSED:
                raise ProxyError(ERR_CONN_REFUSED, e)
            else:
                raise ProxyError(ERR_CONN_MISC, e)

    def request(self, method, url, body=None, headers={}):
        try:
            httplib.HTTPConnection.request(self, method, url, body=body, headers=headers)
        except socket.error, e:
            raise ProxyError(ERR_CONN_MISC, e)
