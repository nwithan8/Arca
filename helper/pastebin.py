import os
import json
import base64
import zlib
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

expiration_options = ["5min", "10min", "1hour", "1day", "1week", "1month", "1year", "never"]


def _json_encode(d):
    return json.dumps(d, separators=(',', ':')).encode('utf-8')


def _base58_encode(v):
    # 58 char alphabet
    alphabet = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    alphabet_len = len(alphabet)

    if isinstance(v, str) and not isinstance(v, bytes):
        v = v.encode('ascii')

    nPad = len(v)
    v = v.lstrip(b'\0')
    nPad -= len(v)

    l = 0
    for (i, c) in enumerate(v[::-1]):
        if isinstance(c, str):
            c = ord(c)
        l += c << (8 * i)

    string = b''
    while l:
        l, idx = divmod(l, alphabet_len)
        string = alphabet[idx:idx + 1] + string

    return (alphabet[0:1] * nPad + string)


#
# The encryption format is described here:
# https://github.com/PrivateBin/PrivateBin/wiki/Encryption-format
#
def _privatebin_encrypt(paste_passphrase,
                        paste_password,
                        paste_plaintext,
                        paste_formatter,
                        paste_attachment_name,
                        paste_attachment,
                        paste_compress,
                        paste_burn,
                        paste_opendicussion):
    if paste_password:
        paste_passphrase += bytes(paste_password, 'utf-8')

    # PBKDF
    # kdf_salt = get_random_bytes(8)
    kdf_salt = bytes(os.urandom(8))
    kdf_iterations = 100000
    kdf_keysize = 256  # size of resulting kdf_key

    backend = default_backend()
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(),
                     length=int(kdf_keysize / 8),  # 256bit
                     salt=kdf_salt,
                     iterations=kdf_iterations,
                     backend=backend)
    kdf_key = kdf.derive(paste_passphrase)

    # AES-GCM
    adata_size = 128

    # cipher_iv = get_random_bytes(int(adata_size / 8))
    cipher_iv = bytes(os.urandom(int(adata_size / 8)))
    cipher_algo = "aes"
    cipher_mode = "gcm"

    compression_type = "none"
    if paste_compress:
        compression_type = "zlib"

    # compress plaintext
    paste_data = {'paste': paste_plaintext}
    if paste_attachment_name and paste_attachment:
        paste_data['attachment'] = paste_attachment
        paste_data['attachment_name'] = paste_attachment_name
        print(paste_attachment_name)
        print(paste_attachment)

    if paste_compress:
        zobj = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        paste_blob = zobj.compress(_json_encode(paste_data)) + zobj.flush()
    else:
        paste_blob = _json_encode(paste_data)

    # Associated data to authenticate
    paste_adata = [
        [
            base64.b64encode(cipher_iv).decode("utf-8"),
            base64.b64encode(kdf_salt).decode("utf-8"),
            kdf_iterations,
            kdf_keysize,
            adata_size,
            cipher_algo,
            cipher_mode,
            compression_type,
        ],
        paste_formatter,
        int(paste_opendicussion),
        int(paste_burn),
    ]

    paste_adata_json = _json_encode(paste_adata)

    aesgcm = AESGCM(kdf_key)
    ciphertext = aesgcm.encrypt(cipher_iv, paste_blob, paste_adata_json)

    # Validate
    # aesgcm.decrypt(cipher_iv, ciphertext, paste_adata_json)

    paste_ciphertext = base64.b64encode(ciphertext).decode("utf-8")

    return paste_adata, paste_ciphertext


def _privatebin_send(paste_url,
                     paste_password,
                     paste_plaintext,
                     paste_formatter,
                     paste_attachment_name,
                     paste_attachment,
                     paste_compress,
                     paste_burn,
                     paste_opendicussion,
                     paste_expire):
    paste_passphrase = bytes(os.urandom(32))
    # paste_passphrase = get_random_bytes(32)

    paste_adata, paste_ciphertext = _privatebin_encrypt(paste_passphrase,
                                                        paste_password,
                                                        paste_plaintext,
                                                        paste_formatter,
                                                        paste_attachment_name,
                                                        paste_attachment,
                                                        paste_compress,
                                                        paste_burn,
                                                        paste_opendicussion)

    # json payload for the post API
    # https://github.com/PrivateBin/PrivateBin/wiki/API
    payload = {
        "v": 2,
        "adata": paste_adata,
        "ct": paste_ciphertext,
        "meta": {
            "expire": paste_expire,
        }
    }

    # http content type
    headers = {'X-Requested-With': 'JSONHttpRequest'}

    r = requests.post(paste_url,
                      data=_json_encode(payload),
                      headers=headers)
    r.raise_for_status()

    try:
        result = r.json()
    except:
        return False, 'Error parsing JSON: {}'.format(r.text)

    paste_status = result['status']
    if paste_status:
        paste_message = result['message']
        return False, "Error getting status: {}".format(paste_message)

    paste_id = result['id']
    paste_url_id = result['url']
    paste_deletetoken = result['deletetoken']

    return {'url': '{}{}#{}'.format(paste_url, paste_url_id, _base58_encode(paste_passphrase).decode("utf-8")),
            'delete': '{}/?pasteid={}&deletetoken={}'.format(paste_url, paste_id, paste_deletetoken)}, None


def privatebin(text, url='https://privatebin.net', pass_protect=False, expiration='never', burn_after_reading=False):
    paste_url = url
    paste_formatter = 'plaintext'
    paste_compress = True
    paste_opendicussion = 0
    paste_burn = 0
    paste_password = None
    paste_attachment_name = None
    paste_attachment = None

    if not text:
        return False, "You did not provide any text to send to {}".format(url)

    if expiration not in expiration_options:
        return False, "Incorrect how_long option. Options: '{}'".format("', '".join(expiration_options))

    if burn_after_reading:
        paste_burn = 1

    if pass_protect:
        paste_password = pass_protect

    return _privatebin_send(paste_url,
                            paste_password,
                            text,
                            paste_formatter,
                            paste_attachment_name,
                            paste_attachment,
                            paste_compress,
                            paste_burn,
                            paste_opendicussion,
                            expiration)


def hastebin(text, url='https://hastebin.com'):
    try:
        post = requests.post('{}/documents'.format(url), data=text.encode('utf-8'))
        data = {'url': '{}/{}'.format(url, post.json()['key'])}
        return data, None
    except Exception as e:
        print(e)
        return None, e
