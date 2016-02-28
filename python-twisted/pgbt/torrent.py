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

        # check encoding

        # get announce url

        # Ignore: 'creation date', 'comment', 'created by', 'announce-list'

        info_dict = content[b'info']
        self.info_hash = hashlib.sha1(bencodepy.encode(info_dict)).digest()

    def decode_info_dict(info):
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
