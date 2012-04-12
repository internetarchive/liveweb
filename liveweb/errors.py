"""Exceptions raised by liveweb internals.
"""
class LivewebException(Exception): 
    pass

class BadURL(LivewebException): 
    """Raised if the given URL was malformed in some way.
    """
    pass

class ConnectionFailure(LivewebException, IOError):
    """Raised if a connection to the remote URL couldn't be established or was 
    interrupted.
    """
    pass
    
class TimeoutError(LivewebException, IOError):
    """Raised if when a connection is timedout.
    """
    pass
    
