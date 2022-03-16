#!/sbin/python

from pathlib import Path
import socket
import queue
import hashlib

# queue module provides thread-safe queue implementation
data_queue = queue.Queue()


class Server:

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 28888))  # all interfaces
        self.buffer_size = 1024
        self.connection: str = ""
        self.session_pwd: Path = Path('.')

    def __del__(self):
        self.close()

    def send(self, cip: str, data: bytes):
        addr = cip, 28889
        self.sock.sendto(data, addr)

    def receive(self):
        data, addr = self.sock.recvfrom(self.buffer_size)
        print(f'Received Message from {addr}:\n{data}')
        return data, addr

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
        fingerprint = data[2].decode()
        file_path = (self.session_pwd / filename).resolve()
        print(f'Receiving {file_path}')
        data_queue.put(file_path)
        response = b'OK' + b'\x00' + fingerprint.encode()
        self.send(self.connection, response)

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
        self.sock.close()


def main():
    server = Server()
    server.start()


if __name__ == '__main__':
    main()
