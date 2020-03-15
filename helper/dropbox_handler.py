import dropbox
import os
import ntpath

DB_KEY = os.environ.get('DROPBOX_API_KEY')
if DB_KEY:
    dbx = dropbox.Dropbox(DB_KEY)


def download_file(filePath, toWhere=None):
    try:
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
            dbx.files_upload(f.read(), '/{}'.format(rename if rename else filename),
                             mode=dropbox.files.WriteMode('overwrite'))
        print("File uploaded")
        return True
    except Exception as e:
        print(e)
        return False


def check_if_folder_exits(folderPath):
    try:
        dbx.files_get_metadata('/{}'.format(folderPath))
        return True
    except Exception as e:
        print(e)
        return False


def create_folder_path(folderPath):
    """
    Ex. Create /home/2020/Spring folders
    """
    try:
        folders = folderPath.split('/')
        from_root = ""
        for folder in folders:
            if not check_if_folder_exits("{}{}".format(from_root, folder)):
                dbx.files_create_folder("/{}{}".format(from_root, folder))
            from_root += folder + "/"
        return True
    except Exception as e:
        print(e)
        return False
