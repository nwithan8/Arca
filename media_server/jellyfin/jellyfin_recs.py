import discord
import requests
import json
from imdbpie import Imdb, ImdbFacade
import random
from progress.bar import Bar
from media_server.jellyfin import jellyfin_api as jf
from media_server.jellyfin import jellyfin_stats as js
from media_server.jellyfin import settings as settings
from urllib.parse import quote

imdbf = ImdbFacade()
imdb = Imdb()

owner_players = []
emoji_numbers = [u"1\u20e3", u"2\u20e3", u"3\u20e3", u"4\u20e3", u"5\u20e3"]

most_common_letters = ['e', 't', 'a', 'o', 'i', 'n', 't', 's', 'r', 'h', 'l', 'u']

accepted_types = ['movie', 'show', 'tv', 'series', 'episode']


class SmallMediaItem:
    def __init__(self, data):
        self.title = data.get('Name')
        self.year = data.get('ProductionYear')
        self.id = data.get('ItemId')
        self.type = data.get('Type')


def unwatched_by_user_id(history, media_item: SmallMediaItem):
    for item in history:
        if item.itemId == media_item.id:
            return False
    return True


def get_random_item(media_type, check_unwatched_by_user_id: int = None):
    try:
        # can't pull all items ahead of time, so use search hints with a common letter in the alpahbet
        letter_to_search = random.choice(most_common_letters)
        data = jf.search(keyword=letter_to_search, mediaType=media_type)
        if not data:
            return get_random_item(media_type=media_type, check_unwatched_by_user_id=check_unwatched_by_user_id)
        items = [SmallMediaItem(item) for item in data]
        random_item = random.choice(items)
        if check_unwatched_by_user_id:
            user_watch_history = js.getUserHistory(user_id=check_unwatched_by_user_id)
            passed_check = False
            failed_count = 0
            while not passed_check:
                if failed_count > 25:  # the odds of not finding something unwatched after 25 random draws, wow
                    return "All"
                if unwatched_by_user_id(history=user_watch_history, media_item=random_item):
                    passed_check = True
                else:
                    random_item = random.choice(items)
                    failed_count += 1
        return random_item
    except Exception as e:
        print(f'Error in getting random item: {e}')
        return None


def get_poster(embed, title):
    try:
        embed.set_image(url=str(imdbf.get_title(imdb.search_for_title(title)[0]['imdb_id']).image.url))
        return embed
    except Exception as e:
        print("Error in get_poster: {}".format(e))
        return embed


def make_embed(mediaItem):
    server_id = jf.getServerInfo().get('Id')
    if server_id:
        embed = discord.Embed(title=mediaItem.title,
                              url=f'{settings.JELLYFIN_URL}/web/index.html#!/itemdetails.html?id={mediaItem.id}&serverId={server_id}',
                              description=f"Watch it on {settings.JELLYFIN_SERVER_NICKNAME}")
        if mediaItem.type not in ['MusicArtist', 'Album', 'Song']:
            embed = get_poster(embed, mediaItem.title)
        return embed
    return None


def find_rec(username, mediaType, unwatched=False):
    try:
        if unwatched:
            user_id = jf.getUserIdFromUsername(username=username)
            if not user_id:
                return None
            return get_random_item(media_type=mediaType, check_unwatched_by_user_id=user_id)
        else:
            return get_random_item(media_type=mediaType)
    except Exception as e:
        print("Error in find_rec: {}".format(e))
        return False


def make_recommendation(mediaType, unwatched, username=None):
    if unwatched:
        if not username:
            return "Please include a Jellyfin username", None, None
        recommendation = find_rec(username, mediaType, True)
        if not recommendation:
            return "I couldn't find that Jellyfin username", None, None
        if recommendation == 'All':
            return "You've already played everything in that section!", None, None
    else:
        recommendation = find_rec(None, mediaType, False)
    embed = make_embed(recommendation)
    return "How about {}?{}".format(recommendation.title, (
        '\nClick 🎞️ to watch a trailer.' if recommendation.type not in ['MusicArtist', 'Album',
                                                                         'Song'] else "")), embed, recommendation


def get_trailer_URL(mediaItem):
    url = 'https://www.googleapis.com/youtube/v3/search?q={query}&key={key}&part=snippet&type=video'.format(
        query=quote('{} {} trailer'.format(mediaItem.title, ('movie' if mediaItem.type == 'Movie' else 'tv show'))),
        key=settings.YOUTUBE_API_KEY
    )
    result = requests.get(url).json()
    if result and result.get('items'):
        return 'https://www.youtube.com/watch?v={}'.format(result['items'][0]['id']['videoId'])
    return "Sorry, I couldn't grab the trailer."
