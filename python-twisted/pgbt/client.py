from torrent import TorrentMetainfo


class PgbtClient():
    def __init__(self):
        pass

    def add_torrent(self, filename):
        torrent = self._load_torrent(filename)
        # TODO: add to active torrents
        pass

    def _load_torrent(self, filename):
        with open(filename, 'rb') as f:
            contents = f.read()
            # TODO: handle errors
            return TorrentMetainfo(contents)
