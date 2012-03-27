

run:
	./bin/uwsgi --http :8080 --wsgi liveweb

venv:
	virtualenv --no-site-packages .
	./bin/pip install -r requirements.txt
	python setup.py develop

test:

	./bin/py.test liveweb/
    
