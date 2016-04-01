import struct
import socket
import bitarray
import logging
import random

from pgbt.config import CONFIG

log = logging.getLogger(__name__)


class TorrentPeer():
    def __init__(self, torrent, ip, port, peer_id=None):
        self.torrent = torrent
        self.peer_id = peer_id
        self.ip = ip
        self.port = port
        self.sock = None
        self.conn = None
        self.recv_buffer = b''

        self.is_started = False
        self.conn_failed = False
        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

        self.peer_pieces = [False for _ in range(
                            len(self.torrent.metainfo.info['pieces']))]
        self.requested_piece = None

    #def __del__(self):
        #if self.sock:
            #self.sock.close()

    def __repr__(self):
        return ('TorrentPeer(ip={ip}, port={port})'
                .format(**self.__dict__))

    def handle_connection_made(self, conn):
        self.conn = conn
        log.debug('%s: handle_connection_made' % self)
        self.run_download()

    def handle_connection_failed(self):
        log.debug('connection failed: %s' % self)
        self.conn_failed = True
        self.conn = None
        self.torrent.handle_peer_stopped(self)

    def handle_connection_lost(self):
        log.debug('connection lost: %s' % self)
        self.conn_failed = True
        self.conn = None
        self.torrent.handle_peer_stopped(self)

    def handle_data_received(self, recv_data):
        """Parse individual messages from the data."""
        #log.info('%s: handle_data_received: %s' % (self, data))
        # TODO: mark connection failed on incomplete message
        data = self.recv_buffer + recv_data
        while data:
            if not self.is_started:
                nbytes = self.parse_handshake(data)
            else:
                nbytes = self.parse_message(data)
            if nbytes == 0:
                break
            data = data[nbytes:]
        self.recv_buffer = data

    def handle_torrent_completed(self):
        if self.conn:
            self.conn.disconnect()
        self.requested_piece = None

    def on_handshake_ok(self):
        self.run_download()

    def on_unchoke(self):
        self.run_download()

    def write_message(self, msg):
        """Write message data to wire."""
        #self.sock.send(msg)
        if self.conn:
            self.conn.write(msg)

    def connect(self):
        self.torrent.conn_man.connect_peer(self)

    def run_download(self):
        if not self.is_started:
            self.send_handshake()
        elif self.peer_choking:
            self.send_message('interested')
        elif self.requested_piece is not None:
            # Wait for piece to finish downloading.
            pass
        else:
            try:
                piece = self.choose_next_piece()
            except PeerNoUnrequestedPiecesError:
                self.conn.disconnect()
                self.torrent.handle_peer_stopped(self)
                return

            self.requested_piece = piece
            self.torrent.piece_requests[piece].append(self)
            self.request_next_block(piece, None)

    def choose_next_piece(self):
        """Return piece index of best piece to fetch from peer next."""
        num_pieces = len(self.torrent.metainfo.info['pieces'])
        # Get first piece that is not complete, not already request from any
        # peer, and is available from this peer.
        for i in range(num_pieces):
            if (not self.torrent.complete_pieces[i]
                    and not self.torrent.piece_requests[i]
                    and self.peer_pieces[i]):
                return i

        # Engdgame. Get a piece that is not complete and is available from this
        # peer, even if already requested from another peer.
        candidates = [i for i in range(num_pieces)
                        if not self.torrent.complete_pieces[i]
                        and self.peer_pieces[i]]
        if not candidates:
            # Raise exception so we can disconnect.
            raise PeerNoUnrequestedPiecesError
        return random.choice(candidates)


    #def start_peer(self):
        #log.info('%s: start_peer', self)
        #self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.sock.settimeout(10)
        #self.sock.connect((self.ip, self.port))
        #self.send_handshake()

    def send_handshake(self):
        log.debug('%s: send_handshake' % self)
        msg = self.build_handshake(
            self.torrent.metainfo.info_hash, CONFIG['peer_id'])
        self.write_message(msg)

    def send_message(self, msg_type, **params):
        """Validate, build, and send message to peer."""
        if not self.is_started:
            raise PeerConnectionError(
                'Attempted to send message before handshake received')
        log.debug('%s: send_message: type=%s params=%s' %
                  (self, msg_type, params))
        if msg_type == 'request' and self.peer_choking:
            log.debug('Attempted to send message to choking peer')
            return
        msg = self.build_message(msg_type, **params)
        self.write_message(msg)

    def request_next_block(self, piece_index, begin):
        piece_length = self.torrent.metainfo.get_piece_length(piece_index)
        begin = 0 if begin is None else begin + CONFIG['block_length']
        block_length = min(piece_length - begin, CONFIG['block_length'])

        self.send_message(
            'request', index=piece_index, begin=begin, length=block_length)

    def parse_handshake(self, data):
        """Parse a handshake and return bytes consumed, or raise exception."""
        # TODO: check for incomplete message
        pstrlen = int(data[0])
        handshake_data = data[1: 49 + pstrlen]
        handshake = self.decode_handshake(pstrlen, handshake_data)
        if handshake['pstr'] != 'BitTorrent protocol':
            raise PeerProtocolError('Protocol not recognized')
        self.is_started = True
        log.debug('%s: received_handshake' % self)
        self.on_handshake_ok()
        return(1 + len(handshake_data))

    #def receive_handshake(self):
        ## TODO: don't call sock.recv here
        #pstrlen = int(self.sock.recv(1)[0])
        #data = self.sock.recv(49 - 1 + pstrlen)
        #handshake = self.decode_handshake(pstrlen, data)
        #if handshake['pstr'] != 'BitTorrent protocol':
            #raise PeerProtocolError('Protocol not recognized')
        #self.is_started = True
        #self.sock.settimeout(0.1)
        #log.debug('%s: received_handshake' % self)

    #def receive_message(self):
        ## get length prefix
        #data_len = 4
        #data = self.sock.recv(data_len)
        #while len(data) < data_len:
            #data += self.sock.recv(data_len - len(data))

        ## unpack length prefix
        #length_prefix = struct.unpack('!L', data)[0]
        #if length_prefix == 0:
            ## TODO: handle keep-alive
            #log.debug('%s: receive_message: keep-alive' % self)
            #return

        ## get data
        #data = self.sock.recv(length_prefix)
        #while len(data) < length_prefix:
            #data += self.sock.recv(length_prefix - len(data))
            ##raise PeerProtocolError('Incomplete message received')

        ## decode data and handle message
        #msg_dict = self.decode_message(data)
        #self.handle_message(msg_dict)

    def parse_message(self, data):
        """Parse a message and return bytes consumed, or raise exception."""
        nbytes = 0      # bytes of data consumed

        if len(data) < 4:
            return 0

        # get length prefix
        length_prefix = struct.unpack('!L', data[:4])[0]
        nbytes += 4

        if length_prefix == 0:
            # TODO: handle keep-alive
            log.debug('%s: receive_message: keep-alive' % self)
            return nbytes

        if nbytes + length_prefix > len(data):
            #raise PeerProtocolError('Incomplete message received')
            return 0

        # decode data and handle message
        msg_dict = self.decode_message(data[nbytes:nbytes+length_prefix])
        nbytes += length_prefix
        self.handle_message(msg_dict)
        return nbytes

    def handle_keepalive(self):
        # TODO
        pass

    def handle_message(self, msg_dict):
        msg_id = msg_dict['msg_id']
        payload = msg_dict['payload']
        msg_types = ['choke', 'unchoke', 'interested', 'not_interested',
                     'have', 'bitfield', 'request', 'piece', 'cancel', 'port']
        msg_type = msg_types[msg_id]

        log.debug('%s: receive_msg: id=%s type=%s payload=%s%s' %
                  (self, msg_id, msg_type,
                   ''.join('%02X' % v for v in payload[:40]),
                   '...' if len(payload) >= 64 else ''))

        # TODO: implement all
        if msg_id == 0:
            assert(msg_type == 'choke')
            self.peer_choking = True
        elif msg_id == 1:
            assert(msg_type == 'unchoke')
            self.peer_choking = False
            self.on_unchoke()
        elif msg_id == 2:
            assert(msg_type == 'interested')
            self.peer_interested = True
        elif msg_id == 3:
            assert(msg_type == 'not_interested')
            self.peer_interested = False
        elif msg_id == 4:
            assert(msg_type == 'have')
            (index,) = struct.unpack('!L', payload)
            self.peer_pieces[index] = True
        elif msg_id == 5:
            assert(msg_type == 'bitfield')
            bitfield = payload
            ba = bitarray.bitarray(endian='big')
            ba.frombytes(bitfield)
            num_pieces = len(self.torrent.metainfo.info['pieces'])
            # Bitfield only comes once as first msg so it can replace list.
            self.peer_pieces = ba.tolist()[:num_pieces]
        elif msg_id == 6:
            assert(msg_type == 'request')
        elif msg_id == 7:
            assert(msg_type == 'piece')
            (index, begin) = struct.unpack('!LL', payload[:8])
            block = payload[8:]
            self.torrent.handle_block(self, index, begin, block)
        elif msg_id == 8:
            assert(msg_type == 'cancel')
        elif msg_id == 9:
            assert(msg_type == 'port')
        else:
            raise PeerProtocolMessageTypeError(
                'Unrecognized message id: %s' % msg_id)

    @staticmethod
    def build_handshake(info_hash, peer_id):
        """<pstrlen><pstr><reserved><info_hash><peer_id>"""
        pstr = b'BitTorrent protocol'
        fmt = '!B%ds8x20s20s' % len(pstr)
        msg = struct.pack(fmt, len(pstr), pstr, info_hash, peer_id)
        return msg

    @staticmethod
    def build_message(msg_type, **params):
        """<length_prefix><msg_id><payload>"""

        msg_id = None
        payload = b''
        # TODO: implement all
        if msg_type == 'choke':
            msg_id = 0
        elif msg_id == 'unchoke':
            msg_id = 1
        elif msg_type == 'interested':
            msg_id = 2
        elif msg_type == 'not_interested':
            msg_id = 3
        elif msg_type == 'have':
            msg_id = 4
        elif msg_type == 'bitfield':
            msg_id = 5
        elif msg_type == 'request':
            msg_id = 6
            payload = struct.pack('!LLL',
                                  params['index'], params['begin'],
                                  params['length'])
        elif msg_type == 'piece':
            msg_id = 7
        elif msg_type == 'cancel':
            msg_id = 8
        elif msg_type == 'port':
            msg_id = 9
        else:
            raise PeerProtocolMessageTypeError(
                'Unrecognized message id: %s' % msg_id)

        length_prefix = len(payload) + 1
        fmt = '!LB%ds' % len(payload)
        msg = struct.pack(fmt, length_prefix, msg_id, payload)

        return msg

    @staticmethod
    def decode_handshake(pstrlen, data):
        fmt = '!%ds8x20s20s' % pstrlen
        fields = struct.unpack(fmt, data)

        return {
            'pstr': fields[0].decode('utf-8'),
            'info_hash': fields[1],
            'peer_id': fields[2]
        }

    @staticmethod
    def decode_message(data):
        msg_id = int(data[0])
        payload = data[1:]

        return {
            'msg_id': msg_id,
            'payload': payload
        }


class AnnounceFailureError(Exception):
    pass


class AnnounceDecodeError(Exception):
    pass


class PeerConnectionError(Exception):
    pass


class PeerProtocolError(Exception):
    pass


class PeerProtocolMessageTypeError(PeerProtocolError):
    pass


class PeerNoUnrequestedPiecesError(Exception):
    pass
