from cryptography.fernet import Fernet
import os
from os.path import exists


def get_raw_key(key_file):
    return read_from_file(key_file)


def get_key(key_file):
    """
    WARNING: New key will be made (and potentially overwrite old file) if key cannot be loaded
    """
    try:
        key = read_from_file(filename=key_file)
        return Fernet(key)
    except Exception as e:
        print("Could not locate encryption key. Creating a new one...")
        key = make_key()
        save_key(key, key_file)
        return Fernet(key)


def split_path(file_path):
    return '/'.join(file_path.split('/')[:-1])


def make_path(file_path):
    working_path = split_path(file_path=file_path)
    if not os.path.exists(working_path):
        os.makedirs(working_path)


def make_key():
    return Fernet.generate_key()


def save_key(key, filename):
    write_to_file(text=key.decode('utf-8'), filename=filename)


def write_to_file(text, filename):
    make_path(file_path=filename)
    f = open(filename, 'w+')
    f.write(text)
    f.close()


def read_from_file(filename):
    with open(filename, 'r') as f:
        text = f.read()
    return text


def backup_file(filename):
    copy_file(filename=filename, new_filename=f'{filename}.bk')


def copy_file(filename, new_filename):
    text = read_from_file(filename=filename)
    write_to_file(text=text, filename=new_filename)


class Encryption:
    def __init__(self, key=None, key_file=None, key_folder=None):
        self.key_folder = key_folder
        if key:
            self.key = Fernet(key)
        self.key_file = key_file
        if self.key_file:
            self.key = get_key(key_file=self.key_file)  # Fernet object

    def exists(self, filename):
        return exists(f"{self.key_folder}/{filename}")

    def encrypt_text(self, text):
        try:
            token = self.key.encrypt(bytes(text, encoding='utf8'))
            # return token.encode('unicode_escape')
            return token.decode('utf-8')
        except:
            pass
        return None

    def encrypt_file(self, text, filename):
        try:
            text = self.encrypt_text(text=text)
            if text:
                write_to_file(text=text, filename=filename)
                return True
        except:
            pass
        return False

    def decrypt_text(self, text):
        try:
            text = self.key.decrypt(bytes(text, encoding='utf8'))
            # return text.encode('unicode_escape')
            return text.decode('utf-8')
        except:
            pass
        return None

    def decrypt_file(self, filename):
        try:
            text = read_from_file(filename=filename)
            return self.decrypt_text(text=text)
        except:
            pass
        return None

    def encrypt_file_in_place(self, filename):
        text = read_from_file(filename=filename)
        os.remove(filename)
        self.encrypt_file(text=text, filename=filename)

    def decrypt_file_in_place(self, filename):
        text = self.decrypt_file(filename=filename)
        os.remove(filename)
        write_to_file(text=text, filename=filename)

    def make_temporary_file(self, permFileName, tempFileName):
        text = read_from_file(filename=permFileName)
        text = self.decrypt_text(text=text)
        write_to_file(text=text, filename=tempFileName)

    def back_to_permanent_file(self, permFileName, tempFileName, deleteTempFile: bool=False):
        text = read_from_file(filename=tempFileName)
        text = self.encrypt_text(text=text)
        write_to_file(text=text, filename=permFileName)
        if deleteTempFile:
            os.remove(tempFileName)