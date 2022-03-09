from pathlib import Path
from uftp_client import Client


def main():
    client = Client('127.0.0.1')
    client.connect()
    client.pwd()
    client.cd('../..')
    client.cd('network_programming/udp_ftp')
    client.pwd()

    data = client.get('TODO.md')
    Path('get_TODO.md').write_bytes(data)
    
    

if __name__ == '__main__':
    main()