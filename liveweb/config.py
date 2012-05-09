"""Liveweb configuration.

This is initialized by calling the load(configfile) function on startup.
"""
import yaml
import os
import logging

user_agent = "ia_archiver(OS-Wayback)"

M = 1024 * 1024

# Max size of ARC record that can be stored in cache
max_cacheable_size = 10 * M

# timeout in seconds
timeout = 60

dns_timeout = None
connect_timeout = None
initial_data_timeout = None
read_timeout = None

max_request_time = 60

max_response_size = 1024 * M

# can be either arc or warc
archive_format = "arc"

# When set to True, the http payload is served instead of arc/warc record
http_passthrough = False

cache = {"type": None}

# If no storage is specified store it in "records" directory in the $PWD
storage = {
    "directory": "records"
}

def get_connect_timeout():
    return connect_timeout or timeout

def get_initial_data_timeout():
    return initial_data_timeout or timeout

def get_read_timeout():
    return read_timeout or timeout

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
