"""The proxy functionality.
"""

import datetime
import fcntl
import gzip
import httplib
import logging
import os
import random
import socket
import struct
import urllib
import urlparse
import random
import string
from cStringIO import StringIO

import redis

from warc import arc
from . import filetools
from .errors import BadURL, ConnectionFailure
from . import config


def get_storage_location(url):
    """This function is to be used to spread the record writes across
    multiple disks. """
    
    # For the time being, just return the storage_base
    return config.storage_root
    
def random_string(length):
    return "".join(random.choice(string.letters) for i in range(length))

def get_arc_file_name(url):
    location = get_storage_location(url)
    now = datetime.datetime.now()

    arc_file_name = location + "/liveweb-%s-%s.arc.gz" % (now.strftime("%Y%m%d%H%M%S"), random_string(5))

    return arc_file_name

def write_arc_file(arc_file_name, arc_record):
    # TODO: Need to understand what this format is.
    # alexa-web-20110904174118-00038/51_23_20110804161301_crawl103.arc.gz

    fp = open(arc_file_name + ".tmp", "wb")
    outfile = gzip.GzipFile(filename = "", fileobj = fp)
    arc_record.write_to(outfile)
    outfile.close()
    fp.close()
    os.rename(arc_file_name + ".tmp", arc_file_name)
    
    file_size = os.stat(arc_file_name).st_size

    return file_size


def decompose_url(url):
    """
    Breaks URL into server:port and the requested resource

    TODO: This logic might belong in the web app rather than the
    TODO: arc_proxy module. It'll have to be done for WARCs too.
    """

    scheme, netloc, path, query, fragment, = urlparse.urlsplit(url)
    if not netloc: # This will happen if there are issues with URLs like www.google.com
        scheme, netloc, path, query, fragment, = urlparse.urlsplit("http://"+url)
        
    resource = urlparse.urlunsplit(["","", path, query, fragment]) #TODO: This might alter the URL
    logging.debug("Scheme : %s\nNetloc : %s\nPath : %s\nQuery : %s\nFragment : %s\n", scheme, netloc, path, query, fragment)
    logging.debug("Recomposed resource is '%s'", resource)
    if not resource:
        logging.debug("Resource string is empty. Changing it to /")
        resource = "/"
    return netloc, resource

def establish_connection(url):
    """
    Establishes an HTTP connection to the given URL and returns the
    HTTPResponse Object.

    This uses thes spyfile class to get the actual transaction without
    any modifications made by by httplib.

    """
    server, resource = decompose_url(url)
    logging.debug("Attempting to fetch '%s' from '%s'", resource, server)

    try:
        conn = httplib.HTTPConnection(server)
    except httplib.InvalidURL:
        raise BadURL("'%s' is an invalid URL", url)

    conn.response_class = filetools.SpyHTTPResponse
    headers = {
        "User-Agent": config.user_agent
    }
    try:
        conn.request("GET", resource, headers=headers)
    except socket.gaierror:
        raise ConnectionFailure()

    return conn

def get(url):
    """Returns the content of the URL as an ARC record.
    
    If this URL was downloaded very recently, it returns the cached copy 
    instead of downloading again.

    This is the only public API.
    """
    cache = config.get_redis_client()
    
    # when redis is disabled
    if cache is None:
        return live_fetch(url)
    
    content = cache.get(url)
    if content is None:
        logging.info("cache miss: %s", url)
        size, arc_file_handle = live_fetch(url)
        
        # too big to cache, just return the file from disk
        if size > config.max_cacheable_size:
            logging.info("too large to cache: %d", size)
            return size, arc_file_handle
        
        content = arc_file_handle.read()
        cache.setex(url, config.expire_time, content)
    else:
        logging.info("cache hit: %s", url)
        # Reset the expire time on read
        # TODO: don't update expire time if the record is more than 1 day old
        cache.expire(url, config.expire_time)
        
    return len(content), [content]

def live_fetch(url):
    """Downloads the content of the URL from web and returns it as an ARC 
    record.

    This will attempt to donwload the file into memory and write it to
    disk. 

    However, if it finds that the file is larger than 10MB, it will
    resort to streaming the data straight onto disk in a temporary
    file and then process the arc file at the end. This will require
    double the I/O but will be sufficiently rare to justify this
    approach.
    
    Cf. http://www.optimizationweek.com/reviews/average-web-page/


    """
    initial_chunk_size = 10 * 1024 * 1024 # 10 MB

    try:
        conn = establish_connection(url)
        remote_ip = conn.sock.getpeername()[0]        
        response = conn.getresponse()
        spyfile = response.fp
        response.read(initial_chunk_size)
        content_type = response.getheader("content-type","application/octet-stream")
    except ConnectionFailure:
        # Match the response of liveweb 1.0
        payload = "HTTP 502 Bad Gateway\n\n"
        content_type = "unk"
        remote_ip = "0.0.0.0"
        spyfile = filetools.SpyFile(StringIO(payload))
        spyfile.read()

    initial_data = spyfile.buf.getvalue()
    data_length = len(initial_data)

    arc_file_name = get_arc_file_name(url)

    if data_length < initial_chunk_size: # We've read out the whole data
        # Create regular arc file here
        arc_record = arc.ARCRecord(headers = dict(url = url,
                                                  date = datetime.datetime.utcnow(),
                                                  content_type = content_type,
                                                  ip_address = remote_ip,
                                                  length = data_length),
                                   payload = initial_data,
                                   version = 1)

        size = write_arc_file(arc_file_name, arc_record)
        # This is an optimisation to return the in memory payload so
        # that we don't have to read it off the disk again.  This
        # takes the arc_record we've created, writes it to a StringIO
        # (compressed_stream) via a GzipFile so that it's compressed
        # and then returns a handle to compressed_stream.
        spyfile.buf.seek(0)
        compressed_stream = StringIO()

        compressed_file = gzip.GzipFile(fileobj = compressed_stream, mode = "w")
        arc_record.write_to(compressed_file)
        compressed_file.close()

        compressed_stream.seek(0)
        arc_file_handle = compressed_stream
    else:
        # TODO: This block probably needs to be moved off to multiple functions
        payload_file_name = arc_file_name + ".tmp.payload"
        payload_file = open(payload_file_name, "wb")
        
        data_length = response.getheader("content-length","XXX") # We won't have the size for streaming data.

        # First write out the header (as much we have anyway)
        arc_header = arc.ARCHeader(url = url,
                                   date = datetime.datetime.utcnow(),
                                   content_type = content_type,
                                   ip_address = remote_ip,
                                   length = data_length)
        
        # Now deal with the payload
        # Now first write the payload which we've already read into the file.
        payload_file.write(initial_data)
        # Then stream in the rest of the payload by changing the spy file
        spyfile.change_spy(payload_file)
        response.read()
        payload_file.close()

        payload_size = os.stat(payload_file_name).st_size

        # Fix the content-length in the header if necessary
        if arc_header['length'] == "XXX":
            arc_header['length'] = payload_size

        # Create the actual file
        f = open(arc_file_name + ".tmp", "wb")
        arc_file = gzip.GzipFile(filename = "" , fileobj = f)
        payload = open(payload_file_name, "rb") #Reopen for read
        # TODO: Write one file into another?
        arc_record = arc.ARCRecord(header = arc_header, payload = payload, version = 1) 
        arc_record.write_to(arc_file)
        arc_file.close()

        os.unlink(payload_file_name)
        os.rename(arc_file_name + ".tmp", arc_file_name)
        
        size = os.stat(arc_file_name).st_size
        arc_file_handle = open(arc_file_name, "rb")
        
    return size, arc_file_handle
