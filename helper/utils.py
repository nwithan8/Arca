import string
import random
import time


def humanbitrate(B, d=1):
    # 'Return the given kilobytes as a human friendly kbps, mbps, gbps, or tbps string'
    # Next line altered so that this takes in kilobytes instead of bytes, as it was originally written
    B = float(B) * 1024
    KB = float(1024)
    MB = float(KB ** 2)  # 1,048,576
    GB = float(KB ** 3)  # 1,073,741,824
    TB = float(KB ** 4)  # 1,099,511,627,776

    if d <= 0:
        if B < KB:
            return '{0} bps'.format(int(B))
        elif KB <= B < MB:
            return '{0:d} kbps'.format(int(B / KB))
        elif MB <= B < GB:
            return '{0:d} Mbps'.format(int(B / MB))
        elif GB <= B < TB:
            return '{0:d} Gbps'.format(int(B / GB))
        elif TB <= B:
            return '{0:d} Tbps'.format(int(B / TB))
    else:
        if B < KB:
            return '{0} bps'.format(B)
        elif KB <= B < MB:
            return '{0:d} kbps'.format(int(B / KB), nd=d)
        elif MB <= B < GB:
            return '{0:.{nd}f} Mbps'.format(B / MB, nd=d)
        elif GB <= B < TB:
            return '{0:.{nd}f} Gbps'.format(B / GB, nd=d)
        elif TB <= B:
            return '{0:.{nd}f} Tbps'.format(B / TB, nd=d)


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


def is_positive_int(n):
    return n.isdigit()


def password(length):
    """
    Generate a random string of letters and digits
    """
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def timestamp_x_days_from_now(days: int):
    return int(time.time()) + (days * 24 * 60 * 60)


def timestamp_x_hours_from_now(hours: int):
    return int(time.time()) + (hours * 60 * 60)


def timestamp_x_minutes_from_now(minutes: int):
    return int(time.time()) + (minutes * 60)


def timestamp_x_seconds_from_now(seconds: int):
    return int(time.time()) + seconds


class StatusCode:
    def __init__(self, message: str, number: int):
        self.message = message
        self.code = number


class StatusCodes:
    USER_ON_BLACKLIST = StatusCode("User is on the blacklist", 999)
    USER_NOT_ON_PLEX = StatusCode("User does not exist on Plex", 700)


class StatusResponse:
    def __init__(self, success: bool = None, code: int = None, issue: str = None, attachment=None,
                 status_code: StatusCode = None):
        self.success = success
        if status_code:
            self.code = status_code.code
            self.issue = status_code.message
        else:
            self.code = code
            self.issue = issue
        self.attachment = attachment

    def __bool__(self):
        return self.success
