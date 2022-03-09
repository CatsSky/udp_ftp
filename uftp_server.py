#!/sbin/python

from pathlib import Path
import socket
import queue

# queue module provides thread-safe queue implementation
data_queue = queue.Queue()


class Server:

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.sock.bind(("", 28888)) # all interfaces
        self.buffer_size = 1024
        self.connection: str = None
        self.pwd: Path = Path('.')

    def __del__(self):
        self.close()

    def send(self, cip: tuple, data: bytearray):
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

    def close(self):
        self.sock.close()
        

    def start(self):
        while True:
            self.pwd = Path('.')
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

                if data[0] == b'PWD':
                    data = self.pwd.absolute().as_posix().encode()
                    self.send(self.connection, data)

                elif data[0] == b'LS':
                    print(f'Listing directory {self.pwd}')
                    data = ' '.join((fd.relative_to(self.pwd).as_posix() for fd in self.pwd.glob('*'))).encode()
                    self.send(self.connection, data)

                elif data[0] == b'CD':
                    path: str = data[1].decode()
                    new_path = (self.pwd / path).resolve()
                    if new_path.is_dir():
                        self.pwd = new_path
                    else:
                        print(f'{new_path} is not a directory')
                        break
                
                elif data[0] == b'GET':
                    path: str = data[1].decode()
                    file_path = (self.pwd / path).resolve()
                    if file_path.is_file():
                        print(f'Sending {file_path}')
                        data = file_path.read_bytes()
                        self.send(self.connection, data)
                    else:
                        print(f'{file_path} does not exist')
                        break
                    
            
    


def main():
    server = Server()
    server.start()


if __name__ == '__main__':
    main()
