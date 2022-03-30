#!/sbin/python

import socket
import queue
from pathlib import Path
import hashlib
import math
import time
import threading
from StoppableThread import StoppableThread

def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

class Client:

    def __init__(self, sip: str):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.sock.bind(("", 28889)) # all interfaces
        self.buffer_size = 2048
        self.reserve_size = 128
        self.message_sze = self.buffer_size - self.reserve_size
        self.connection: str = sip

        # queue module provides thread-safe queue implementation
        self.data_queue = queue.Queue()

        self.listener_thread = StoppableThread(target=self.listener_task)
        self.listener_thread.start()

    def __del__(self):
        self.close()

    
    def listener_task(self):
        ct: StoppableThread = threading.current_thread()
        try:
            while True:
                if ct.stopEvent.is_set():
                    return

                data, addr = self.sock.recvfrom(self.buffer_size)
                if addr[0] != self.connection:
                    continue

                # checksum validation
                if hashlib.md5(data[0:-16]).digest() != data[-16:]:
                    print(f'Invalid checksum for {data}')
                    print(f'Expected: {hashlib.md5(data[0:-16]).digest()} | Received: {data[-16:]}')
                    continue

                data = data[0:-16]

                self.data_queue.put(data)

        except Exception as e:
            print(e.with_traceback)
            print('Listener thread terminated')
            return

    def send(self, sip: str, data: bytes):
        addr = sip, 28888

        # Add checksum to data
        data = data + hashlib.md5(data).digest()
        
        self.sock.sendto(data, addr)

    def sendStartFrom(self, messages: list[bytes], digest: bytes, start: int):
        ct: StoppableThread = threading.current_thread()
        for idx in range(start, len(messages)):
            if ct.stopEvent.is_set():
                return

            chunk = messages[idx]
            data = b'FILE\x00' + digest + idx.to_bytes(4, 'big') + len(chunk).to_bytes(4, 'big') + chunk
            self.send(self.connection, data)
            time.sleep(0.0015) # rate limiting
            # TODO: flowrate control and congestion control

    def sendFile(self, file: bytes):
        digest = hashlib.sha256(file).hexdigest().encode()
        messages = [*chunks(file, self.message_sze)]

        send_thread = StoppableThread(target=self.sendStartFrom, args=(messages, digest, 0))
        send_thread.start()

        last_resend_idx = 0
        last_resend_time = 0.0

        while True:
            data = self.receive()
            dataList = data.split(b'\x00')
            if dataList[0] == b'OK':
                print('File sent successfully')
                break
            if dataList[0] == b'RE' and dataList[1] == digest:
                idx = int.from_bytes(data[69:], byteorder='big')
                if last_resend_idx == idx and time.monotonic() - last_resend_time < 0.005:
                    # do not resend if duplicate RE is received and timout has not yet met
                    continue

                last_resend_idx = idx
                last_resend_time = time.monotonic()

                print(f'Resend packet stream from {idx}')
                send_thread.stop()
                send_thread.join()
                send_thread = StoppableThread(target=self.sendStartFrom, args=(messages, digest, idx))
                send_thread.start()
        
        send_thread.stop()
        send_thread.join()
        
        print('File sent successfully')


    def receive(self):
        return self.data_queue.get()

    def receiveFile(self, digest: bytes, file_size: int):
        chunkNum = math.ceil(file_size / self.message_sze)
        chunks: list[bytes] = []

        idx = 0

        while len(chunks) != chunkNum:
            data = self.receive()
            if data[0:4] != b'FILE':
                print(f'Invalid file chunk received')
                print(f'content: {data}')
                continue
            recvDigest = data[5:69]
            if recvDigest != digest:
                print(f'File packet is not expected')
                print(f'Expected: {digest} | Received: {recvDigest}')
                continue
            chunkIdx = int.from_bytes(data[69:73], 'big')
            if chunkIdx != idx:
                print(f'Invalid chunk index received')
                print(f'Expected: {idx} | Received: {chunkIdx}')
                response = b'RE\x00' + digest + b'\x00' + idx.to_bytes(4, 'big')
                self.send(self.connection, response)
                self.data_queue = queue.Queue()
                time.sleep(0.005)
                continue

            size = int.from_bytes(data[73:77], 'big')
            chunk = data[77:77 + size]
            chunks.append(chunk)
            idx += 1

        file = b''.join(chunks)
        print(f'File rceived. Total of {len(chunks)} chunks')

        return file

    def pwd(self):
        self.send(self.connection, b'PWD')
        return self.receive().decode()
    
    def ls(self):
        self.send(self.connection, b'LS')
        return self.receive().decode()
    
    def cd(self, path: str):
        self.send(self.connection, b'CD\x00' + path.encode())

    def get(self, path: str):
        self.send(self.connection, b'GET\x00' + path.encode())

        res = self.receive().split(b'\x00')
        filename = res[1].decode()
        digest = res[2]
        file_size = int(res[3].decode())
        file_path = (Path('.') / filename).resolve()
        print(f'Receiving {file_path}')
        print(f'Digest: {digest} | File size: {file_size}')

        file = self.receiveFile(digest, file_size)

        # File integraty check
        if hashlib.sha256(file).hexdigest() != digest.decode():
            print(f'File {filename} integrity check failed')
            response = b'FAIL\x00' + digest
            self.send(self.connection, response)
            return
        
        print(f'File integrity check passed')
        file_path.write_bytes(file)
        response = b'OK' + b'\x00' + digest
        self.send(self.connection, response)

        file_path.write_bytes(file)

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
        print('Stopping listener thread')
        self.listener_thread.stop()
        self.listener_thread.join()

