#!/sbin/python

import socket
import queue
from pathlib import Path
import hashlib
import math
import time
import threading


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

class Client:

    def __init__(self, sip: str):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.sock.bind(("", 28889)) # all interfaces
        self.buffer_size = 508
        self.reserve_size = 80
        self.message_sze = self.buffer_size - self.reserve_size
        self.connection: str = sip

        # queue module provides thread-safe queue implementation
        self.data_queue = queue.Queue()

    def __del__(self):
        self.close()

    def send(self, sip: str, data: bytes):
        addr = sip, 28888
        self.sock.sendto(data, addr)

    def sendFile(self, file: bytes):
        digest = hashlib.sha256(file).hexdigest().encode()
        messages = [*chunks(file, self.message_sze)]
        for idx, chunk in enumerate(messages):
            data = digest + idx.to_bytes(4, 'big') + len(chunk).to_bytes(4, 'big') + chunk
            self.send(self.connection, data)
            time.sleep(1e-9) # weird workaround for buffer overflow
            
        res = self.waitForResponse()
        if res == b'OK':
            print('File sent successfully')


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

    def put(self, filepath: str):
        file = Path(filepath).read_bytes()
        digest = hashlib.sha256(file).hexdigest().encode()
        filename = Path(filepath).name
        print(f'File: {filename} | Digest: {digest} | File Size: {len(file)}')
        data = b'PUT\x00' + filename.encode() + b'\x00' + digest + b'\x00' + str(len(file)).encode()
        self.send(self.connection, data)
        
        self.sendFile(file)
        

    def connect(self):
        self.send(self.connection, b'CONNECT')

    def disconnect(self):
        self.send(self.connection, b'EXIT')

    def close(self):
        self.disconnect()
        self.sock.close()


