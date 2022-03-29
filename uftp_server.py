#!/sbin/python

from pathlib import Path
import socket
import queue
import hashlib
import math
import threading
import time
from typing import Mapping


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

class Server:

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 28888))  # all interfaces
        self.buffer_size = 2048
        self.reserve_size = 80
        self.message_sze = self.buffer_size - self.reserve_size
        self.connection: str = ""
        self.session_pwd: Path = Path('.')

        # queue module provides thread-safe queue implementation
        self.data_queues: dict[str, queue.Queue] = dict()

        self.listener_thread = threading.Thread(target=self.listener_task)
        self.listener_thread.start()


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
                if addr[0] not in self.data_queues:
                    self.data_queues[addr[0]] = queue.Queue()
                self.data_queues[addr[0]].put(data)
        except Exception as e:
            print(e.with_traceback)
            print('Listener thread terminated')

    # def receive(self):
    #     data, addr = self.data_queue.get()
    #     return data, addr

    def receiveFile(self, digest: bytes, file_size: int):
        chunkNum = math.ceil(file_size / self.message_sze)
        chunks: list[bytes] = []

        idx = 0

        while len(chunks) != chunkNum:
            data = self.listenFrom(self.connection)
            if data[0:4] != b'FILE':
                print(f'Invalid file chunk received')
                print(f'content: {data}')
                continue
            recvDigest = data[5:69]
            if recvDigest != digest:
                print(f'File integrity check failed')
                print(f'Expected: {digest} | Received: {recvDigest}')
                continue
            chunkIdx = int.from_bytes(data[69:73], 'big')
            if chunkIdx != idx:
                print(f'Invalid chunk index received')
                print(f'Expected: {idx} | Received: {chunkIdx}')
                response = b'RE\x00' + digest + b'\x00' + idx.to_bytes(4, 'big')
                self.send(self.connection, response)
                self.data_queues[self.connection] = queue.Queue()
                time.sleep(0.005)
                continue

            size = int.from_bytes(data[73:77], 'big')
            chunk = data[77:77 + size]
            chunks.append(chunk)
            idx += 1
            
                
        
        # while len(chunks) != chunkNum:
        #     data = self.listenFrom(self.connection)
        #     recvDigest = data[5:69].decode()
        #     if recvDigest != digest:
        #         continue
        #     idx = int.from_bytes(data[69:73], 'big')
        #     size = int.from_bytes(data[73:77], 'big')
        #     chunk = data[77:]
        #     chunks[idx] = chunk

            # print(f'Received chunk {idx}')
            # print(f'Total {len(chunks)} out of {chunkNum} chunks')
            # print(f'Chunk size: {size}')

        self.send(self.connection, b'OK')
        file = b''.join(chunks)

        return file
        
        
        
    def listenFrom(self, ip: str):
        while True:
            if self.data_queues[ip].empty():
                continue
            return self.data_queues[ip].get()

    def waitForConnection(self):
        while True:
            for cip in self.data_queues:
                data = self.listenFrom(cip)
                
                if data == b'CONNECT':
                    self.connection = cip
                    print(f'Connection established with {cip}')
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
        digest = data[2]
        file_size = int(data[3].decode())
        file_path = (self.session_pwd / filename).resolve()
        print(f'Receiving {file_path}')
        print(f'Digest: {digest} | File size: {file_size}')

        file = self.receiveFile(digest, file_size)

        # File integraty check
        if hashlib.sha256(file).hexdigest() != digest:
            print(f'File {filename} integrity check failed')
            response = b'FAIL\x00' + digest
            self.send(self.connection, response)
            return
        
        print(f'File integrity check passed')
        file_path.write_bytes(file)
        response = b'OK' + b'\x00' + digest
        self.send(self.connection, response)


    def start(self):
        while True:
            self.session_pwd = Path('.')
            self.waitForConnection()
            while True:
                data = self.listenFrom(self.connection)
                if data == b'EXIT':
                    print(f'Session with {self.connection} closed')
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
        print('Waiting for listener thread to terminate')
        self.listener_thread.join(timeout=0.0)


def main():
    server = Server()
    try:
        server.start()
    except KeyboardInterrupt:
        server.close()


if __name__ == '__main__':
    main()
