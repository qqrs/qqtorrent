import copy
import bencode
from pprint import pprint, pformat

SHA_LEN = 20


class Torrent(object):
    def __init__(self, bentorrent):
        torrent_dict = bencode.bdecode(bentorrent)
        self.__dict__.update(torrent_dict)
        self.info = dotdict(self.info)

        # Separate SHA-1 hashes of pieces.
        # TODO: need to handle byte order?
        pieces = self.info.pieces
        assert(len(pieces) % 20 == 0)
        chunks = [pieces[i:i+SHA_LEN] for i in xrange(0, len(pieces), SHA_LEN)]
        self.info.pieces = chunks

        #TODO: validation


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
    """Dot notation access to dictionary attributes"""
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __getattr__(self, attr):
        return self.get(attr)

    def __deepcopy__(self, memo):
        return dotdict(copy.deepcopy(dict(self), memo))


if __name__ == '__main__':
    main()
