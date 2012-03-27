"""The proxy functionality.
"""

def get(url):
    """Returns the content of the URL as an ARC record.
    
    If this URL was downloaded very recently, it returns the cached copy 
    instead of downloading again.
    """
    content = "helloworld\n"
    return content
    
def fetch(url):
    """Downloads the content of the URL from web and returns it as an ARC 
    record.
    """
    pass
