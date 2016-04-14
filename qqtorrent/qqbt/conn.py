"""An event loop for managing concurrent peer network connections.

The peer networking functionality has three entirely entirely separate implementations:
    1. using a custom event loop with select/kqueue/epoll
    2. using Twisted, which is a library that provides everything in (1)
    3. using threads, with a separate thread for each connection to handle the
       blocking I/O, and the event loop reading back results through queues
"""
import logging
import selectors
import socket
import queue
import time
import threading
from twisted.internet import protocol, reactor

log = logging.getLogger(__name__)

concurrency_mode = 'select'
#concurrency_mode = 'twisted'
#concurrency_mode = 'threads'


class ConnectionManagerBase():
    def connect_peer(peer):
        raise NotImplementedError

    def start_event_loop():
        raise NotImplementedError

    def stop_event_loop():
        raise NotImplementedError


class PeerConnectionBase():
    def write(self, data):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

# =============================================================================


class ConnectionManagerSelect():
    def __init__(self):
        self.sel = selectors.DefaultSelector()
        self.conns = []
        self.loop_active = False

    def connect_peer(self, peer):
        try:
            conn = PeerConnectionSelect(self.sel, peer)
        except PeerConnectionFailedError:
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
        self.write_queue = queue.Queue()
        self.connect()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(3.0)
        try:
            self.sock.connect((self.peer.ip, self.peer.port))
        except OSError:
            self.handle_connection_failed()
            raise PeerConnectionFailedError

        self.sock.setblocking(False)
        self.sel.register(
            self.sock, selectors.EVENT_READ, self.handle_event)
        self.peer.handle_connection_made(self)

    def handle_connection_failed(self):
        #log.debug('PeerConnectionSelect.handle_connection_failed')
        self.peer.handle_connection_failed()

    def handle_connection_lost(self):
        #log.debug('PeerConnectionSelect.handle_connection_lost')
        self.disconnect()
        self.peer.handle_connection_lost()

    def handle_event(self, sock, mask):
        assert(sock == self.sock)

        if mask & selectors.EVENT_WRITE:
            self.handle_event_write(mask)
        elif mask & selectors.EVENT_READ:
            self.handle_event_read(mask)
        else:
            raise Exception('Unexpected event mask: %s' % mask)

    def handle_event_read(self, mask):
        #log.debug('PeerConnectionSelect.handle_event_read')
        assert(mask == selectors.EVENT_READ)
        try:
            data = self.sock.recv(4096)
        except ConnectionError:
            self.handle_connection_lost()
            return

        if not data:
            self.handle_connection_lost()
            return

        self.peer.handle_data_received(data)

    def handle_event_write(self, mask):
        #log.debug('PeerConnectionSelect.handle_event_write')
        assert(mask == selectors.EVENT_WRITE)

        try:
            data = self.write_queue.get_nowait()
        except queue.Empty:
            # Disable write events.
            self.sel.modify(self.sock, selectors.EVENT_READ, self.handle_event)
            return

        try:
            self.sock.send(data)
        except BrokenPipeError:
            self.handle_connection_lost()
            return


    def write(self, data):
        #log.debug('PeerConnectionSelect.write: %s' % data)
        self.write_queue.put(data)
        # Enable write events.
        self.sel.modify(
            self.sock, selectors.EVENT_READ|selectors.EVENT_WRITE,
            self.handle_event)

    def disconnect(self):
        if self.sock:
            self.sel.unregister(self.sock)
            self.sock.close()
        self.sock = None


class PeerConnectionFailedError(Exception):
    pass

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


class ConnectionManagerThreaded():
    def __init__(self):
        self.conns = []
        self.loop_active = False

    def connect_peer(self, peer):
        conn = PeerConnectionThreaded(peer)
        self.conns.append(conn)

    def start_event_loop(self):
        self.loop_active = True
        while self.loop_active:
            time.sleep(0)
            for conn in self.conns:
                if not conn.thread.is_alive():
                    continue
                conn.check_events()

    def stop_event_loop(self):
        self.loop_active = False
        for conn in self.conns:
            conn.disconnect()


class PeerConnectionThreaded():
    def __init__(self, peer):
        self.peer = peer
        self.is_stopped = False

        self.receive_queue = queue.Queue()
        self.write_queue = queue.Queue()
        self.connect_event = threading.Event()
        self.disconnect_event = threading.Event()
        self.connection_succeeded = threading.Event()
        self.connection_failed = threading.Event()
        self.connection_lost = threading.Event()

        self.thread = PeerConnectionThreadedThread(self)
        self.thread.start()
        self.connect()

    def check_events(self):
        """Check receive queue and event flags from thread and take actions."""
        if not self.receive_queue.empty():
            try:
                data = self.receive_queue.get_nowait()
            except queue.Empty:
                pass
            else:
                self.handle_data_received(data)

        if self.connection_succeeded.is_set():
            self.connection_succeeded.clear()
            self.handle_connection_succeded()
        if self.connection_failed.is_set():
            self.connection_failed.clear()
            self.handle_connection_failed()
        if self.connection_lost.is_set():
            self.connection_lost.clear()
            self.handle_connection_lost()

    def handle_connection_succeded(self):
        self.peer.handle_connection_made(self)

    def handle_connection_failed(self):
        self.peer.handle_connection_failed()

    def handle_connection_lost(self):
        self.peer.handle_connection_lost()

    def handle_data_received(self, data):
        self.peer.handle_data_received(data)

    def connect(self):
        self.connect_event.set()

    def write(self, data):
        self.write_queue.put(data)

    def disconnect(self):
        self.disconnect_event.set()


class PeerConnectionThreadedThread(threading.Thread):
    def __init__(self, conn):
        self.ip = conn.peer.ip
        self.port = conn.peer.port

        self.receive_queue = conn.receive_queue
        self.write_queue = conn.write_queue
        self.connect_event = conn.connect_event
        self.disconnect_event = conn.disconnect_event
        self.connection_succeeded = conn.connection_succeeded
        self.connection_failed = conn.connection_failed
        self.connection_lost = conn.connection_lost

        threading.Thread.__init__(self)

    def run(self):
        while not self.connect_event.is_set():
            time.sleep(0)
        try:
            self.thread_connect()
        except PeerConnectionFailedError:
            self.connection_failed.set()
            self.sock.close()
            self.sock = None
            return

        while not self.disconnect_event.is_set():
            time.sleep(0)
            self.thread_send()
            self.thread_receive()

        self.sock.close()
        self.sock = None

    def thread_connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(3.0)
        try:
            self.sock.connect((self.ip, self.port))
        except OSError:
            raise PeerConnectionFailedError

        self.sock.setblocking(False)
        self.connection_succeeded.set()

    def thread_send(self):
        while True:
            try:
                data = self.write_queue.get_nowait()

                try:
                    self.sock.send(data)
                except BrokenPipeError:
                    self.thread_handle_connection_lost()
                    return
            except queue.Empty:
                return

    def thread_receive(self):
        try:
            data = self.sock.recv(4096)
        except BlockingIOError:
            return
        except ConnectionError:
            self.thread_handle_connection_lost()
            return

        if not data:
            self.thread_handle_connection_lost()
            return

        self.receive_queue.put(data)

    def thread_handle_connection_lost(self):
        self.connection_lost.set()
        self.disconnect_event.set()


# =============================================================================

if concurrency_mode == 'twisted':
    ConnectionManager = ConnectionManagerTwisted
elif concurrency_mode == 'select':
    ConnectionManager = ConnectionManagerSelect
elif concurrency_mode == 'threads':
    ConnectionManager = ConnectionManagerThreaded
