import base64
import hashlib
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KEY_LEN = 32
IV_LEN = 16


def evp_bytes_to_key(
    password: bytes, salt: bytes, key_len=KEY_LEN, iv_len=IV_LEN
) -> tuple[bytes, bytes]:
    """Derives the key and the IV from the password and the salt using evp_bytes_to_key function"""
    dtot = hashlib.md5(password + salt).digest()
    d = [dtot]
    while len(dtot) < (iv_len + key_len):
        d.append(hashlib.md5(d[-1] + password + salt).digest())
        dtot += d[-1]
    return dtot[:key_len], dtot[key_len : key_len + iv_len]


def pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    """Pad the certificate data with PKCS#7"""
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len] * pad_len)


def pkcs7_unpad(data: bytes) -> bytes:
    """Unpad the decrypted data with PKCS#7"""
    pad_len = data[-1]
    return data[:-pad_len]


def openssl_encrypt_encode(password: bytes, cert_file: str) -> bytes:
    """
    Defines a function that encrypts and encodes the password using a certificate file and OpenSSL and Base64 encoding
    """
    with open(cert_file, "rb") as f:
        cert_data = f.read()

    # Generate a random salt of 8 bytes.
    salt = os.urandom(8)

    key, iv = evp_bytes_to_key(password, salt)

    # Create a cipher object using AES-256 in CBC mode with the derived key and IV
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())

    padded_data = pkcs7_pad(cert_data)

    # Encrypt the padded data using the cipher object
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    # Encode the encrypted data in base64
    encoded_data = base64.b64encode(encrypted_data)

    # Return the encoded data with the salt as prefix
    return salt + encoded_data


def openssl_decrypt_decode(password: bytes, encoded_data: bytes) -> bytes:
    """Defines a function that decrypts and decodes a file with OpenSSL and base64"""
    # Extract the salt from the first 8 bytes of the encoded data
    salt = encoded_data[:8]

    # Decode the rest of the encoded data from base64
    encrypted_data = base64.b64decode(encoded_data[8:])

    key, iv = evp_bytes_to_key(password, salt)

    # Create a cipher object using AES-256 in CBC mode with the derived key and IV
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())

    # Decrypt the encrypted data using the cipher object
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

    unpadded_data = pkcs7_unpad(decrypted_data)

    # Return the original certificate data
    return unpadded_data
