"""The webapp for arc proxy.
"""

from cStringIO import StringIO
import gzip
import logging

from . import proxy
from . import errors
from . import config
from . import file_pool
from . import cache


# File pool to store arc files
pool = file_pool.FilePool(**config.storage)

_cache = cache.create(**config.cache)

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
            
    def _get(self, url):
        response = proxy.get(url)
        response = arc_writer(response)
        return response
        
    def get(self, url):
        response = self.cache.get(url)
        if not response:
            response = self._get(url)
            self.cache.set(url, response)
        return response
    
    def __iter__(self):
        response = None
        try:
            self.parse_request()

            record = _cache.get(self.url)
            if record is None:
                response = proxy.urlopen(self.url)
                record = response.write_arc(pool)
                _cache.set(self.url, record)

            # XXX-Anand: http_passthrough doesn't work on cache hit
            if config.http_passthrough:
                return self.proxy_response(response)
            else:
                return self.success(record.content_length, record.content_iter)
        except errors.BadURL:
            logging.error("bad url %r", self.url)
            return self.error("400 Bad Request")
        except errors.ConnectionFailure:
            logging.error("Connection failure", exc_info=True)
            return self.error("502 Bad Gateway")
        except:
            logging.error("Internal Error", exc_info=True)
            return self.error("500 Internal Server Error")
        finally:
            if response:
                # XXX-Anand: response.cleanup will unlink the temp file, # 
                # which'll will be in use when we are in http_passthrough mode. 
                # The file will be removed when the reference to the file object 
                # is gone. 
                # This may create trouble on windoz.
                response.cleanup()
            
    def proxy_response(self, response):
        """Send the response data as it is """
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
