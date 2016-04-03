import socket
import time
import os
import logging

from qqbt.torrent_metainfo import TorrentMetainfo
from qqbt.torrent import Torrent
from qqbt.conn import ConnectionManager
from qqbt.config import CONFIG

log = logging.getLogger(__name__)


class QqbtClient():
    def __init__(self, outdir=None):
        self.active_torrents = []
        self.finished_torrents = []
        self.outdir = outdir
        self.conn_man = ConnectionManager()

    def add_torrent(self, filename):
        with open(filename, 'rb') as f:
            contents = f.read()

        # TODO: handle errors
        metainfo = TorrentMetainfo(contents)
        torrent = Torrent(
            self.conn_man, metainfo, self.on_completed_torrent,
            self.on_completed_piece)
        self.active_torrents.append(torrent)

    def on_completed_piece(self, torrent):
        print('%s: %s' % (torrent, torrent.get_progress_string()))

    def on_completed_torrent(self, torrent, data):
        print('Torrent completed!')
        if torrent.metainfo.info['format'] == 'SINGLE_FILE':
            self.save_single_file(torrent, data)
        else:
            self.save_multiple_file(torrent, data)

        self.active_torrents.remove(torrent)
        self.finished_torrents.append(torrent)

        if not self.active_torrents:
            self.all_torrents_completed()

    def all_torrents_completed(self):
        self.conn_man.stop_event_loop()

    def save_single_file(self, torrent, data):
        (_, filename) = os.path.split(torrent.metainfo.name)
        filepath = (os.path.join(os.path.expanduser(self.outdir), filename)
                    if self.outdir else filename)
        with open(filepath, 'wb') as f:
            f.write(data)
        log.info('save_single_file: %s' % filepath)

    def save_multiple_file(self, torrent, data):
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

    def start_torrents(self):
        for torrent in self.active_torrents:
            torrent.start_torrent()
        #log.info('Found %s peers: %s' %
                 #(len(torrent.peers), torrent.peers))

        #peer = [v for v in torrent.peers if v.ip == '96.126.104.219'][0]
        self.conn_man.start_event_loop()

    def zrun_torrent(self):
        """Download first torrent from first peer in a single thread."""
        # \/ this is a hack \/
        torrent = self.active_torrents[0]
        torrent.start_torrent()
        log.info('Found %s peers: %s' %
                 (len(torrent.peers), torrent.peers))

        peer = torrent.peers[1]
        peer.start_peer()

        while not peer.is_started:
            try:
                peer.receive_handshake()
            except socket.timeout:
                pass
            time.sleep(1)

        def _drain_msgs():
            try:
                while True:
                    peer.receive_message()
            except socket.timeout:
                pass
        _drain_msgs()
        peer.send_message('interested')

        while peer.peer_choking:
            time.sleep(1)
            log.info('Waiting to unchoke')
            _drain_msgs()

        log.info('Peer has %s of %s pieces' %
                 (sum(peer.peer_pieces), len(peer.peer_pieces)))

        def _request_all_pieces():
            num_pieces = len(torrent.metainfo.info['pieces'])
            for i in range(num_pieces):
                if torrent.complete_pieces[i] is not None:
                    continue
                piece_length = torrent.metainfo.get_piece_length(i)
                for begin in range(0, piece_length, CONFIG['block_length']):
                    block_length = min(piece_length, CONFIG['block_length'])

                    peer.send_message(
                        'request', index=i, begin=begin, length=block_length)
                    _drain_msgs()

            for _ in range(10):
                if not any(v is None for v in torrent.complete_pieces):
                    break
                time.sleep(1)
                _drain_msgs()
                print('Missing pieces: %s' % torrent.piece_blocks)

        while not torrent.is_complete:
            _request_all_pieces()
