#!/sbin/python

from pathlib import Path
import socket
import queue
import hashlib
import math
import threading
import multiprocessing
import time


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

class Server:

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 28888))  # all interfaces
        self.buffer_size = 508
        self.reserve_size = 80
        self.message_sze = self.buffer_size - self.reserve_size
        self.connection: str = ""
        self.session_pwd: Path = Path('.')

        # queue module provides thread-safe queue implementation
        self.data_queue = queue.Queue()

        self.listener_process = multiprocessing.Process(target=self.listener_task)
        self.listener_process.start()


    def __del__(self):
        self.close()

    def send(self, cip: str, data: bytes):
        addr = cip, 28889
        self.sock.sendto(data, addr)

    def sendFile(self, file_path: Path):
        file = file_path.read_bytes()
        self.send(self.connection, file)

    def listener_task(self):
        try:
            while True:
                data, addr = self.sock.recvfrom(self.buffer_size)
                self.data_queue.put((data, addr))
        except Exception as e:
            print(e)
            print('Listener thread terminated')

    def receive(self):
        data, addr = self.data_queue.get()
        # print(f'Received Message from {addr}:\n{data}')
        return data, addr

    def receiveFile(self, digest: str, file_size: int):
        chunkNum = math.ceil(file_size / self.message_sze)
        chunks = dict()
        
        while len(chunks) != chunkNum:
            data = self.listenFrom(self.connection)
            recvDigest = data[:64].decode()
            if recvDigest != digest:
                continue
            idx = int.from_bytes(data[64:68], 'big')
            size = int.from_bytes(data[68:72], 'big')
            chunk = data[72:]
            chunks[idx] = chunk

            print(f'Received chunk {idx}')
            print(f'Total {len(chunks)} out of {chunkNum} chunks')
            print(f'Chunk size: {size}')

        self.send(self.connection, b'OK')
        file = b''.join(chunks.values())

        return file
        
        
        
    def listenFrom(self, ip: str):
        while True:
            data, (cip, cport) = self.receive()
            if cip != self.connection:
                continue
            return data

    def waitForConnection(self):
        while True:
            data, addr = self.receive()
            if data == b'CONNECT':
                self.connection = addr[0]
                print(f'Connection established with {addr}')
                return

    def pwd(self, data: list[bytes]):
        path = self.session_pwd.absolute().as_posix()
        self.send(self.connection, path.encode())

    def ls(self, data: list[bytes]):
        print(f'Listing directory {self.session_pwd}')
        files = ' '.join((fd.relative_to(self.session_pwd).as_posix()
                         for fd in self.session_pwd.glob('*'))).encode()
        self.send(self.connection, files)

    def cd(self, data: list[bytes]):
        path: str = data[1].decode()
        new_path = (self.session_pwd / path).resolve()
        if new_path.is_dir():
            self.session_pwd = new_path
        else:
            print(f'{new_path} is not a directory')

    def get(self, data: list[bytes]):
        path = data[1].decode()
        file_path = (self.session_pwd / path).resolve()
        if file_path.is_file():
            print(f'Sending {file_path}')
            file = file_path.read_bytes()
            self.send(self.connection, file)
        else:
            print(f'{file_path} does not exist')

    def put(self, data: list[bytes]):
        filename = data[1].decode()
        digest = data[2].decode()
        file_size = int(data[3].decode())
        file_path = (self.session_pwd / filename).resolve()
        print(f'Receiving {file_path}')
        print(f'Digest: {digest} | File size: {file_size}')

        file = self.receiveFile(digest, file_size)
        file_path.write_bytes(file)
        # response = b'OK' + b'\x00' + digest.encode()
        # self.send(self.connection, response)


    def start(self):
        while True:
            self.session_pwd = Path('.')
            self.waitForConnection()
            while True:
                data, (cip, cport) = self.receive()
                if cip != self.connection:
                    print(f'{cip} is not connected to this server')
                    continue

                if data == b'EXIT':
                    print(f'Session with {cip} closed')
                    break

                data = data.split(b'\x00')

                try:
                    getattr(self, data[0].decode().lower())(data)
                except Exception as e:
                    print(e)
                    print('Invalid command')
                    continue

    def close(self):
        print('Closing server')
        self.sock.close()
        self.listener_process.terminate()


def main():
    server = Server()
    try:
        server.start()
    except KeyboardInterrupt:
        server.close()


if __name__ == '__main__':
    main()
