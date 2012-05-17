"""
File pool implementation
"""

import datetime
import os
import Queue
import random
import threading
import socket
import itertools

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
    def __init__(self, directory, pattern="liveweb-%(timestamp)s-%(serial)05d.arc.gz", max_files=1, max_file_size=100*1024*1024, init_file_func=None):
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
        self.init_file_func = init_file_func

        self.queue = Queue.Queue(self.max_files)

        self.seq_counter = itertools.count()

        # vars required to substitue filename pattern.
        self._port = os.getenv("LIVEWEB_PORT", "0")
        self._host = socket.gethostname()
        self._pid = os.getpid()

        # Adding None to queue indicating that new file needs to be created
        for i in range(self.max_files):
            self.queue.put(None)

    def set_sequence(self, counter):
        """Sets the sequence counter used to generate filename.

        Used to set a distrbuted persistent counter using redis/database.

        :param counter: An iterable counter
        """
        self.seq_counter = counter

    def _new_file(self):
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        pattern_dict = dict(
            timestamp=timestamp,
            timestamp20=timestamp,
            timestamp17=timestamp[:17],
            timestamp14=timestamp[:14],
            serial=self.seq_counter.next(),
            port=self._port,
            host=self._host,
            fqdn=self._host,
            pid=self._pid)

        fname = self.pattern%pattern_dict
        partial_dir = os.path.join(self.directory, 'partial')
        absolute_name = os.path.join(partial_dir, fname)

        logging.info("Creating new file %s", absolute_name)

        fp = MemberFile(absolute_name, self, mode = "ab")
        # Initialize the file object like writing file headers etc.
        if self.init_file_func:
            self.init_file_func(fp)
        return fp

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
            complete_dir = os.path.join(self.directory, 'complete')
            basename = os.path.basename(f.name)
            complete_name = os.path.join(complete_dir, basename)
            os.rename(f.name, complete_name)
            self.queue.put(None)

    def get_file(self):
        f = self.queue.get()
        # f is None when new file needs to be created
        if f is None:
            f = self._new_file()
        logging.debug("Getting %s",f)
        return f

    def close(self):
        logging.debug("Closing all descriptors. Emptying pool.")
        while not self.queue.empty():
            fp = self.queue.get_nowait()
            if fp:
                fp.close()
