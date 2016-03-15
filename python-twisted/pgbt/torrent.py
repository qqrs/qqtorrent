import struct
import requests
import bencodepy
import hashlib
import logging

from pgbt.config import CONFIG
from pgbt.peer import TorrentPeer

log = logging.getLogger(__name__)


class Torrent():
    """An active torrent upload/download."""
    def __init__(self, metainfo, on_complete=None):
        """
        Args:
            metainfo (TorrentMetainfo): decoded torrent file
            autostart (bool): immediately connect to tracker and start peers
        """
        self.metainfo = metainfo
        self.on_complete = on_complete
        self.active_peers = []
        self.other_peers = []
        self.tracker = None

        self.piece_blocks = [[] for _ in self.metainfo.info['pieces']]
        self.complete_pieces = [None for _ in self.metainfo.info['pieces']]
        self.is_complete = False

    def start_torrent(self):
        self.tracker = TorrentTracker(self, self.metainfo.announce)
        self.tracker.send_announce_request()

    def add_peer(self, peer_dict):
        """Add peer if not already present."""
        peer = self.find_peer(**peer_dict)
        if peer:
            return peer
        peer = TorrentPeer(self, **peer_dict)
        self.other_peers.append(peer)
        return peer

    def find_peer(self, ip, port):
        for peer_list in (self.active_peers, self.other_peers):
            for v in peer_list:
                if v.ip == ip and v.port == port:
                    return v
        return None

    def handle_block(self, piece_index, begin, block):
        for v in self.piece_blocks[piece_index]:
            if v[0] == begin:       # TODO: check for overlap of block range
                # already got this piece
                return
        self.piece_blocks[piece_index].append((begin, block))

        expected_length = self.metainfo.get_piece_length(piece_index)
        piece_length = sum(len(v[1]) for v in self.piece_blocks[piece_index])
        if piece_length == expected_length:
            self.handle_completed_piece(piece_index)

    def handle_completed_piece(self, piece_index):
        if self.complete_pieces[piece_index] is not None:
            log.warning('Piece %d already completed' % piece_index)
            return

        self.piece_blocks[piece_index].sort(key=lambda v: v[0])
        blocks = [v[1] for v in self.piece_blocks[piece_index]]
        piece = bytes(v for block in blocks for v in block)

        piece_sha = hashlib.sha1(piece).digest()
        canonical_sha = self.metainfo.info['pieces'][piece_index]
        if piece_sha != canonical_sha:
            # TODO: discard and retry piece
            raise TorrentPieceError('Piece %d sha mismatch')

        self.complete_pieces[piece_index] = piece
        self.piece_blocks[piece_index] = None
        log.debug('handle_completed_piece: %d' % piece_index)

        if not any(v is None for v in self.complete_pieces):
            self.handle_completed_torrent()

    def handle_completed_torrent(self):
        log.info('%s: handle_completed_torrent' % (self))
        self.is_complete = True
        data = bytes(v for piece in self.complete_pieces for v in piece)

        if self.on_complete:
            self.on_complete(self, data)


class TorrentTracker():
    """An tracker connection for a torrent."""
    def __init__(self, torrent, announce):
        self.torrent = torrent
        self.announce = announce
        self.tracker_id = None

    def send_announce_request(self):
        # TODO: send 'port', 'uploaded', 'downloaded', 'left', 'compact',
        # 'no_peer_id', 'event' (started/completed/stopped)
        http_resp = requests.get(self.announce, {
            'info_hash': self.torrent.metainfo.info_hash,
            'peer_id': CONFIG['peer_id']
        })
        self.handle_announce_response(http_resp)

    def handle_announce_response(self, http_resp):
        resp = bencodepy.decode(http_resp.text.encode('latin-1'))
        d = self.decode_announce_response(resp)

        # TODO: use 'interval', 'tracker id', 'complete', 'incomplete'

        for peer_dict in d['peers']:
            # TODO: raise error or warning on port = 0?
            if peer_dict['ip'] and peer_dict['port'] > 0:
                self.torrent.add_peer(peer_dict)

    @classmethod
    def decode_announce_response(cls, resp):
        d = {}

        if b'failure reason' in d:
            raise AnnounceFailureError(d[b'failure reason'].decode('utf-8'))

        d['interval'] = int(resp[b'interval'])
        d['complete'] = int(resp[b'complete'])
        d['incomplete'] = int(resp[b'incomplete'])

        try:
            d['tracker_id'] = resp[b'tracker id'].decode('utf-8')
        except KeyError:
            d['tracker_id'] = None

        raw_peers = resp[b'peers']
        if isinstance(raw_peers, list):
            d['peers'] = cls.decode_dict_model_peers(raw_peers)
        elif isinstance(raw_peers, bytes):
            d['peers'] = cls.decode_binary_model_peers(raw_peers)
        else:
            raise AnnounceDecodeError('Invalid peers format: %s' % raw_peers)

        return d

    @staticmethod
    def decode_dict_model_peers(peers_dicts):
        return [{'ip': d[b'ip'],
                 'port': d[b'port'],
                 'peer_id': d.get(b'peer id')}
                for d in peers_dicts]

    @staticmethod
    def decode_binary_model_peers(peers_bytes):
        fmt = '!BBBBH'
        fmt_size = struct.calcsize(fmt)
        if len(peers_bytes) % fmt_size != 0:
            raise AnnounceDecodeError('Binary model peers field length error')
        peers = [struct.unpack_from(fmt, peers_bytes, offset=ofs)
                 for ofs in range(0, len(peers_bytes), fmt_size)]

        return [{'ip': '%d.%d.%d.%d' % p[:4],
                 'port': int(p[4])}
                for p in peers]


class AnnounceFailureError(Exception):
    pass


class AnnounceDecodeError(Exception):
    pass


class TorrentPieceError(Exception):
    pass
