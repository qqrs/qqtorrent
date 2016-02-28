import sys
from nose.tools import *
import pgbt.cli
import pgbt.torrent


def setup():
    pass


def teardown():
    pass


def test_basic():
    pass


def test_main():
    assert_is_none(pgbt.cli.main())
    if hasattr(sys.stdout, "getvalue"):
        output = sys.stdout.getvalue().strip()
        assert_equals(output,'hello')


def test_torrent():
    assert_equal(pgbt.torrent.torrentfn(), 'torrent')
