import dropbox
import os
from dropbox.exceptions import ApiError, AuthError
import ntpath

DB_KEY = os.environ.get('DROPBOX_API_KEY')
dbx = dropbox.Dropbox(DB_KEY)


def download_file(filePath, toWhere=None):
    try:
        print('/{}'.format(filePath))
        if toWhere:
            dbx.files_download_to_file('/{}'.format(filePath), toWhere)
        else:
            dbx.files_download('/{}'.format(filePath))
        return True
    except FileNotFoundError:
        return False


def upload_file(filePath, rename=False):
    try:
        with open(filePath, 'rb') as f:
            print("Uploading {} to Dropbox...".format(filePath))
            if not rename:
                filename = ntpath.basename(filePath)
            dbx.files_upload(f.read(), '/{}'.format(rename if rename else filename), mode=dropbox.files.WriteMode('overwrite'))
        print("File uploaded")
        return True
    except dropbox.exceptions.APIError as e:
        print(e)
        return False
