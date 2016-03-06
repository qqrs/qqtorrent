from pgbt.torrent_metainfo import TorrentMetainfo
from pgbt.torrent import Torrent
from pgbt.peer import TorrentPeer


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
