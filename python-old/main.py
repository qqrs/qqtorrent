import copy
import struct
import hashlib
from pprint import pprint, pformat

import bencode
import voluptuous
import requests


SHA_LEN = 20
assert(hashlib.sha1().digest_size == SHA_LEN)


class Torrent(object):
    """A torrent file"""
    def __init__(self, benstr):
        """
        Args:
            benstr (str): bencoded str with torrent file contents
        """
        d = bencode.bdecode(benstr)
        info_hash = hashlib.sha1(bencode.bencode(d['info'])).digest()
        d = self._validate_dict(d)
        d = dict_keys_to_underscores(d)
        self.__dict__.update(d)
        self.info = dotdict(self.info)
        self.info_hash = info_hash

        # Separate SHA-1 hashes of pieces.
        # TODO: need to respect encoding value?
        # TODO: need to handle byte order?
        pieces = self.info.pieces
        chunks = [pieces[i:i+SHA_LEN] for i in xrange(0, len(pieces), SHA_LEN)]
        self.info.pieces = chunks

    def _validate_dict(self, torrent_dict):

        def LengthAligned(boundary=None, msg=None):
            """The length must be aligned to a multiple of boundary."""
            def f(v):
                if boundary and boundary > 0 and len(v) % boundary != 0:
                    raise voluptuous.LengthInvalid(
                        'length of value must be a multiple of %s' % boundary)
                return v
            return f

        schema = voluptuous.Schema({
            'announce': voluptuous.Url(),
            'encoding': str,
            voluptuous.Optional('created by'): str,
            voluptuous.Optional('creation date'): int,
            'info': {
                'length': int,
                'name': str,
                'piece length': int,
                'pieces': voluptuous.All(str, LengthAligned(SHA_LEN))
            }
        # TODO: more permissive validation?
        }, required=True)

        return schema(torrent_dict)

    def __repr__(self):
        tdict = copy.deepcopy(self.__dict__)
        if tdict['info']['pieces']:
            tdict['info']['pieces'] = '...'
        return ''.join(('Torrent(', pformat(tdict), ')'))


def main():
    torrent = open_torrent('../shared/flagfromserver.torrent')
    resp = requests.get(torrent.announce, {
        'info_hash': torrent.info_hash,
        'peer_id': 'QQ-0000-' + '0' * 12,
        'left': torrent.info.length
    })
    d = bencode.bdecode(resp.text)
    if not isinstance(d['peers'], dict):
        d['peers'] = binary_peers_to_dict(d['peers'].encode('latin-1'))

    print d


def open_torrent(filename):
    with open(filename) as f:
        t = Torrent(f.read())
    return t


def binary_peers_to_dict(peers_bytes):
    fmt = '!BBBBH'
    fmt_size = struct.calcsize(fmt)
    assert(len(peers_bytes) % fmt_size == 0)
    peers = [struct.unpack_from(fmt, peers_bytes, offset=ofs)
             for ofs in xrange(0, len(peers_bytes), fmt_size)]
    return [{
        'ip': '%d.%d.%d.%d' % p[:4],
        'port': '%d' % p[4]
    } for p in peers]


class dotdict(dict):
    """Dot notation access to dictionary attributes."""
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __getattr__(self, attr):
        return self.get(attr)

    def __deepcopy__(self, memo):
        return dotdict(copy.deepcopy(dict(self), memo))


def dict_keys_to_underscores(d):
    """Replaces spaces in dict keys with underscores, recursively."""
    for k in d.keys():
        if isinstance(d[k], dict):
            dict_keys_to_underscores(d[k])
        if ' ' in k:
            d[k.replace(' ', '_')] = d[k]
            del d[k]
    return d


if __name__ == '__main__':
    main()
