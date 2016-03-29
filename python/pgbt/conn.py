import logging
from twisted.internet import protocol, reactor

log = logging.getLogger(__name__)


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


def connect_peer(peer):
    f = PeerConnectionFactory(peer)
    reactor.connectTCP(peer.ip, peer.port, f)


def start_event_loop():
    reactor.run()


def stop_event_loop():
    reactor.stop()
