"""Liveweb configuration.

This is initialized by calling the load(configfile) function on startup.
"""
import yaml
import os
import redis
import logging

storage_root = "/tmp/records"
user_agent = "ia_archiver(OS-Wayback)"

M = 1024 * 1024

# Max size of ARC record that can be stored in cache
max_cacheable_size = 10 * M

# timeout in seconds
timeout = 60

expire_time = 3600

redis_params = None

_redis_client = None

def get_redis_client():
    """Returns the redis client instance created from the config.
    """
    # TODO: this is not right place to have this function. Move it to some better place.
    global _redis_client
    if _redis_client is None and redis_params is not None:
        _redis_client = redis.StrictRedis(**redis_params)
    return _redis_client

def _parse_size(size):
    size = str(size).upper().replace(" ", "")

    if size.endswith("GB"):
        return int(size[:-2]) * (1024 ** 3)
    elif size.endswith("MB"):
        return int(size[:-2]) * (1024 ** 2)
    elif size.endswith("KB"):
        return int(size[:-2]) * (1024 ** 1)
    else:
        return int(size)
        
def load(filename):
    """Loads configuration from specified config file.
    """
    logging.info("Loading config file: %s", filename)
    if not os.path.exists(filename):
        logging.warn("config file not found: %s, ignoring...", filename)
        return
        
    d = yaml.safe_load(open(filename))
    
    if "max_cacheable_size" in d:
        d['max_cacheable_size'] = _parse_size(d['max_cacheable_size'])

    # update config
    globals().update(d)
    
# handy function to check for existance of a config parameter
get = globals().get
