"""The proxy functionality.
"""

import datetime
import urllib

from warc import arc

def get(url):
    """Returns the content of the URL as an ARC record.
    
    If this URL was downloaded very recently, it returns the cached copy 
    instead of downloading again.
    """
    u = urllib.urlopen(url)
    status_line = "HTTP/1.1 200 OK\r\n"
    body = u.read()
    
    # urllib decodes the chunked transfer-encoded.
    # removing the header and adding content-length as a work-around.
    if 'transfer-encoding' in u.headers:
        del u.headers['transfer-encoding']
    u.headers['content-length'] = str(len(body))
    
    headers = str(u.headers)
    payload = status_line + headers + "\r\n" + body
    
    content_type = u.headers.get('content-type',"application/octet-stream").split(';')[0]

    headers = dict(url  = url,
                   ip_address = "127.0.0.1", #TODO : Fix this
                   date = datetime.datetime.utcnow(), 
                   content_type = content_type,
                   length = len(payload))
    return arc.ARCRecord(headers = headers, payload = payload)


    
def fetch(url):
    """Downloads the content of the URL from web and returns it as an ARC 
    record.
    """
    pass
