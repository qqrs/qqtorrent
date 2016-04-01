import logging
import selectors
import socket
from twisted.internet import protocol, reactor

log = logging.getLogger(__name__)

#concurrency_mode = 'twisted'
concurrency_mode = 'select'
#concurrency_mode = 'threads'


#class ConnectionManager():
    #def connect_peer(peer):
        #raise NotImplementedError

    #def start_event_loop():
        #raise NotImplementedError

    #def stop_event_loop():
        #raise NotImplementedError

# =============================================================================


class PeerConnectionProtocol(protocol.Protocol):
    def connectionMade(self):
        #log.debug('%s: connectionMade' % self.factory.peer)
        self.factory.peer.handle_connection_made(self)

    def dataReceived(self, data):
        #log.debug('%s: dataReceived' % self.factory.peer)
        self.factory.peer.handle_data_received(data)

    def connectionLost(self, reason):
        pass

    def write(self, data):
        self.transport.write(data)

    def disconnect(self):
        self.transport.loseConnection()


class PeerConnectionFactory(protocol.ClientFactory):
    protocol = PeerConnectionProtocol

    def __init__(self, peer):
        self.peer = peer

    def clientConnectionFailed(self, connector, reason):
        #log.warn('%s: clientConnectionFailed: %s' % (self.peer, reason))
        self.peer.handle_connection_failed()

    def clientConnectionLost(self, connector, reason):
        #log.warn('%s: clientConnectionLost: %s' % (self.peer, reason))
        self.peer.handle_connection_lost()


class ConnectionManagerTwisted():
    @staticmethod
    def connect_peer(peer):
        f = PeerConnectionFactory(peer)
        reactor.connectTCP(peer.ip, peer.port, f)

    @staticmethod
    def start_event_loop():
        reactor.run()

    @staticmethod
    def stop_event_loop():
        reactor.stop()

# =============================================================================


class ConnectionManagerSelect():
    def __init__(self):
        self.sel = selectors.DefaultSelector()
        self.conns = []
        self.loop_active = False

    def connect_peer(self, peer):
        try:
            conn = PeerConnectionSelect(self.sel, peer)
        except PeerConnectionFailed:
            return

        self.conns.append(conn)

    def start_event_loop(self):
        self.loop_active = True
        while self.loop_active:
            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

    def stop_event_loop(self):
        for conn in self.conns:
            conn.disconnect()
        self.loop_active = False


class PeerConnectionSelect():
    def __init__(self, sel, peer):
        log.debug('PeerConnectionSelect.__init__: %s' % peer)
        self.sel = sel
        self.peer = peer
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(2.0)
        try:
            self.sock.connect((peer.ip, peer.port))
        except OSError:
            self.handle_connection_failed()
            raise PeerConnectionFailed

        self.sock.setblocking(False)
        sel.register(self.sock, selectors.EVENT_READ, self.handle_event_read)
        self.peer.handle_connection_made(self)

    def handle_connection_failed(self):
        #log.debug('PeerConnectionSelect.handle_connection_failed')
        self.peer.handle_connection_failed()

    def handle_connection_lost(self):
        #log.debug('PeerConnectionSelect.handle_connection_lost')
        if self.sock:
            self.sock.close()
        self.sock = None
        self.peer.handle_connection_lost()

    def handle_event_read(self, zsock, zmask):
        #log.debug('PeerConnectionSelect.handle_event_read')
        assert(zsock == self.sock)
        try:
            data = self.sock.recv(1024)
        except ConnectionError as e:
            log.error('ConnectionError')
            log.error(e)
            self.handle_connection_lost()
            return

        #if not data:
            #log.error('connection lost: data == b''')
            #self.handle_connection_lost()
            #return

        self.peer.handle_data_received(data)

    def write(self, data):
        #log.debug('PeerConnectionSelect.write: %s' % data)
        # TODO: make this non-blocking
        self.sock.send(data)

    def disconnect(self):
        if self.sock:
            self.sel.unregister(self.sock)
            self.sock.close()
        self.sock = None


class PeerConnectionFailed(Exception):
    pass


# =============================================================================


class ConnectionManagerThreaded():
    def __init__(self):
        pass

    def connect_peer(self, peer):
        pass

    def start_event_loop(self):
        pass

    def stop_event_loop(self):
        pass

# =============================================================================

ConnectionManager = ConnectionManagerTwisted
if concurrency_mode == 'twisted':
    ConnectionManager = ConnectionManagerTwisted
elif concurrency_mode == 'select':
    ConnectionManager = ConnectionManagerSelect
elif concurrency_mode == 'threads':
    ConnectionManager = ConnectionManagerThreaded
