import socket
import time

from pgbt.torrent_metainfo import TorrentMetainfo
from pgbt.torrent import Torrent
from pgbt.config import CONFIG


class PgbtClient():
    def __init__(self):
        self.active_torrents = []

    def add_torrent(self, filename):
        with open(filename, 'rb') as f:
            contents = f.read()

        # TODO: handle errors
        metainfo = TorrentMetainfo(contents)
        torrent = Torrent(metainfo)
        torrent.start_torrent()
        peer = torrent.other_peers[0]
        peer.start_peer()

        def _drain_msgs():
            try:
                while True:
                    peer.receive_message()
            except socket.timeout:
                pass
        _drain_msgs()
        peer.send_message('interested')
        _drain_msgs()

        num_pieces = len(torrent.metainfo.info['pieces'])
        for i in range(num_pieces):
            piece_length = torrent.metainfo.get_piece_length(i)
            for begin in range(0, piece_length, CONFIG['block_length']):
                block_length = min(piece_length, CONFIG['block_length'])

                print('Sending request (%s, %s, %s)' % (i, begin, block_length))
                peer.send_message(
                    'request', index=i, begin=begin, length=block_length)
                _drain_msgs()

        time.sleep(5)
        _drain_msgs()
        print(num_pieces)
        print(len(torrent.piece_blocks))
        print(torrent.piece_blocks)
        import ipdb; ipdb.set_trace()
