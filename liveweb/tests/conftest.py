import os
import shutil
import urllib
import subprocess
import time

def pytest_funcarg__pooldir(request):
    "Creates a directory for the pool"
    dirname = "/tmp/pool-xxx"

    if os.path.exists(dirname):
        shutil.rmtree(dirname)

    os.mkdir(dirname)

    request.addfinalizer(lambda : shutil.rmtree(dirname))
    
    return dirname


def pytest_funcarg__webtest(request):
    dirname = os.path.dirname(__file__)
    path = os.path.join(dirname, "webtest.py")
    port = 9876

    p = subprocess.Popen(['python', path, str(port)])
    request.addfinalizer(p.kill)

    # Return an object with url and port atrributes
    x = lambda: None
    x.url = "http://127.0.0.1:%d" % port
    x.port = port

    # wait until the server is ready, with max-tries=20
    for i in range(20):
        print i
        try:
            urllib.urlopen(x.url + "/")
            break
        except IOError:
            time.sleep(0.1)

    return x
