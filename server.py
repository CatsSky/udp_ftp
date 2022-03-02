import socket
import queue

# queue module provides thread-safe queue implementation
data_queue = queue()


def main():
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.bind(("", 28888)) # all interfaces
    buffer_size = 1024

    print('Server is up and listening')
    while True:
        data, addr = sock.recvfrom(buffer_size)
        print(f'Received Message from {addr}:\n{data}')


if __name__ == "__main__":
    main()
