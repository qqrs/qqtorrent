from nose.tools import *

from pgbt.torrent import Torrent, TorrentTracker, AnnounceDecodeError


def setup():
    pass


def teardown():
    pass


# TODO: integration tests


def test_torrent_add_peer():
    t = Torrent(None)
    pd1 = {'ip': '1.1.1.1', 'port': 1}
    pd2 = {'ip': '1.1.1.2', 'port': 1}

    p1a = t.add_peer(pd1)
    assert_is_not_none(p1a)
    p1b = t.add_peer(pd1)
    assert_is_not_none(p1b)
    assert_equal(id(p1a), id(p1b))

    p2 = t.add_peer(pd2)
    assert_is_not_none(p2)
    assert(len(t.other_peers) == 2)


def test_torrent_tracker_decode_binary_model_peers():
    peers_bytes = b'\xce\xfc\xd7\x8a\x00\x00`~h\xdb\xcb\xa2'
    peers_dicts = TorrentTracker.decode_binary_model_peers(peers_bytes)
    assert_equals(peers_dicts,
        [{'port': 0, 'ip': '206.252.215.138'},
         {'port': 52130, 'ip': '96.126.104.219'}])

    peers_dicts = TorrentTracker.decode_binary_model_peers(b'')
    assert_equals(peers_dicts, [])

    peers_bytes = b'\xce\xfc\xd7\x8a\x00'
    assert_raises(AnnounceDecodeError,
                  TorrentTracker.decode_binary_model_peers, peers_bytes)
