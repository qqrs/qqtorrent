import struct
import socket
import requests
import bencodepy

from pgbt.config import CONFIG


class TorrentPeer():
    def __init__(self, torrent, ip, port, peer_id=None):
        self.torrent = torrent
        self.peer_id = peer_id
        self.ip = ip
        self.port = port
        self.sock = None

        self.is_started = False
        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

    def __del__(self):
        if self.sock:
            self.sock.close()

    def __repr__(self):
        return ('TorrentPeer(ip={ip}, port={port}, peer_id={peer_id})'
                .format(**self.__dict__))

    def start_peer(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect((self.ip, self.port))
        print('Sending peer handshake: %s:%s' % (self.ip, self.port))
        self.send_handshake_message()
        self.receive_handshake_message()

    def send_handshake_message(self):
        msg = self.build_handshake(
            self.torrent.metainfo.info_hash, CONFIG['peer_id'])
        self.sock.send(msg)

    def receive_handshake_message(self):
        pstrlen = int(self.sock.recv(1)[0])
        data = self.sock.recv(49 - 1 + pstrlen)
        handshake = self.decode_handshake(pstrlen, data)
        if handshake['pstr'] != 'BitTorrent protocol':
            raise PeerProtocolException('Protocol not recognized')
        print('Peer %s received handshake' % self)

    @staticmethod
    def build_handshake(info_hash, peer_id):
        """<pstrlen><pstr><reserved><info_hash><peer_id>"""
        pstr = b'BitTorrent protocol'
        fmt = '!B%ds8x20s20s' % len(pstr)
        msg = struct.pack(fmt, len(pstr), pstr, info_hash, peer_id)
        return msg

    @staticmethod
    def decode_handshake(pstrlen, data):
        fmt = '!%ds8x20s20s' % pstrlen
        fields = struct.unpack(fmt, data)

        return {
            'pstr': fields[0].decode('utf-8'),
            'info_hash': fields[1],
            'peer_id': fields[2].decode('utf-8')
        }


class AnnounceFailureError(Exception):
    pass


class AnnounceDecodeError(Exception):
    pass


class PeerProtocolException(Exception):
    pass
