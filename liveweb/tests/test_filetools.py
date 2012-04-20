from .. import filetools
from cStringIO import StringIO

class TestMemFile:
    def test_nodata(self):
        f = filetools.MemFile()
        assert f.read() == ""
        assert f.readline() == ""
        
    def test_mem(self):
        f = filetools.MemFile(100)
        f.write("helloworld")
        assert f.tell() == 10
        f.seek(0)
        assert f.read() == "helloworld"

    def test_readlines(self):
        f = filetools.MemFile(100)
        f.write("a\nb\nc\n")
        f.seek(0)
        assert f.readline() == "a\n"
        assert f.readline() == "b\n"
        assert f.readline() == "c\n"
        assert f.readline() == ""
        
    def test_mem(self):
        f = filetools.MemFile(100)
        f.write("helloworld" * 10)
        assert f.tell() == 100
        assert f.in_memory() is True

        f.write("helloworld")
        assert f.in_memory() is False
        assert f.name is not None
        
        f.seek(0)
        content = f.read()
        assert len(content) == 110
        assert content == "helloworld" * 11    
        
        
def test_fileiter():
    f = StringIO("helloworld" * 15)
    # there are 15 "helloworld"s and we are asking it to read 4 of them.
    assert list(filetools.fileiter(f, 40, chunk_size=10)) == ["helloworld"] * 4

    # case where the size is not multiple of chunk_size
    assert list(filetools.fileiter(f, 38, chunk_size=10)) == ["helloworld", "helloworld", "helloworld", "hellowor"]

    # what if we ask for more data than we have?
    f = StringIO("helloworld" + "helloworld" + "end")
    assert list(filetools.fileiter(f, 40, chunk_size=10)) == ["helloworld", "helloworld", "end"]
