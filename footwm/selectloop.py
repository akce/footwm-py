"""
Event loop for client ui's.

Copyright (c) 2014-2016 Akce
"""
# Python standard modules.
import errno
import select
import socket
import time

# Python local modules.
from . import log as loghelp

log = loghelp.make(name=__name__)

class StreamServer(object):

    def __init__(self, address=None, family=socket.AF_INET, newconn=None):
        """ """
        self._address = address or ('localhost', 5555)
        self._family = family
        self._newconn = newconn     # New connection handler.
        self.retry_connect = 5
        self.connected = False

    def connect(self):
        try:
            self._socket = socket.socket(self._family, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind(self._address)
            self._socket.listen(1)
            log.debug('listening address=%s', self._address)
        except socket.error as e:
            log.error(e)
            self.connected = False
        else:
            self.connected = True
        return self.connected

    def close(self):
        self._socket.shutdown(socket.SHUT_RDWR)
        log.debug('closing server socket {}', self._socket)
        self._socket.close()
        self.connected = False
        return True

    def fileno(self):
        """ Implement for select.select. """
        return self._socket.fileno()

    def handle_recv(self):
        """ Accep a new client connection. """
        conn, addr = self._socket.accept()
        log.debug("Accept conn: %s", str(addr))
        self._newconn(conn)
        return True

class ClientMixin(object):

    def __init__(self, receiver, terminal):
        self._receiver = receiver
        self._terminal = terminal
        self._chunk = ''

    def fileno(self):
        """ Implement for select.select. """
        return self._socket.fileno()

    def close(self):
        log.debug('closing %s', self._socket)
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            # Already closed. Do nothing.
            pass
        self._socket.close()
        del self._socket
        self.connected = False

    def handle_recv(self):
        """ Handle read event.
        Return False if error. Socket will be closed and removed from input list.
        """
        chunkstr = str(self._socket.recv(1024), 'utf-8')
        if chunkstr:
            # Check if we've received all the message. Since this is a streaming
            # socket we might need to put outstanding chunks together for a
            # complete message.
            if self._chunk:
                _str = self._chunk + chunkstr
            else:
                _str = chunkstr
            if _str.endswith(self._terminal):
                # We have at least one complete message
                msgs = _str.split(self._terminal)[:-1]   # Ignore the empty message at the end.
                self._chunk = ''
            else:
                # Last message is incomplete.
                x = _str.split(self._terminal)
                if len(x) == 0:
                    # Entire received str is not a complete message, so add it all to chunk.
                    self._chunk += _str
                    msgs = []
                else:
                    # Store the incomplete message, send the rest off for processing.
                    msgs = x[:-1]
                    self._chunk = x[-1]
            for m in msgs:
                #log.debug('received %s', m)
                self._receiver.handle_message(m)
            ret = True
        else:
            ret = False
        return ret

    def post(self, msg):
        """ post a message, don't wait for a response. """
        self._socket.sendall(bytes(msg + self._terminal, 'utf-8'))

class StreamClient(ClientMixin):
    """ Stream client class interfaces with the select loop, and handles message re-assembly and sending. """

    def __init__(self, address=None, family=socket.AF_INET, receiver=None, terminal='\n\n\n'):
        """ Provide either a connected socket (s) or address/family. """
        super().__init__(receiver, terminal)
        self._address = address or ('localhost', 5555)
        self._family = family
        self.retry_connect = 5  # seconds
        self.connected = False

    def connect(self):
        self._socket = socket.socket(self._family, socket.SOCK_STREAM)
        try:
            self._socket.connect(self._address)
        except socket.error:
            self._receiver.disconnected(self)
            self.connected = False
        else:
            self.connected = True

    def close(self):
        super().close()
        self._receiver.disconnected(self)

class StreamRemote(ClientMixin):
    """ Stream connection from remote received by the StreamServer. """

    def __init__(self, sock, receiver=None, terminal='\n\n\n'):
        super().__init__(receiver=receiver, terminal=terminal)
        self._socket = sock
        # For now assume the socket is connected.
        self.connected = True

class EventLoop(object):

    def __init__(self):
        self.inputs = []
        self._select_timeout = None
        # Clients that aren't connected but will retry.
        # deadclients is a map of client object -> reconnect time.
        self._deadclients = {}

    def add_client(self, client, timeout=None):
        # Check if the client is connected, add direct to inputs?
        log.debug('add_client %s connected=%s', client, client.connected)
        if client.connected:
            # XXX Change inputs to a set?
            if client not in self.inputs:
                self.inputs.append(client)
        else:
            # Add the disconnected client to the deadclients retry map.
            try:
                if timeout is None:
                    t = client.retry_connect
                else:
                    t = timeout
            except AttributeError:
                # client has no retry_connect attribute, it's not reconnectable, so don't add it.
                log.debug('drop non-reconnectable %s', client)
            else:
                self._deadclients[client] = time.time() + t

    @staticmethod
    def _eintr_retry(func, *args):
        """restart a system call interrupted by EINTR"""
        while True:
            try:
                return func(*args)
            except OSError as e:
                if e.errno != errno.EINTR:
                    raise

    def serve_forever(self):
        # XXX Maybe use a thread.Signal instead of True?
        # if we have deadclients, then we want to try and connect them straight away.
        if self._deadclients:
            self._select_timeout = 0
        # End the loop if there are no clients left...
        while self.inputs or self._deadclients:
            log.debug('select.timeout=%s inputs=%s deadclients=%s', self._select_timeout, len(self.inputs), len(self._deadclients.keys()))
            readable, _, exceptional = EventLoop._eintr_retry(select.select, self.inputs, [], self.inputs, self._select_timeout)
            for r in readable:
                try:
                    success = r.handle_recv()
                except socket.error as e:
                    success = False
                if success is False:
                    self._remove(r)
            for sock in exceptional:
                self._remove(sock)
            self._connect_deadclients()
            self._reset_select_timeout()
        log.debug('Exiting the main loop, no inputs or deadclients!')

    def _connect_deadclients(self):
        """ Try and (re)connect any dead clients. """
        # XXX Should this connect stuff go in a separate thread?
        log.debug('_connect_deadclients _select_timeout=%s', self._select_timeout)
        for client in list(self._deadclients.keys()):
            retryafter = self._deadclients[client]
            now = time.time()
            if now > retryafter:
                del self._deadclients[client]
                # Try and reconnect the client.
                connected = client.connect()
                if connected is True:
                    # Success, add to inputs list.
                    self.inputs.append(client)
                    log.debug('add connected client %s', client)
                else:
                    # Failed, requeue in deadclients.
                    self.add_client(client)

    def _reset_select_timeout(self):
        if self._deadclients:
            # Set the select timeout to when the next dead client roughly needs to retry connecting.
            nextup = min(self._deadclients.values())
            self._select_timeout = nextup - time.time()
        else:
            if self.inputs:
                # No dead clients, set the timeout to wait for the next input event.
                self._select_timeout = None

    def post(self, message):
        """ Publish to those streams that have a post method, ie, the writable ones. """
        for c in self.inputs:
            try:
                c.post(message)
            except AttributeError:
                pass

    def _remove(self, sock):
        log.debug('_remove %s', sock)
        self.inputs.remove(sock)
        sock.close()
        # Add client for re-connect attempts.
        self.add_client(sock)

    def shutdown(self):
        for x in self.inputs:
            self._remove(x)
