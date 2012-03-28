
VENV=.

# host:port of the liveweb proxy. 
# This is used by the wayback.
LIVEWEB=localhost:9099

UWSGI=$(VENV)/bin/uwsgi -H$(VENV)

run:
	$(UWSGI) --http :8080 --wsgi liveweb

venv:
	virtualenv --no-site-packages $(VENV)
	$(VENV)/bin/pip install -r requirements.txt
	python setup.py develop

test:

	$(VENV)/bin/py.test liveweb/
    
wayback:
	$(UWSGI) --http :9000 --wsgi liveweb.tools.wayback --pyargv $(LIVEWEB)
