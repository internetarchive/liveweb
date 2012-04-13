    
PROJECT_NAME=$(shell basename $(PWD))

# If VENV_ROOT is defined in the environment, use it to find the VENV
# directory, else consider the current dir as the venv dir.
VENV_ROOT ?= $(shell dirname $(PWD))


# Use the active virtualenv or the one inside the project
VIRTUAL_ENV ?= $(VENV_ROOT)/$(PROJECT_NAME)

VENV=$(VIRTUAL_ENV)

# host:port of the liveweb proxy. 
# This is used by the wayback.
LIVEWEB_ADDRESS=localhost:7070
WAYBACK_ADDRESS=:8080

CONFIG=config.yml

UWSGI=$(VENV)/bin/uwsgi -H$(VENV)

run:
	$(UWSGI) -M -i --http ${LIVEWEB_ADDRESS} --wsgi liveweb.main --pyargv $(CONFIG)

venv:
	virtualenv --no-site-packages $(VENV)
	$(VENV)/bin/pip install -r requirements.txt
	$(VENV)/bin/python setup.py develop

test:

	$(VENV)/bin/py.test liveweb/
    
wayback:
	$(UWSGI) --http ${WAYBACK_ADDRESS} --wsgi liveweb.tools.wayback --pyargv $(LIVEWEB_ADDRESS)

