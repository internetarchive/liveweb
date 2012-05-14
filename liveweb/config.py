"""Liveweb configuration.

This is initialized by calling the load(configfile) function on startup.
"""
import yaml
import os
import logging
from ConfigParser import ConfigParser

from .cli import make_config

# The config options and default values are specified in make_config function in cli.py

def init_defaults():
    global _config
    _config = make_config()
    gloabsl().update(_config.dict())

def load():
    """Loads the configuration from environment, config file and command-line arguments.
    """
    global _config
    _config = make_config()
    _config.load()
    globals().update(_config.dict())

extra_headers = {}

def get_connect_timeout():
    return connect_timeout or default_timeout

def get_initial_data_timeout():
    return initial_data_timeout or default_timeout

def get_read_timeout():
    return read_timeout or default_timeout

# handy function to check for existance of a config parameter
get = globals().get
