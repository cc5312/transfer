import socket

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.serialization import PublicFormat

from utils import *


def receive(conf, receive_port, filename):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print('Listening on 0.0.0.0:{}'.format(receive_port))
    sock.bind(("0.0.0.0", int(receive_port)))
    sock.listen()
    print('waiting connections')
    conn, client_address = sock.accept()
    print("connection accepted, sending public key...")
    pk = get_public_key(conf)
    conn.sendall(pk.public_bytes(Encoding.PEM, PublicFormat.PKCS1))
    print("Public key sent. Receiving encrypted_shared_key...")
    # First 32 bits are the shared key:
    encrypted_shared_key = conn.recv(
        256)  # chacha20 key, but encrypted with a 2048bit RSA key, so the size is 256 bytes
    if len(encrypted_shared_key) == 0:
        print("empty shared key received. Exiting...")
        exit(1)
    key = decrypt_shared_key(conf, encrypted_shared_key)
    chacha20 = ChaCha20Poly1305(key)
    print("receiving file size...")
    filesize = int.from_bytes(conn.recv(8), byteorder='big')
    print("file size is {} bytes".format(filesize))

    print("Receiving encrypted chunks and decrypting them on {}...".format(filename))
    with open(filename, 'wb') as f:
        i = 0
        data = b''
        while filesize > 0:
            print("{} bytes remaining".format(filesize))
            while len(data) < BLOCK_SIZE:
                newdata = conn.recv(BLOCK_SIZE)  # Encrypted size is CHUNK_SIZE + 16
                data += newdata
                if len(newdata) == 0:
                    break
            if len(data) > 0:
                print("decrypting package of size {}...".format(len(data[:BLOCK_SIZE])))
                decrypted = chacha20.decrypt(i.to_bytes(12, byteorder="big"), data[:BLOCK_SIZE], None)
                f.write(decrypted)
                filesize -= len(decrypted)
                i += 1
                data = data[BLOCK_SIZE:]
    print("done!")
    conn.close()
