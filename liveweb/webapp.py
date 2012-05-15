"""The webapp for arc proxy.
"""

from cStringIO import StringIO
import gzip
import logging
import socket
import datetime

from warc.arc import ARCRecord, ARCFile

from . import proxy
from . import errors
from . import config
from . import file_pool
from . import cache

pool = None
_cache = None

def init_arc_file(fileobj):
    """Writes the ARC file headers when a new file is created.
    """
    zfileobj = gzip.GzipFile(fileobj=fileobj, filename=None, mode="w")

    headers = {}
    headers['date'] = datetime.datetime.utcnow()
    headers['ip_address'] = socket.gethostbyname(socket.gethostname())
    headers['org'] = "InternetArchive"

    afile = ARCFile(fileobj=zfileobj, filename=fileobj.name, mode='wb', version=1, file_headers=headers)
    afile._write_header()
    afile.close()
    fileobj.flush()

def setup():
    """This is called from main to initialize the requires globals.
    """
    global pool, _cache

    # Write ARC file header if the archive format is "arc"
    if config.archive_format == "arc":
        init_file = init_arc_file
    else:
        init_file = None

    pool = file_pool.FilePool(config.output_directory,
                              pattern=config.filename_pattern,
                              max_files=config.num_writers,
                              max_file_size=config.filesize_limit,
                              init_file_func=init_file)
    _cache = cache.create(type=config.cache, config=config)

class application:
    """WSGI application for liveweb proxy.
    """
    def __init__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response
        
    def parse_request(self):
        self.method = self.environ['REQUEST_METHOD']
        if 'REQUEST_URI' in self.environ: # This is for uwsgi
            self.url = self.environ['REQUEST_URI'] #TODO: Is this a valid environment variable always?
        if 'RAW_URI' in self.environ: # This is for gunicorn
            self.url = self.environ['RAW_URI'] #TODO: Is this a valid environment variable always?

        # Allow accessing the proxy using regular URL so that we can use
        # tools like ab.
        if self.url.startswith("/_web/"):
            self.url = self.url[len("/_web/"):]
            
        # Since this is a proxy, the URL is always of the form http://hostname/path
        # nginx is stripping the http://host from the passed URL and just passing the /path here.
        # This is a work-around for that issue.
        if self.url.startswith("/"):
            self.url = "http://" + self.environ['HTTP_HOST'] + self.url
        
    def __iter__(self):
        response = None
        try:
            self.parse_request()

            record = self.get_record()
            if config.http_passthrough:
                return self.proxy_response(record)
            else:
                return self.success(record.content_length, record.content_iter)
        except:
            logging.error("Internal Error - %s", self.url, exc_info=True)
            return self.error("500 Internal Server Error")
        finally:
            if response:
                # XXX-Anand: response.cleanup will unlink the temp file, # 
                # which'll will be in use when we are in http_passthrough mode. 
                # The file will be removed when the reference to the file object 
                # is gone. 
                # This may create trouble on windoz.
                response.cleanup()

    def get_record(self):
        """Fetches the Record object from cache or constructs from web.
        """
        record = _cache.get(self.url)
        if record is None:
            http_response = proxy.urlopen(self.url)
            record = http_response.write_arc(pool)
            _cache.set(self.url, record)
        return record

    def proxy_response(self, record):
        """Send the response data as it is """
        # TODO: This is very inefficient. Improve.

        # Now we only have the ARC record data. 
        record_payload = record.read_all()
        record_payload = gzip.GzipFile(fileobj=StringIO(record_payload)).read()        
        arc = ARCRecord.from_string(record_payload, version=1)

        # Create a FakeSocket and read HTTP headers and payload.
        sock = proxy._FakeSocket(StringIO(arc.payload))
        response = proxy.ProxyHTTPResponse(self.url, sock)
        response.begin()

        status = "%d %s" % (response.status, response.reason)
        headers = response.getheaders()
        self.start_response(status, headers)
        return response.get_payload()
    
    def success(self, clen, data):
        status = '200 OK'
        response_headers = [
            ('Content-type', 'application/x-arc-record'),
            ('Content-Length', str(clen))
        ]
        self.start_response(status, response_headers)
        return iter(data)
        
    def error(self, status, headers=None):
        if headers is None:
            headers = [
                ('Content-Type', 'text/plain'),
                ('Content-Length', '0'),
            ]
        self.start_response(status, headers)
        return iter([])
