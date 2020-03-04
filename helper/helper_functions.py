def filesize(size):
    """
    Convert bytes to kilobytes, megabytes, etc.
    :param size:
    :return:
    """
    pf = ['Byte', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    i = 0
    while size > 1024:
        i += 1
        size /= 1024
    return "{:.2f}".format(size) + " " + pf[i] + ("s" if size != 1 else "")
