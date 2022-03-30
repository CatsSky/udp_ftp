#!/sbin/python

from pathlib import Path
from uftp_client import Client


def main():
    client = Client('127.0.0.1')
    client.connect()
    client.pwd()
    client.cd('test')
    client.pwd()

    # data = client.put('../../../../Downloads/t14s_gen2_x13_gen2_hmm_en.pdf')
    # data = client.put('uftp_client.py')
    client.put('random10m')
    # data = client.get('random10m')

    client.close()
    
    

if __name__ == '__main__':
    main()