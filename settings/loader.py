def _read_token_from_file():
    file_path = ".token"
    with open(file_path, 'r') as f:
        return f.read()

def get_bot_token():
    return _read_token_from_file()