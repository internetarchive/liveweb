import os
import sys
import logging

logging.basicConfig(level=logging.INFO, 
                    format="%(asctime)s %(threadName)18s %(levelname)5s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")

from . import config 

# load config
config.load()

# Make sure the storage directory exists
if not os.path.exists(config.output_directory):
    os.makedirs(config.output_directory)

from . import webapp

# Intialize
webapp.setup()

application = webapp.application

