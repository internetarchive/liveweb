"""
File pool implementation
"""

import datetime
import os
import Queue
import random
import threading

import logging
logging.basicConfig(level = logging.DEBUG)

class MemberFile(object):
    """
    """
    def __init__(self, name, pool, *largs, **kargs):
        self.fp = open(name, *largs, **kargs)
        self.pool = pool
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.pool.return_file(self)
    

    def __getattr__(self, attr):
        return getattr(self.fp, attr)
        
    

class FilePool(object):
    """
    Implements a pool of files from which a file can be requested.

    """
    def __init__(self, directory, pattern, max_files, max_file_size):
        """
        Creates a pool of files in the given directory with the
        specified pattern.

        The number of files is max_files and the maximum size of each
        file is max_file_size.

        The `get_file` method returns a new file from the pool

        """
        self.directory = directory
        self.pattern = pattern
        self.max_files = max_files
        self.max_file_size = max_file_size

        self.queue = Queue.Queue(self.max_files)

        self.seq = 0
        
        for i in range(self.max_files):
            self._add_file_to_pool()

    def _add_file_to_pool(self):
        "Creates a new file and puts it in the pool"
        pattern_dict = dict(timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%s%f"),
                            seq = "%05d"%self.seq)
        fname = self.pattern%pattern_dict
        absolute_name = os.path.join(self.directory, fname)
        logging.debug("Adding %s to pool",absolute_name)
        fp = MemberFile(absolute_name, self, mode = "ab")
        self.queue.put_nowait(fp)
        self.seq += 1
    
    def return_file(self, f):
        """Returns a file to the pool. Will discard the file and
        insert a new one if the file is above max_file_size."""
        logging.debug("Returning %s",f)
        file_size = f.tell()
        if file_size < self.max_file_size:
            logging.debug(" Put it back")
            self.queue.put(f)
        else:
            logging.debug(" Closing and creating a new file")
            f.close()
            self._add_file_to_pool()
        
    def get_file(self):
        f = self.queue.get()
        logging.debug("Getting %s",f)
        return f

    def close(self):
        logging.debug("Closing all descriptors. Emptying pool.")
        while not self.queue.empty():
            fp = self.queue.get_nowait()
            fp.close()
            
        
        
        
        
        


        
        
        

            
        
