# -*- coding: utf-8 -*-
from __future__ import absolute_import

from twisted.internet.protocol import ServerFactory, Protocol
import os
import struct

SOCKET_PATH = "/tmp/openhbbtvbrowser.socket"

browserclients = []
onCommandReceived = []
onBrowserClosed = []


class ClientConnection(Protocol):
    magic = 987654321
    headerformat = "!III"
    headersize = struct.calcsize(headerformat)

    def __init__(self):
        self.data = b""
        self.datasize = None
        self.cmd = 0

    def dataReceived(self, data):
        self.data += data
        while True:
            if self.datasize is None:
                if len(self.data) < self.headersize:
                    return
                magic, self.cmd, self.datasize = struct.unpack(self.headerformat, self.data[:self.headersize])
                self.data = self.data[self.headersize:]
                if magic != self.magic or self.datasize > 1024 * 1024:
                    self.data = b""
                    self.datasize = None
                    self.transport.loseConnection()
                    return

            if len(self.data) < self.datasize:
                return

            payload = self.data[:self.datasize]
            self.data = self.data[self.datasize:]
            cmd = self.cmd
            self.cmd = 0
            self.datasize = None

            for callback in list(onCommandReceived):
                callback(cmd, payload)

            if not self.data:
                return

    def connectionMade(self):
        if self not in browserclients:
            browserclients.append(self)

    def connectionLost(self, reason):
        if self in browserclients:
            browserclients.remove(self)
        if not browserclients:
            for callback in list(onBrowserClosed):
                callback()


class CommandServer:
    def __init__(self, socket_path=SOCKET_PATH):
        from twisted.internet import reactor
        self.socket_path = socket_path
        self.factory = ServerFactory()
        self.factory.protocol = ClientConnection
        try:
            os.remove(self.socket_path)
        except OSError:
            pass
        self.port = reactor.listenUNIX(self.socket_path, self.factory)

    def close(self):
        global browserclients
        for client in list(browserclients):
            client.transport.loseConnection()
        browserclients = []
        if self.port is not None:
            try:
                self.port.stopListening()
            except Exception:
                pass
            self.port = None
        try:
            os.remove(self.socket_path)
        except OSError:
            pass

    def __del__(self):
        self.close()

    def sendCommand(self, cmd, data=b""):
        if isinstance(data, str):
            data = data.encode("utf-8")
        elif data is None:
            data = b""
        for client in list(browserclients):
            client.transport.write(struct.pack("!III", client.magic, int(cmd), len(data)))
            if data:
                client.transport.write(data)

    def connectedClients(self):
        return len(browserclients)
