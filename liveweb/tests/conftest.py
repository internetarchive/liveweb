import os
import shutil

def pytest_funcarg__pooldir(request):
    "Creates a directory for the pool"
    dirname = "/tmp/pool-xxx"

    if os.path.exists(dirname):
        shutil.rmtree(dirname)

    os.mkdir(dirname)

    request.addfinalizer(lambda : shutil.rmtree(dirname))
    
    return dirname

    
