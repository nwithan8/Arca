from cryptography.fernet import Fernet
import os
from os.path import exists


def getKey(key_file):
    """
    WARNING: New key will be made (and potentially overwrite old file) if key cannot be loaded
    """
    try:
        key = open(key_file, 'r').read()
        return Fernet(key)
    except Exception as e:
        key = makeKey()
        saveKey(makeKey(), key_file)
        return Fernet(key)


def makeKey():
    return Fernet.generate_key()


def saveKey(key, filename):
    f = open(filename, 'w+')
    f.write(key.decode('utf-8'))
    f.close()


class Encryption:
    def __init__(self, key_file):
        self.key_file = key_file
        self.key = getKey(self.key_file)

    def encryptText(self, text):
        token = self.key.encrypt(bytes(text))
        return token.encode('unicode_escape')

    def decryptText(self, text):
        text = self.key.decrypt(bytes(text))
        return text.encode('unicode_escape')

    def encryptFile(self, text, filename):
        text = self.encryptText(text)
        f = open(filename, 'w+')
        f.write(text)
        f.close()

    def decryptFile(self, file):
        f = open(file, 'r')
        return self.decryptText(f.read())

    def makeTemporaryFile(self, permFileName, tempFileName):
        perm = open(permFileName, 'r')
        text = self.decryptText(perm.read())
        perm.close()
        temp = open(tempFileName, 'w+')
        temp.write(text)
        temp.close()

    def backToPermFile(self, permFileName, tempFileName, deleteTempFile=False):
        temp = open(tempFileName, 'r')
        text = self.encryptText(temp.read())
        temp.close()
        perm = open(permFileName, 'w+')
        perm.write(text)
        perm.close()
        if deleteTempFile:
            os.remove(tempFileName)
