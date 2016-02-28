import os
import copy
import hashlib
from pprint import pformat
import bencodepy
import voluptuous as vol
#from schema import Schema, And, Use, Optional


class TorrentMetainfo():
    """A torrent metainfo file."""
    def __init__(self, bencontent):
        """
        Args:
            bencontent (bytes): bencoded torrent file contents
        """
        try:
            content = bencodepy.decode(bencontent)
        except bencodepy.DecodingError as e:
            # TODO: better msg
            raise TorrentDecodeError from e

        # TODO: validate shape using voluptuous or schema

        # 'encoding' field defines character encoding for 'pieces' field.
        encoding = content.get(b'encoding')
        if encoding and encoding.decode('utf-8').lower() != 'utf-8':
            raise(TorrentDecodeError('Unsupported encoding: %s' % encoding))

        self.announce = content[b'announce'].decode('utf-8')
        try:
            vol.Url()(self.announce)
        except vol.UrlInvalid as e:
            msg = 'Invalid announce URL: %s' % self.announce
            raise TorrentDecodeError(msg) from e

        # Ignore 'creation date', 'comment', 'created by', 'announce-list'

        info_dict = content[b'info']
        self.info_hash = hashlib.sha1(bencodepy.encode(info_dict)).digest()
        self.info = self._decode_info_dict(info_dict)

        print(self)

    def _decode_info_dict(self, d):
        info = {}

        info['piece_length'] = d[b'piece length']

        SHA_LEN = 20
        pieces_shas = d[b'pieces']
        info['pieces'] = [pieces_shas[i:i+SHA_LEN]
                          for i in range(0, len(pieces_shas), SHA_LEN)]
        # TODO: different representation?

        self.name = d[b'name'].decode('utf-8')

        files = d.get(b'files')
        if not files:
            info['format'] = 'SINGLE_FILE'
            info['files'] = None
            info['length'] = d[b'length']
        else:
            info['format'] = 'MULTIPLE_FILE'
            info['length'] = None
            info['files'] = []
            for f in d[b'files']:
                path_segments = [v.decode('utf-8') for v in f[b'path']]
                info['files'].append({
                    'length': f[b'length'],
                    'path': os.path.join(*path_segments)
                })

        return info

    def __repr__(self):
        tdict = copy.deepcopy(self.__dict__)
        if len(tdict['info']['pieces']) > 3:
            tdict['info']['pieces'] = tdict['info']['pieces'][:3] + ['...']
        if tdict['info']['files'] and len(tdict['info']['files']) > 3:
            tdict['info']['files'] = tdict['info']['files'][:3] + ['...']
        return ''.join(('TorrentMetainfo(', pformat(tdict), ')'))


class TorrentDecodeError(Exception):
    pass
