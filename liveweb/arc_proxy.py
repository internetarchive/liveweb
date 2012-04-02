"""The proxy functionality.
"""

import datetime
import fcntl
import gzip
import httplib
import os
import socket
import struct
import urllib
import urlparse


from warc import arc
from . import filetools

STORAGE_BASE = "/tmp/records"

url_cache = {}

class ArcProxyException(Exception): pass

class BadURL(ArcProxyException): 
    "Raised if the given URL was malformed in some way"
    pass

class ConnectionFailure(ArcProxyException, IOError):
    "Raised if a connection to the remote URL couldn't be established or was interrupted"
    pass


def get_ip_address(ifname):
    """Return the IP address of the requested interface.
    This was obtained from 

    http://code.activestate.com/recipes/439094-get-the-ip-address-associated-with-a-network-inter/
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

def get_storage_location(url):
    """This function is to be used to spread the record writes across
    multiple disks. """
    
    # For the time being, just return the storage_base
    return STORAGE_BASE


def write_arc_file(url, arc_record):
    location = get_storage_location(url)
    # TODO: Need to understand what this format is.
    # alexa-web-20110904174118-00038/51_23_20110804161301_crawl103.arc.gz
    now = datetime.datetime.now()
    arc_file_name = location + "/liveweb-%s.arc.gz"%now.strftime("%Y%m%d%H%M%S")
    
    outfile = gzip.GzipFile(arc_file_name + ".tmp", "wb")
    arc_record.write_to(outfile)
    outfile.close()
    os.rename(arc_file_name + ".tmp", arc_file_name)
    
    file_size = os.stat(arc_file_name).st_size

    return file_size, arc_file_name


def decompose_url(url):
    """
    Breaks URL into server:port and the requested resource

    """
    scheme, netloc, path, query, fragment, = urlparse.urlsplit(url)
    resource = urlparse.urlunsplit(["","", path, query, fragment]) #TODO: This might alter the URL
    return netloc, resource

def retrieve_url(url):
    """
    Fetches the given url using an HTTP GET and returns the complete
    HTTP transaction.

    This uses thes spyfile class to get the actual transaction without
    any modifications made by by httplib.

    Returns the HTTPResponse Object and the actual data sent back on the line. 

    """
    server, resource = decompose_url(url)

    try:
        conn = httplib.HTTPConnection(server)
    except httplib.InvalidURL:
        raise BadURL("'%s' is an invalid URL", url)

    conn.response_class = filetools.SpyHTTPResponse
    try:
        conn.request("GET", resource)
    except socket.gaierror:
        raise

    response = conn.getresponse()
    fp = response.fp
    response.read() 
    line_data = fp.buf.getvalue() # TODO: Stream this data back instead of this one shot read.
    
    return response, line_data

def get(url):
    """Returns the content of the URL as an ARC record.
    
    If this URL was downloaded very recently, it returns the cached copy 
    instead of downloading again.

    This is the only public API.
    """
    global url_cache

    if url in url_cache:
        size, arc_file_name = url_cache[url]
    else:
        size, arc_file_name = live_fetch(url)
        url_cache[url] = (size, arc_file_name)

    return (size, open(arc_file_name, "rb"))
    
def live_fetch(url):
    """Downloads the content of the URL from web and returns it as an ARC 
    record.
    """
    http_response, payload = retrieve_url(url)
    headers = http_response.getheaders()
    content_type = http_response.getheader('content-type',"application/octet-stream").split(';')[0]

    headers = dict(url  = url,
                   ip_address = get_ip_address("lo"), #TODO: Use eth0 but select dynamically.
                   date = datetime.datetime.utcnow(),
                   content_type = content_type,
                   length = len(payload)
                   )
    arc_record = arc.ARCRecord(headers = headers, payload = payload)

    size, file_name = write_arc_file(url, arc_record)
    return size, file_name

