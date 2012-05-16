"""Cache for liveweb.
"""

from collections import namedtuple
import logging
import sqlite3

import redis

from .proxy import Record

class RedisCache:
    """Cache based on Redis.

    This caches the whole arc record.
    """
    def __init__(self, **params):
        """Creates a new instance of redis client.

        :param host: host to connect, defaults to "localhost"
        :param port: port to connect, defaults to 6379, the default redis server port
        :param db: db number, defaults to 0
        :param expire_time: amount of time in seconds after which the entry in the cache should expire, defaults to one hour.
        """
        self.expire_time = int(params.pop('expire_time', 3600)) # default timeout

        # max size of record that can be cached. Defaults to 100K.
        self.max_record_size = params.pop('max_record_size', 100*1024)

        self.redis_client = redis.StrictRedis(**params)

    def get(self, url):
        data = self.redis_client.get(url)
        if data is not None:
            logging.info("cache hit - %s", url)
            return Record(filename=None,
                          offset=0, 
                          content_length=len(data),
                          content_iter=iter([data]))

    def set(self, url, record):
        """Puts a new entry in the cache.

        :param url: URL for which the response is being cached
        :param record: record to be cached
        """
        if record.content_length <= self.max_record_size:
            data = record.read_all()
            self.redis_client.setex(url, self.expire_time, data)

    def next(self):
        """Returns the next-value of the counter.
        Used by file_pool to get next sequence.
        """
        return self.redis_client.incr("filename-sequence")

class SqliteCache:
    """Cache implementation based on sqlite.

    This stores url, filepath, offset and content_length in the
    database. Useful when running in http-passthough mode with
    browser.
    """
    SCHEMA = ("" + 
              "CREATE TABLE cache (" +
              "    url text unique," + 
              "    filename text unique," +
              "    offset int," + 
              "    clen int" +
              ")")

    def __init__(self, database):
        self.database = database
        self.create_table()

    def create_table(self):
        if "cache" not in self._get_tables():
            self.query(self.SCHEMA)

    def _get_tables(self):
        q = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        tables = [row[0] for row in self.query(q)]
        return tables

    def query(self, query, args=[], commit=False):
        logging.debug("query: %r - %r", query, args)
        conn = sqlite3.connect(self.database)
        cursor = conn.execute(query, args)
        rows = cursor.fetchall()
        if commit:
            conn.commit()
        cursor.close()
        conn.close()
        return rows
        
    def get(self, url):
        rows = self.query("SELECT filename, offset, clen FROM cache WHERE url=?", [url])
        if rows:
            logging.info("cache hit - %s", url)
            filepath, offset, content_length = rows[0]
            return Record(filepath, offset=offset, content_length=content_length)
        else:
            logging.info("cache miss - %s", url)

    def set(self, url, record):
        self.query("INSERT INTO cache (url, filename, offset, clen) VALUES (?, ?, ?, ?)", 
                   [url, record.filename, record.offset, record.content_length],
                   commit=True)

class NoCache:
    def get(self, url):
        return None

    def set(self, url, record):
        pass

def create(type, config):
    logging.info("creating cache %s", type)

    if type == 'redis':
        return RedisCache(host=config.redis_host, 
                          port=config.redis_port, 
                          db=config.redis_db, 
                          expire_time=config.redis_expire_time, 
                          max_record_size=config.redis_max_record_size)
    elif type == 'sqlite':
        return SqliteCache(config.sqlite_db)
    elif type == 'none' or type == None:
        return NoCache()
    else:
        raise ValueError("Unknown cache type %r" % type)
