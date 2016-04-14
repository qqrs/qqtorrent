import os
import logging

from qqbt.torrent_metainfo import TorrentMetainfo
from qqbt.torrent import Torrent
from qqbt.conn import ConnectionManager

log = logging.getLogger(__name__)


class QqbtClient():
    """BitTorrent client class.

    Provides an interface to all operations needed to start, run, or a complete
    a torrent.  All CLI or GUI entry points should interface only with this
    class. All file operations should happen only within this class.
    """
    def __init__(self, outdir=None):
        self.active_torrents = []
        self.finished_torrents = []
        self.outdir = outdir
        self.conn_man = ConnectionManager()

    def add_torrent(self, filename):
        with open(filename, 'rb') as f:
            contents = f.read()

        # TODO: comprehensively handle errors
        metainfo = TorrentMetainfo(contents)
        torrent = Torrent(
            self.conn_man, metainfo, self.on_completed_torrent,
            self.on_completed_piece)
        self.active_torrents.append(torrent)

    def start_torrents(self):
        for torrent in self.active_torrents:
            torrent.start_torrent()
        self.conn_man.start_event_loop()

    def on_completed_piece(self, torrent):
        print('%s: %s' % (torrent, torrent.get_progress_string()))

    def on_completed_torrent(self, torrent, data):
        print('Torrent completed!')
        if torrent.metainfo.info['format'] == 'SINGLE_FILE':
            self._save_single_file(torrent, data)
        else:
            self._save_multiple_file(torrent, data)

        self.active_torrents.remove(torrent)
        self.finished_torrents.append(torrent)

        if not self.active_torrents:
            self.on_all_torrents_completed()

    def on_all_torrents_completed(self):
        self.conn_man.stop_event_loop()

    def _save_single_file(self, torrent, data):
        (_, filename) = os.path.split(torrent.metainfo.name)
        filepath = (os.path.join(os.path.expanduser(self.outdir), filename)
                    if self.outdir else filename)
        with open(filepath, 'wb') as f:
            f.write(data)
        log.info('save_single_file: %s' % filepath)

    def _save_multiple_file(self, torrent, data):
        begin = 0
        base_dir = torrent.metainfo.name
        base_dir = (os.path.join(os.path.expanduser(self.outdir), base_dir)
                    if self.outdir else base_dir)
        for file_dict in torrent.metainfo.info['files']:
            filepath = os.path.join(base_dir, file_dict['path'])
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file_data = data[begin: begin+file_dict['length']]
            with open(filepath, 'wb') as f:
                f.write(file_data)
            log.info('save_multiple_file: %s' % filepath)
            begin += file_dict['length']

        if begin != len(data):
            log.warn('begin != len(data)')
