import socket
import queue

# queue module provides thread-safe queue implementation
data_queue = queue()

def send(sock: socket, addr: tuple, data: bytearray):
    sock.sendto(data, addr)

def worker():
    pass


def main():
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    udp_host, udp_port = socket.gethostname(), 28888
    addr = udp_host, udp_port

    msg = b"Hello Python!"
    send(sock, addr, msg)

    sock.close()

if __name__ == "__main__":
    main()