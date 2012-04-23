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
        self.expire_time = params.pop('expire_time', 3600) # default timeout
        self.redis_client = redis.StrictRedis(**params)

    def get(self, url):
        data = self.redis_client.get(url)
        if data is not None:
            return Record(filename=None,
                          offset=0, 
                          content_length=len(data),
                          content_iter=iter([data]))

    def set(self, url, record):
        """Puts a new entry in the cache.

        :param url: URL for which the response is being cached
        :param record: record to be cached
        """
        maxsize = 1024 * 100
        if record.content_length <= maxsize:
            data = record.read_all()
            self.redis_client.setex(url, self.expire_time, data)

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

    def __init__(self, db):
        self.dbname = db
        self.create_table()

    def create_table(self):
        if "cache" not in self._get_tables():
            self.query(self.SCHEMA)

    def _get_tables(self):
        q = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        tables = [row[0] for row in self.query(q)]
        return tables

    def query(self, query, args=[], commit=False):
        logging.info("query: %r - %r", query, args)
        conn = sqlite3.connect(self.dbname)
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
            logging.info("cache hit")
            filepath, offset, content_length = rows[0]
            return Record(filepath, offset=offset, content_length=content_length)
        else:
            logging.info("cache miss")

    def set(self, url, record):
        self.query("INSERT INTO cache (url, filename, offset, clen) VALUES (?, ?, ?, ?)", 
                   [url, record.filename, record.offset, record.content_length],
                   commit=True)

class NoCache:
    def get(self, url):
        return None

    def set(self, url, record):
        pass

cache_types = {
    "redis": RedisCache,
    "sqlite": SqliteCache,
    None: NoCache
}

def create(type, **params):
    logging.info("creating cache %s %s", type, params)
    klass = cache_types[type]
    return klass(**params)
