import struct
import socket
import bitarray

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
        return ('TorrentPeer(ip={ip}, port={port})'
                .format(**self.__dict__))

    def start_peer(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(0.2)
        self.sock.connect((self.ip, self.port))
        print('Sending peer handshake: %s:%s' % (self.ip, self.port))
        self.send_handshake()
        self.receive_handshake()

    def send_handshake(self):
        msg = self.build_handshake(
            self.torrent.metainfo.info_hash, CONFIG['peer_id'])
        self.sock.send(msg)

    def send_message(self, msg_type, **params):
        msg = self.build_message(msg_type, **params)
        self.sock.send(msg)

    def receive_handshake(self):
        pstrlen = int(self.sock.recv(1)[0])
        data = self.sock.recv(49 - 1 + pstrlen)
        handshake = self.decode_handshake(pstrlen, data)
        if handshake['pstr'] != 'BitTorrent protocol':
            raise PeerProtocolError('Protocol not recognized')
        print('%s received handshake' % self)

    def receive_message(self):
        # get length prefix
        data_len = 4
        data = self.sock.recv(data_len)
        while len(data) < data_len:
            data += self.sock.recv(data_len - len(data))

        # unpack length prefix
        length_prefix = struct.unpack('!L', data)[0]
        if length_prefix == 0:
            print('%s received keep-alive' % self)
            return

        # get data
        data = self.sock.recv(length_prefix)
        while len(data) < length_prefix:
            data += self.sock.recv(length_prefix - len(data))
            #raise PeerProtocolError('Incomplete message received')

        # decode data and handle message
        msg_dict = self.decode_message(data)
        self.handle_message(msg_dict)

    def handle_keepalive(self):
        # TODO
        pass

    def handle_message(self, msg_dict):
        msg_id = msg_dict['msg_id']
        payload = msg_dict['payload']

        # TODO: implement all
        if msg_id == 0:
            msg_type = 'choke'
        elif msg_id == 1:
            msg_type = 'unchoke'
        elif msg_id == 2:
            msg_type = 'interested'
        elif msg_id == 3:
            msg_type = 'not_interested'
        elif msg_id == 4:
            msg_type = 'have'
            # TODO
        elif msg_id == 5:
            msg_type = 'bitfield'
            # TODO
            bitfield = payload
            ba = bitarray.bitarray(endian='big')
            ba.frombytes(bitfield)
            for i in range(len(self.torrent.metainfo.info['pieces'])):
                if not ba.pop():
                    print('Missing piece: %x' % i)
        elif msg_id == 6:
            msg_type = 'request'
        elif msg_id == 7:
            msg_type = 'piece'
            (index, begin) = struct.unpack('!LL', payload[:8])
            block = payload[8:]
            self.torrent.handle_block(index, begin, block)
        elif msg_id == 8:
            msg_type = 'cancel'
        elif msg_id == 9:
            msg_type = 'port'
        else:
            raise PeerProtocolMessageTypeError(
                'Unrecognized message id: %s' % msg_id)

        print('%s received msg: id=%s type=%s payload=%s%s' %
              (self, msg_id, msg_type,
               ''.join('%02X' % v for v in payload[:64]),
               '...' if len(payload) >= 64 else ''))


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


class PeerProtocolError(Exception):
    pass


class PeerProtocolMessageTypeError(PeerProtocolError):
    pass
