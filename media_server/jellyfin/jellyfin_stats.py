from media_server.jellyfin import settings as settings
from media_server.jellyfin import jellyfin_api as jf


class HistoryItem:  # use results from *
    def __init__(self, data):
        self.date = data[0]
        self.userId = data[1]
        self.itemId = data[2]
        self.itemType = data[3]
        self.itemName = data[4]
        self.method = data[5]
        self.client = data[6]
        self.device = data[7]
        self.durationSeconds = data[8]


def getUserHistory(user_id, past_x_days: int = 0, sum_watch_time: bool = False):
    sql_statement = f"SELECT {'SUM(PlayDuration)' if sum_watch_time else '*'} FROM PlaybackActivity WHERE UserId = '{user_id}'"
    if past_x_days:
        sql_statement += f" AND DateCreated >= date(julianday(date('now'))-14)"
    query = {
        "CustomQueryString": sql_statement,
        "ReplaceUserId": "false"}
    data = jf.statsCustomQuery(query)
    if not data:
        if sum_watch_time:
            return 0
        return None
    if sum_watch_time:
        return data['results'][0][0]
    history = [HistoryItem(item) for item in data['results']]
    return history
