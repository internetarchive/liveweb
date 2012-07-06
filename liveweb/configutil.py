"""Utility to work with configuration.

The configuration can be changed in many different ways. The configuration sources in the order of priority are:

* The command-line arguments
* The config file
* The environment variables

The optparse module alone is not sufficient to handle this. If the
OptionParser is used with default values, there is no way to know if
the option is specified as command line argument or it is a default
value.

Also, we need a way to specify time in seconds/minutes/hours and bytes
in KB/MB/GB. These formats should work for all the 3 sources.

This module provides a framework to address these issues.
"""
import os
import sys
import logging
from ConfigParser import ConfigParser
import optparse

class Config:
    """Entry point to configuration.

    This provides way to set the configuration using environment
    variables, config file and command line parameters.

    The configuration is made of many ConfigOptions. Each ConfigOption
    accounts for one environment variable, one setting in the config
    file and one command line variable.

    This class provides tools to read/set environment variable, load
    config file and create OptionParser to parse the command-line
    arguments.
    """
    def __init__(self, name):
        self.name = name
        self.config_options = []

    def add_option(self, *args, **kwargs):
        """Creates a new ConfigOption created using the specified arguments and adds it to this Config.
        """
        option = ConfigOption(*args, **kwargs)
        self.config_options.append(option)

    def get(self, name):
        return self.dict().get(name)

    def dict(self, dirty=None):
        """Returns values of all the config options as a dict.

        If dirty=True is specified, only the values of the modified options are returned.
        """
        return dict((c.name, c.value) for c in self.config_options 
                    if dirty is None or c.dirty==dirty)

    def putenv(self):
        """Updates this process env with environment variables
        indicating current configuration.

        Useful to set config values before exec'ing a new process.
        """
        for c in self.config_options:
            c.putenv()

    def load(self, env=None, args=None):
        """Loads the configuration from environment, config-file and command-line arguments.
        """
        self.load_from_env(env)

        p = self.create_optparse_parser()
        options, args2 = p.parse_args(args)

        # take config file from command-line or env
        # TODO: support an option to provide an alternative name for "config"
        config_file = getattr(options, "config", None) or self.get("config")
        if config_file:
            self.load_from_ini(config_file)

        self.load_from_optparse_options(options)

    def load_from_env(self, env=None):
        """Loads the configuration from environment.
        """
        for c in self.config_options:
            c.load_from_env(env)

    def load_from_ini(self, filename):
        """Loads the configuration from a config file.
        """
        p = ConfigParser()
        p.read(filename)

        for c in self.config_options:
            # using name as used in command line options in the config file
            name = c.name.replace("_", "-")
            if p.has_option(self.name, name):
                c.set(p.get(self.name, name, raw=True))

    def create_optparse_parser(self):
        p = optparse.OptionParser(self.name)
        for c in self.config_options:
            p.add_option(c.option)
        return p

    def load_from_optparse_options(self, options):
        options = options.__dict__
        for c in self.config_options:
            if options.get(c.name) is not None:
                c.set(options[c.name])

class ConfigOption:
    """Represents one entry in the Configuration.

    This corresponds to one environment variable, one config setting and one command line option.
    """
    def __init__(self, *opts, **kw):
        self.type = kw.pop("type", "string")
        self.default = kw.pop("default", None)
        self.help = kw.pop("help", None)
        
        help = self.help and self.help.replace("%default", str(self.default))

        if self.type == "bool":
            self.option = _Option(*opts, action="store_true", help=help, **kw)
        else:
            type = self.type
            self.option = _Option(*opts, type=type, help=help, **kw)
        
        self.name = self.option.dest
        self.kw = kw
        
        self.set(self.default)

    @property
    def dest(self):
        return self.option.dest

    @property
    def optname(self):
        return self.name.replace("_", "-")

    @property
    def envname(self):
        """Name of the enviroment variable to specify this.
        """
        return "LIVEWEB_" + self.name.upper()

    @property
    def dirty(self):
        """True if the value of this item is modified."""
        return self.strvalue != self.default

    def set(self, value):
        if value is None:
            self.value = None
            self.strvalue = value
        else:
            self.strvalue = str(value)
            self.value = self.parse(value)

    def parse(self, value):
        if self.type == "bool":
            return self.parse_boolean(value)
        else:
            return self.option.convert_value("--" + self.optname, str(value))

    def parse_boolean(self, strvalue):
        return str(strvalue).lower() in ["true", "1"]

    def load_from_env(self, env=None):
        if env is None:
            env = os.environ
        if self.envname in env:
            self.set(env[self.envname])

    def putenv(self):
        if self.dirty or self.envname in os.environ:
            os.putenv(self.envname, self.strvalue)

    def add_option(self, option_parser):
        option_parser.add_option("--" + self.optname, help=self.help, **kw)

def parse_time(strvalue):
    """Parses time specified in seconds, minutes and hours into seconds.
    
    Time is specifed in seconds, minutes and hours using suffix s, m
    and h respectively. This method parses that info and converts that
    with appropriate multipler to convert into seconds.
    """
    if not isinstance(strvalue, basestring):
        return strvalue

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
    
def parse_bytes(strvalue):
    """Parses the bytes specified as KB, MB and GB into number.
    """
    if not isinstance(strvalue, basestring):
        return strvalue

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

def wrap_checker(f):
    def g(option, opt, value):
        try:
            return f(value)
        except ValueError:
            what = option.type
            raise optparse.OptionValueError(
                "option %s: invalid %s value: %r" % (opt, what, value))
    return g

class _Option(optparse.Option):
    """Customized Option class to support time and bytes types.
    """
    TYPES = optparse.Option.TYPES + ("time", "bytes")
    TYPE_CHECKER = dict(optparse.Option.TYPE_CHECKER,
                        bytes=wrap_checker(parse_bytes),
                        time=wrap_checker(parse_time))

