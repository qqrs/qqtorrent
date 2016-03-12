from pgbt.torrent_metainfo import TorrentMetainfo
from pgbt.torrent import Torrent
from pgbt.peer import TorrentPeer

import socket

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
        torrent.other_peers[0].start_peer()

        def _drain_msgs():
            try:
                while True:
                    torrent.other_peers[0].receive_message()
            except socket.timeout:
                pass
        _drain_msgs()
        torrent.other_peers[0].send_message('interested')
        _drain_msgs()

        for (i, piece_sha) in enumerate(torrent.metainfo.info['pieces']):
            torrent.other_peers[0].send_message('request', index=i, begin=0, length=2**14)
            print(piece_sha)
            _drain_msgs()
