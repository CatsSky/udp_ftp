#!/sbin/python

from re import T
import socket
import queue

# queue module provides thread-safe queue implementation
data_queue = queue.Queue()


class Client:

    def __init__(self, sip: str):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.sock.bind(("", 28889)) # all interfaces
        self.buffer_size = 1024
        self.connection: str = sip

    def send(self, sip: tuple, data: bytearray):
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

    def close(self):
        self.disconnect()
        self.sock.close()

    def connect(self):
        self.send(self.connection, b'CONNECT')

    def disconnect(self):
        self.send(self.connection, b'EXIT')

    def __del__(self):
        self.close()


def main():
    client = Client("127.0.0.1")
    client.connect()
    pwd = client.pwd()
    print(pwd)
    ls = client.ls()
    print(ls)
    client.cd("../..")
    print(client.ls())

if __name__ == "__main__":
    main()