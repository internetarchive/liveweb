import glob
import os

def test_creation(pooldir):
    """
    Tests to see if the file pool is created properly.

    Creates a pool and then walks through the pool directory to see if
    the expected files are there.
    """
    from ..file_pool import FilePool

    # Create the pool
    pool = FilePool(pooldir, pattern = "test-%(serial)05d", max_files = 10, max_file_size = 10)

    # call pool.get_file() so that files are initialized
    for i in range(pool.max_files):
        pool.get_file()

    # Get files in pool directory.
    pool_files = set(glob.glob(pooldir + "/partial/*"))

    # Check if this is the same as what we expect
    expected_files = set(["%s/partial/test-%05d"%(pooldir,x) for x in range(0,10)])

    assert expected_files == pool_files

def test_get_return(pooldir):
    """
    Tests to see if get_file return_file work as expected.

    gets files, checks the number of files in the queue, returns them
    and checks again.
    """

    from ..file_pool import FilePool

    # Create the pool
    pool = FilePool(pooldir, pattern = "test-%(serial)05d", max_files = 10, max_file_size = 10)

    fps = []

    assert len(pool.queue.queue) == 10

    for i in range(1, 6):
        fps.append(pool.get_file())
        assert len(pool.queue.queue) == 10 - i

    assert len(pool.queue.queue) == 5

    for i in range(1, 6):
        pool.return_file(fps.pop())
        assert len(pool.queue.queue) == 5 + i

    assert len(pool.queue.queue) == 10

def test_max_file_size(pooldir):
    """
    Tests to see if the files are closed and released when the maximum
    file size is reached and the file is returned.
    """
    from ..file_pool import FilePool

    # Create the pool
    pool = FilePool(pooldir, pattern = "test-%(serial)05d", max_files = 10, max_file_size = 10)

    fp = pool.get_file()
    fp.write("test" * 100) # Max size has been exceeded. File should
    pool.return_file(fp)   # get removed from pool when returned.

    # queue should have all Nones now.
    assert list(pool.queue.queue) == [None] * 10

    complete_files = set(glob.glob(pooldir + "/complete/*"))
    expected_complete_files = set(("%s/complete/test-%05d"%(pooldir,0),))
    assert expected_complete_files == complete_files


def test_close_pool(pooldir):
    """
    Makes sure that the pool is emptied when closed.

    """
    from ..file_pool import FilePool

    # Create the pool
    pool = FilePool(pooldir, pattern = "test-%(serial)05d", max_files = 10, max_file_size = 10)

    pool.close()

    assert len(pool.queue.queue) == 0


def test_member_file_context(pooldir):
    """
    Tests the context manager behaviour of the MemberFile object.
    """

    from ..file_pool import FilePool

    # Create the pool
    pool = FilePool(pooldir, pattern = "test-%(serial)05d", max_files = 10, max_file_size = 10)

    assert len(pool.queue.queue) == 10

    with pool.get_file() as f:
        assert len(pool.queue.queue) == 9
        name = f.name
        f.write("Hello")

    assert len(pool.queue.queue) == 10
    pool.close()

    assert open(name).read() == "Hello"
