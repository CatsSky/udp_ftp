#!/sbin/python

import socket
import queue
from pathlib import Path

# queue module provides thread-safe queue implementation
data_queue = queue.Queue()


class Client:

    def __init__(self, sip: str):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.sock.bind(("", 28889)) # all interfaces
        self.buffer_size = 1024
        self.connection: str = sip

    def __del__(self):
        self.close()

    def send(self, sip: str, data: bytes):
        addr = sip, 28888
        self.sock.sendto(data, addr)

    def receive(self):
        data, addr = self.sock.recvfrom(self.buffer_size)
        print(f'Received Message from {addr}:\n{data}')
        return data, addr

    def waitForResponse(self):
        while True:
            data, addr = self.receive()
            if addr[0] == self.connection:
                return data

    def pwd(self):
        self.send(self.connection, b'PWD')
        return self.waitForResponse().decode()
    
    def ls(self):
        self.send(self.connection, b'LS')
        return self.waitForResponse().decode()
    
    def cd(self, path: str):
        self.send(self.connection, b'CD\x00' + path.encode())

    def get(self, path: str):
        self.send(self.connection, b'GET\x00' + path.encode())
        data = self.waitForResponse()
        return data

    def put(self, data: bytearray):
        self.send(self.connection, b'PUT\x00' + data)

    def connect(self):
        self.send(self.connection, b'CONNECT')

    def disconnect(self):
        self.send(self.connection, b'EXIT')

    def close(self):
        self.disconnect()
        self.sock.close()


