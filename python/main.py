import copy
import bencode
from pprint import pprint, pformat

import voluptuous


SHA_LEN = 20


class Torrent(object):
    """A torrent file"""
    def __init__(self, benstr):
        """
        Args:
            benstr (str): bencoded str with torrent file contents
        """
        d = bencode.bdecode(benstr)
        d = self._validate_dict(d)
        d = dict_keys_to_underscores(d)
        self.__dict__.update(d)
        self.info = dotdict(self.info)

        # Separate SHA-1 hashes of pieces.
        # TODO: need to respect encoding value?
        # TODO: need to handle byte order?
        pieces = self.info.pieces
        assert(len(pieces) % 20 == 0)
        chunks = [pieces[i:i+SHA_LEN] for i in xrange(0, len(pieces), SHA_LEN)]
        self.info.pieces = chunks

    def _validate_dict(self, torrent_dict):
        schema = voluptuous.Schema({
            'announce': str,
            'encoding': str,
            voluptuous.Optional('created by'): str,
            voluptuous.Optional('creation date'): int,
            'info': {
                'length': int,
                'name': str,
                'piece length': int,
                'pieces': str
            }
        }, required=True)

        return schema(torrent_dict)

    def __repr__(self):
        tdict = copy.deepcopy(self.__dict__)
        if tdict['info']['pieces']:
            tdict['info']['pieces'] = '...'
        return ''.join(('Torrent(', pformat(tdict), ')'))


def main():
    torrent = open_torrent('../shared/flagfromserver.torrent')
    print torrent


def open_torrent(filename):
    with open(filename) as f:
        t = Torrent(f.read())
    return t


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
