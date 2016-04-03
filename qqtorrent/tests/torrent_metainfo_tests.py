import sys
import copy
from nose.tools import *
import bencodepy

from qqbt.torrent_metainfo import TorrentMetainfo, TorrentDecodeError


def setup():
    pass


def teardown():
    pass


def _load_torrent(filename):
    with open(filename, 'rb') as f:
        return f.read()


def test_single_file_torrent():
    filename = '../shared/flagfromserver.torrent'
    t = TorrentMetainfo(_load_torrent(filename))
    info = t.info

    assert_equal(t.announce, 'http://thomasballinger.com:6969/announce')
    assert_equal(t.info_hash,
                 b'+\x15\xca+\xfdH\xcd\xd7m9\xecU\xa3\xab\x1b\x8aW\x18\n\t')
    assert_equal(t.name, 'flag.jpg')
    assert_is_none(info['files'])
    assert_equal(info['format'], 'SINGLE_FILE')
    assert_equal(info['piece_length'], 16384)
    assert_equal(len(info['pieces']), 79)
    assert_true(all(type(v) is bytes and len(v) == 20 for v in info['pieces']))


def test_multiple_file_torrent():
    filename = '../shared/amusementsinmath16713gut_archive.torrent'
    t = TorrentMetainfo(_load_torrent(filename))
    info = t.info

    assert_equal(t.announce, 'http://bt1.archive.org:6969/announce')
    assert_equal(t.info_hash,
                 b'SO;Z;\xa8\x14\x15\x1f\xd6h$"fa\xd0\x10Vw\x80')
    assert_equal(t.name, 'amusementsinmath16713gut')
    assert_is_not_none(info['files'])
    assert_equal(len(info['files']), 497)
    assert_true(all(type(v) is dict
                    and type(v['path']) is str and type(v['length']) is int
                    for v in info['files']))
    assert_equal(sum(v['length'] for v in info['files']), 16058935)
    assert_equal(info['format'], 'MULTIPLE_FILE')
    assert_equal(info['piece_length'], 524288)
    assert_equal(len(info['pieces']), 31)
    assert_true(all(type(v) is bytes and len(v) == 20 for v in info['pieces']))


# TODO: cover more bad formats
def test_torrent_decode_exceptions():
    assert_raises(TorrentDecodeError, TorrentMetainfo, b'')
    assert_raises(TorrentDecodeError, TorrentMetainfo, b' ')

    sample = {
        'announce': 'http://aaa.com',
        'encoding': 'UTF-8',
        'info': {
            'name': 'bbb',
            'length': 1,
            'piece length': 1,
            'pieces': b'.....................'
        }
    }
    TorrentMetainfo(bencodepy.encode(sample))

    t = copy.deepcopy(sample)
    t['announce'] = ''
    assert_raises(TorrentDecodeError, TorrentMetainfo, bencodepy.encode(t))

    t = copy.deepcopy(sample)
    del t['encoding']
    TorrentMetainfo(bencodepy.encode(t))

    t = copy.deepcopy(sample)
    t['encoding'] = 'zzz'
    assert_raises(TorrentDecodeError, TorrentMetainfo, bencodepy.encode(t))
