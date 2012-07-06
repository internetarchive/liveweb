import os
import sys
import logging

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(threadName)18s %(levelname)5s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")

logging.info("starting liveweb-proxy")

from . import config

# load config
config.load()

# Make sure the storage directory exists
partial_dir = os.path.join(config.output_directory, 'partial')
complete_dir = os.path.join(config.output_directory, 'complete')
if not os.path.exists(partial_dir):
    os.makedirs(partial_dir)
if not os.path.exists(complete_dir):
    os.makedirs(complete_dir)

from . import webapp

# Intialize
webapp.setup()

application = webapp.application
