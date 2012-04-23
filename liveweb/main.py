import os
import sys
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

from . import config 

# load config
if len(sys.argv) > 1:
    config.load(sys.argv[1])
    
# Make sure the storage_root directory exists
if not os.path.exists(config.storage_root):
    os.makedirs(config.storage_root)

from . import webapp
application = webapp.application
