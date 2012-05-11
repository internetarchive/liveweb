"""Liveweb configuration.

This is initialized by calling the load(configfile) function on startup.
"""
import yaml
import os
import logging
from ConfigParser import ConfigParser

class ConfigItem:
    def __init__(self, name, type="string", default=None, choices=None):
        self.name = name
        self.type = type
        self.default = default
        self.choices = choices
        
        self.set(self.default)

    @property
    def optname(self):
        return self.name.replace("_", "-")

    @property
    def envname(self):
        """Name of the enviroment variable to specify this.
        """
        return "LIVEWEB_" + self.name.upper()

    def set(self, value):
        if value is None:
            self.value = None
        else:
            self.value = self.parse(value)

    def parse(self, value):
        m = getattr(self, "parse_" + self.type)
        return m(value)

    parse_int = int
    parse_string = str

    def parse_boolean(self, strvalue):
        return strvalue.lower() in ["true", "1"]

    def parse_choice(self, strvalue):
        if strvalue not in self.choices:
            raise ValueError("%s=%r is not a valid choice. Available choices are %s" % (self.name, strvalue, self.choices))
        return strvalue

    def parse_time(self, strvalue):
        """Parses time specified in seconds, minutes and hours into seconds.

        Time is specifed in seconds, minutes and hours using suffix s,
        m and h respectively. This method parses that info and
        converts that with appropriate multipler to convert into
        seconds.
        """
        strvalue = strvalue.replace(" ", "")
        scales = {
            's': 1,
            'm': 60,
            'h': 3600
        }

        if strvalue[-1] in scales.keys():
            scale = scales[strvalue[-1]]
            strvalue = strvalue[:-1]
        else:
            scale = 1

        t = float(strvalue) * scale
        return t

    def parse_bytes(self, strvalue):
        """Parses the bytes specified as KB, MB and GB into number.
        """
        strvalue = strvalue.replace(" ", "")
        scales = {
            "KB": 1024,
            "MB": 1024**2,
            "GB": 1024**3
        }
        if strvalue[-2:] in scales:
            scale = scales[strvalue[-2:]]
            strvalue = strvalue[:-2]
        else:
            scale = 1
        size = int(strvalue) * scale
        return size

    def load_from_env(self, env=None):
        if env is None:
            env = os.environ
        if self.envname in env:
            self.set(env[self.envname])

    def putenv(self):
        if self.value != self.default:
            os.putenv(self.envname, c.value)

class Config:
    def __init__(self, config_values):
        self.config_values = config_values

    def dict(self):
        return dict((c.name, c.value) for c in self.config_values)

    def load_from_env(self, env=None):
        for c in self.config_values:
            c.load_from_env(env)

    def load_from_ini(self, filename):
        p = ConfigParser()
        p.read(filename)

        for c in self.config_values:
            if p.has_option("liveweb", c.name):
                c.set(p.get("liveweb", c.name, raw=True))

    def update_globals(self):
        globals().update(self.dict())

    def putenv(self):
        for c in self.config_values:
            c.putenv()

_config = Config([
    ConfigItem("user_agent", type="string", default="ia_archiver(OS-Wayback)"),
    ConfigItem("default_timeout", type="time", default="10s"),
    ConfigItem("connect_timeout", type="time"),
    ConfigItem("initial_data_timeout", type="time"),
    ConfigItem("read_timeout", type="time"),

    ConfigItem("max_request_time", type="time", default="5m"),
    ConfigItem("max_response_size", type="bytes", default="100MB"),
    
    ConfigItem("archive_format", type="choice", choices=["none", "arc", "warc"], default="arc"),

    # When set to True, the http payload is served instead of arc/warc record
    ConfigItem("http_passthrough", type="boolean", default="false"),

    ConfigItem("cache", type="choice", choices=["none", "redis", "sqlite"], default="none"),

    ConfigItem("redis_host", type="string", default="localhost"),
    ConfigItem("redis_port", type="int", default="6379"),
    ConfigItem("redis_db", type="int", default="0"),
    ConfigItem("redis_expire_time", type="time", default="1h"),
    ConfigItem("redis_max_record_size", type="bytes", default="100KB"),

    ConfigItem("output_directory", type="string", default="records"),
    ConfigItem("filename_pattern", type="string", default="live-%(timestamp)s-%(serial)05d.arc.gz"),
    ConfigItem("num_writers", type="int", default="1"),
    ConfigItem("filesize_limit", type="bytes", default="100MB"),
])

# Add the default values to this module globals
_config.update_globals()

extra_headers = {}

def get_connect_timeout():
    return connect_timeout or default_timeout

def get_initial_data_timeout():
    return initial_data_timeout or default_timeout

def get_read_timeout():
    return read_timeout or default_timeout

def load_from_ini(filename):
    _config.load_from_ini(filename)
    _config.update_globals()

def load_from_env():
    _config.load_from_env()
    _config.update_globals()

# handy function to check for existance of a config parameter
get = globals().get
