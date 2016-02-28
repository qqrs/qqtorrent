import bencodepy
import voluptuous as vol
import hashlib
#from schema import Schema, And, Use, Optional


class TorrentFile():
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
        encoding = content.get(b'encoding').decode('utf-8')
        if encoding and encoding.lower() != 'utf-8':
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
        self.info_dict = self.decode_info_dict(info_dict)

    def decode_info_dict(self, d):
        info = {}

        print(info)
        # pieces_length
        # pieces

        # if files list not present then single file mode
        #  name
        #  length
        # else
        #  name
        #  files
        #    length
        #    path
        pass






class TorrentDecodeError(Exception):
    pass
