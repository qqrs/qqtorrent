import struct
import requests
import bencodepy

class Torrent():
    """An active torrent upload/download."""
    def __init__(self, metainfo, autostart=True):
        """
        Args:
            metainfo (TorrentMetainfo): decoded torrent file
            autostart (bool): immediately connect to tracker and start peers
        """
        self.metainfo = metainfo
        self.active_peers = []
        self.other_peers = []
        self.tracker = TorrentTracker(self)
        self.tracker.send_announce_request()


class TorrentTracker():
    def __init__(self, torrent):
        self.torrent = torrent
        self.tracker_id = None

    def send_announce_request(self):
        http_resp = requests.get(self.torrent.metainfo.announce, {
            'info_hash': self.torrent.metainfo.info_hash,
            'peer_id': 'QQ-0000-000000000000',
            'left': self.torrent.metainfo.info['length']
        })
        self.handle_announce_response(http_resp)

    def handle_announce_response(self, http_resp):
        resp = bencodepy.decode(http_resp.text.encode('latin-1'))
        d = self.decode_announce_response(resp)
        print(d)
        # set tracker id
        pass

    def decode_announce_response(self, resp):
        d = {}
        print(resp)

        # resp[b'failure reason']
        d['interval'] = int(resp[b'interval'])
        d['complete'] = int(resp[b'complete'])
        d['incomplete'] = int(resp[b'incomplete'])

        try:
            d['tracker_id'] = resp[b'tracker id'].decode('utf-8')
        except KeyError:
            d['tracker_id'] = None

        raw_peers = resp[b'peers']
        if isinstance(raw_peers, list):
            d['peers'] = self.decode_dict_model_peers(raw_peers)
        elif isinstance(raw_peers, bytes):
            d['peers'] = self.decode_binary_model_peers(raw_peers)
        else:
            raise AnnounceDecodeError('Invalid peers format: %s' % raw_peers)

        return d

    def decode_dict_model_peers(self, peers_dicts):
        return [TorrentPeer(ip=d[b'ip'], port=d[b'port'],
                            peer_id=d.get(b'peer id'))
                for d in peers_dicts]

    def decode_binary_model_peers(self, peers_bytes):
        fmt = '!BBBBH'
        fmt_size = struct.calcsize(fmt)
        assert(len(peers_bytes) % fmt_size == 0)
        peers = [struct.unpack_from(fmt, peers_bytes, offset=ofs)
                 for ofs in range(0, len(peers_bytes), fmt_size)]

        return [TorrentPeer(ip='%d.%d.%d.%d' % p[:4], port=int(p[4]))
                for p in peers]


class TorrentPeer():
    def __init__(self, ip, port, peer_id=None):
        self.peer_id = peer_id
        self.ip_address = ip
        self.port = port

    def __repr__(self):
        return ('TorrentPeer(ip={ip_address}, port={port}, peer_id={peer_id})'
                .format(**self.__dict__))


class AnnounceDecodeError(Exception):
    pass
