import sys
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

from . import config 
from . import webapp

if len(sys.argv) > 1:
    config.load(sys.argv[1])

application = webapp.application
