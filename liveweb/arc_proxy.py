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
    headers = str(u.headers)
    body = u.read()
    payload = headers + body

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
