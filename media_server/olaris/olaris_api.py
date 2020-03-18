import requests
import json
from media_server.olaris import settings as settings

token = ""


class BoolResponse:
    def __init__(self, data):
        self.success = data.get('success')


class CreatePSResponse:
    def __init__(self, data):
        self.success = data.get('success')


class CreateSTResponse:
    def __init__(self, data):
        self.error = Error(data.get('error'))
        self.metadataPath = data.get('metadataPath')
        self.hlsStreamingPath = data.get('hlsStreamPath')
        self.dashStreamingPath = data.get('dashStreamingPath')
        self.jwt = data.get('jwt')
        self.streams = [Stream(stream) for stream in data.get('streams')]


class Episode:
    def __init__(self, data):
        self.name = data.get('name')
        self.overview = data.get('overview')
        self.stillPath = data.get('stillPath')
        self.airDate = data.get('airDate')
        self.episodeNumber = data.get('episodeNumber')
        self.tmdbID = data.get('tmdbID')
        self.uuid = data.get('uuid')
        self.files = [EpisodeFile(episode_file) for episode_file in data.get('files')]
        self.playState = PlayState(data.get('playState'))
        self.season = Season(data.get('season'))


class EpisodeAddedEvent:
    def __init__(self, data):
        self.episode = Episode(data.get('episode'))


class EpisodeFile:
    def __init__(self, data):
        self.fileName = data.get('fileName')
        self.filePath = data.get('filePath')
        self.uuid = data.get('uuid')
        self.streams = [Stream(stream) for stream in data.get('streams')]
        self.totalDuration = data.get('totalDuration')
        self.fileSize = data.get('fileSize')
        # self.library = Library(data.get('library'))


class Error:
    def __init__(self, data):
        self.message = data.get('message')
        self.hasError = data.get('hasError')


class Invite:
    def __init__(self, data):
        self.code = data.get('code')
        self.user = User(data.get('user'))


class Library:
    def __init__(self, data):
        self.id = data.get('id')
        self.kind = data.get('kind')
        self.name = data.get('name')
        self.filePath = data.get('filePath')
        self.isRefreshing = data.get('isRefreshing')
        self.backend = data.get('backend')
        self.rcloneName = data.get('rcloneName')
        self.healthy = data.get('healthy')
        self.movies = [Movie(movie) for movie in data.get('movies')]
        self.episodes = [Episode(episode) for episode in data.get('episodes')]


class LibraryResponse:
    def __init__(self, data):
        self.library = Library(data.get('library'))
        self.error = Error(data.get('Error'))


class MediaItem:
    def __init__(self, data):
        self.item = None
        if data.get('year') and not data.get('firstAirDate'):  # is a movie
            self.item = Movie(data)
        else:
            self.item = Episode(data)


class Movie:
    def __init__(self, data):
        self.name = data.get('name')
        self.title = data.get('title')
        self.year = data.get('year')
        self.overview = data.get('overview')
        self.imdbID = data.get('imdbID')
        self.tmdbID = data.get('tmdbID')
        self.backdropPath = data.get('backdropPath')
        self.posterPath = data.get('posterPath')
        self.uuid = data.get('uuid')
        self.files = [MovieFile(file) for file in data.get('files')]
        self.playState = PlayState(data.get('playState'))


class MovieAddedEvent:
    def __init__(self, data):
        self.movie = Movie(data.get('movie'))


class MovieFile:
    def __init__(self, data):
        self.fileName = data.get('fileName')
        self.filePath = data.get('filePath')
        self.libraryId = data.get('libraryId')
        self.uuid = data.get('uuid')
        self.streams = [Stream(stream) for stream in data.get('streams')]
        self.totalDuration = data.get('totalDuration')
        self.fileSize = data.get('fileSize')
        # self.library = Library(data.get('library'))


class PlayState:
    def __init__(self, data):
        self.finished = data.get('finished')
        self.playtime = data.get('playtime')
        self.uuid = data.get('uuid')


class PlayStateResponse:
    def __init__(self, data):
        self.uuid = data.get('uuid')
        self.playState = PlayState(data.get('playState'))


class Remote:
    def __init__(self, name):
        self.name = name


class SearchItem:
    def __init__(self, data):
        self.item = None
        if data.get('firstAirDate') or data.get('unwatchedEpisodesCount'):  # is a series
            self.item = Series(data)
        else:
            self.item = Movie(data)


class Season:
    def __init__(self, data):
        self.name = data.get('name')
        self.overview = data.get('overview')
        self.seasonNumber = data.get('seasonNumber')
        self.airDate = data.get('airDate')
        self.posterPath = data.get('posterPath')
        self.tmdbID = data.get('tmdbID')
        self.episodes = [Episode(episode) for episode in data.get('episodes')]
        self.uuid = data.get('uuid')
        self.unwatchedEpisodesCount = data.get('unwatchedEpisodesCount')
        self.series = Series(data.get('series'))


class SeasonAddedEvent:
    def __init__(self, data):
        self.season = Season(data.get('season'))


class Series:
    def __init__(self, data):
        self.name = data.get('name')
        self.overview = data.get('overview')
        self.firstAirDate = data.get('firstAirDate')
        self.status = data.get('status')
        self.seasons = [Season(season) for season in data.get('season')]
        self.backdropPath = data.get('backdropPath')
        self.posterPath = data.get('posterPath')
        self.tmdbID = data.get('tmdbID')
        self.type = data.get('type')
        self.uuid = data.get('uuid')
        self.unwatchedEpisodesCount = data.get('unwatchedEpisodesCount')


class SeriesAddedEvent:
    def __init__(self, data):
        self.series = Series(data.get('series'))


class Stream:
    def __init__(self, data):
        self.codecName = data.get('codecName')
        self.codecMime = data.get('codecMime')
        self.profile = data.get('profile')
        self.bitRate = data.get('bitRate')
        self.streamType = data.get('streamType')
        self.language = data.get('language')
        self.title = data.get('title')
        self.resolution = data.get('resolution')
        self.totalDuration = data.get('totalDuration')
        self.streamID = data.get('streamID')
        self.streamURL = data.get('streamURL')


class TmdbMovieSearchItem:
    def __init__(self, data):
        self.title = data.get('title')
        self.releaseYear = data.get('releaseYear')
        self.overview = data.get('overview')
        self.tmdbID = data.get('tmdbID')
        self.backdropPath = data.get('backdropPath')
        self.posterPath = data.get('posterPath')


class TmdbSeriesSearchItem:
    def __init__(self, data):
        self.name = data.get('name')
        self.firstAirYear = data.get('firstAirYear')
        self.tmdbID = data.get('tmdbID')
        self.backdropPath = data.get('backdropPath')
        self.posterPath = data.get('posterPath')


class UpdateEpisodeFileMetadataPayload:
    def __init__(self, data):
        self.error = Error(data.get('error'))


class UpdateMovieFileMetadataPayload:
    def __init__(self, data):
        self.error = Error(data.get('error'))
        self.mediaItem = MediaItem(data.get('mediaItem'))
        self.mediaItem = data.get('mediaItem')


class User:
    def __init__(self, data):
        self.id = data.get('id')
        self.username = data.get('username')
        self.admin = data.get('admin')


class UserInviteResponse:
    def __init__(self, data):
        self.code = data.get('code')
        self.error = Error(data.get('error'))


class UserResponse:
    def __init__(self, data):
        self.user = User(data.get('user'))
        self.error = Error(data.get('error'))


class Directive:
    def __init__(self, data):
        self.name = data.get('name')
        self.description = data.get('description')
        self.locations = [DirectiveLocation(location) for location in data.get('locations')]
        self.args = [InputValue(arg) for arg in data.get('args')]


class EnumValue:
    def __init__(self, data):
        self.name = data.get('name')
        self.description = data.get('description')
        self.isDeprecated = data.get('isDeprecated')
        self.deprecationReason = data.get('deprecationReason')


class Field:
    def __init__(self, data):
        self.name = data.get('name')
        self.description = data.get('description')
        self.args = [InputValue(arg) for arg in data.get('args')]
        self.type = Type(data.get('type'))
        self.isDeprecated = data.get('isDeprecated')
        self.deprecationReason = data.get('deprecationReason')


class InputValue:
    def __init__(self, data):
        self.name = data.get('name')
        self.description = data.get('description')
        self.type = Type(data.get('type'))
        self.defaultValue = data.get('defaultValue')


class Schema:
    def __init__(self, data):
        self.types = [Type(type_data) for type_data in data.get('types')]
        self.queryType = Type(data.get('queryType'))
        self.mutationType = Type(data.get('mutationType'))
        self.subscriptionType = Type(data.get('subscriptionType'))
        self.directives = [Directive(directive) for directive in data.get('directives')]


class Type:
    def __init__(self, data):
        self.kind = TypeKind(data.get('kind'))
        self.name = data.get('name')
        self.description = data.get('description')
        self.fields = [Field(field) for field in data.get('fields')]
        self.interfaces = [Type(interface) for interface in data.get('interfaces')]
        self.possibleTypes = [Type(possibleType) for possibleType in data.get('possibleTypes')]
        self.enumValues = [EnumValue(enumValue) for enumValue in data.get('enumValues')]
        self.inputFields = [InputValue(inputField) for inputField in data.get('inputFields')]
        self.ofType = Type(data.get('ofType'))


class DirectiveLocation:  # limited documentation
    def __init__(self, data):
        pass


class TypeKind:  # limited documentation
    def __init__(self, data):
        pass


def get_jwt():
    try:
        res = requests.post(url='{base}/m/v1/auth'.format(base=settings.OLARIS_URL),
                            json={'username': '{}'.format(settings.ADMIN_USERNAME),
                                  'password': '{}'.format(settings.ADMIN_PASSWORD)})
        if res:
            return res.json()['jwt']
    except Exception as e:
        print(e)
    return None


def post_request(query, type='query'):
    try:
        jwt = get_jwt()
        if jwt:
            data = {'query': query}
            if type == 'mutation':
                data = {'mutation': query}
            if type == 'subscription':
                data = {'subscription': query}
            print(data)
            response = requests.post(url='{base}/m/query?JWT={jwt}'.format(base=settings.OLARIS_URL, jwt=jwt),
                                     json=data)
            if response:
                return response.json()
        else:
            raise Exception("Could not retrieve JWT for request authentication")
    except Exception as e:
        print(e)
    return None


def get_libraries():
    """
    :return: [Library]
    """
    query = """{
        libraries {
            id
            kind
            name
            filePath
            isRefreshing
            backend
            rcloneName
            healthy
            movies {
                name
                title
                year
                overview
                imdbID
                tmdbID
                backdropPath
                posterPath
                uuid
                files {
                    fileName
                    filePath
                    libraryId
                    uuid
                    streams {
                        codecName
                        codecMime
                        profile
                        bitRate
                        streamType
                        language
                        title
                        resolution
                        totalDuration
                        streamID
                        streamURL
                    }
                    totalDuration
                    fileSize
                }
                playState {
                    finished
                    playtime
                    uuid
                }
            }
            episodes {
                name
                overview
                stillPath
                airDate
                episodeNumber
                tmdbID
                uuid
                files {
                    fileName
                    filePath
                    uuid
                    streams {
                        codecName
                        codecMime
                        profile
                        bitRate
                        streamType
                        language
                        title
                        resolution
                        totalDuration
                        streamID
                        streamURL
                    }
                    totalDuration
                    fileSize
                }
                playState {
                    finished
                    playtime
                    uuid
                }
                seasons {
                    name
                    overview
                    seasonNumber
                    airDate
                    posterPath
                    tmdbID
                    uuid
                    unwatchedEpisodesCount
                    series {
                        name
                        overview
                        firstAirDate
                        status
                        backdropPath
                        posterPath
                        tmdbID
                        type
                        uuid
                        unwatchedEpisodesCount
                    }
                }
            }
        }
    }"""
    data = post_request(query=query, type='query')
    print(data)
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on get_libraries")
    else:
        return [Library(library) for library in data['data']['libraries']]


def get_movies(uuid: str = None, offset: int = None, limit: int = None):
    """
    :return: [Movie]
    """
    uuid_filter = ("uuid: {0},".format(uuid) if uuid else "")
    offset_filter = ("offset: {0},".format(offset) if offset else "")
    limit_filter = ("limit: {0},".format(limit) if limit else "")
    query = """{
        movies(""" + uuid_filter + offset_filter + limit_filter + """) {
            name
            title
            year
            overview
            imdbID
            tmdbID
            backdropPath
            posterPath
            uuid
            files {
                fileName
                filePath
                libraryId
                uuid
                streams {
                    codecName
                    codecMime
                    profile
                    bitRate
                    streamType
                    language
                    title
                    resolution
                    totalDuration
                    streamID
                    streamURL
                }
                totalDuration
                fileSize
            }
            playState {
                finished
                playtime
                uuid
            }
        }
    }"""
    data = post_request(query=query, type='query')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on get_movies")
    else:
        return [Movie(movie) for movie in data['data']['movies']]


def get_series(uuid: str = None, offset: int = None, limit: int = None):
    """
    :return: [Series]
    """
    uuid_filter = ("uuid: {0},".format(uuid) if uuid else "")
    offset_filter = ("offset: {0},".format(offset) if offset else "")
    limit_filter = ("limit: {0},".format(limit) if limit else "")
    query = """"{
        series(""" + uuid_filter + offset_filter + limit_filter + """) {
            name
            overview
            firstAirDate
            status
            backdropPath
            posterPath
            tmdbID
            type
            uuid
            unwatchedEpisodesCount
            seasons {
                name
                overview
                seasonNumber
                airDate
                posterPath
                tmdbID
                uuid
                unwatchedEpisodesCount
                episodes {
                    name
                    overview
                    stillPath
                    airDate
                    episodeNumber
                    tmdbID
                    uuid
                    files {
                        fileName
                        filePath
                        uuid
                        streams {
                            codecName
                            codecMime
                            profile
                            bitRate
                            streamType
                            language
                            title
                            resolution
                            totalDuration
                            streamID
                            streamURL
                        }
                        totalDuration
                        fileSize
                    }
                    playState {
                        finished
                        playtime
                        uuid
                    }    
                }
            }    
        }
    }"""
    data = post_request(query=query, type='query')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on get_series")
    else:
        return [Series(series) for series in data['data']['series']]


def get_season(uuid: str = None):
    """
    :return: Season
    """
    uuid_filter = ("uuid: {0},".format(uuid) if uuid else "")
    query = """{
        season(""" + uuid_filter + """) {
            name
            overview
            seasonNumber
            airDate
            posterPath
            tmdbID
            uuid
            unwatchedEpisodesCount
            episodes {
                name
                overview
                stillPath
                airDate
                episodeNumber
                tmdbID
                uuid
                files {
                    fileName
                    filePath
                    uuid
                    streams {
                        codecName
                        codecMime
                        profile
                        bitRate
                        streamType
                        language
                        title
                        resolution
                        totalDuration
                        streamID
                        streamURL
                    }
                    totalDuration
                    fileSize
                }
                playState {
                    finished
                    playtime
                    uuid
                }
            }
            series {
                name
                overview
                firstAirDate
                status
                backdropPath
                posterPath
                tmdbID
                type
                uuid
                unwatchedEpisodesCount
            }
        }
    }"""
    data = post_request(query=query, type='query')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on get_season")
    else:
        return Season(data['data'])


def get_episode(uuid: str = None):
    """
    :return: Episode
    """
    uuid_filter = ("uuid: {0},".format(uuid) if uuid else "")
    query = """{
        episode(""" + uuid_filter + """) {
            name
            overview
            stillPath
            airDate
            episodeNumber
            tmdbID
            uuid
            files {
                fileName
                filePath
                uuid
                streams {
                    codecName
                    codecMime
                    profile
                    bitRate
                    streamType
                    language
                    title
                    resolution
                    totalDuration
                    streamID
                    streamURL
                }
                totalDuration
                fileSize
            }
            playState {
                finished
                playtime
                uuid
            }
            seasons {
                name
                overview
                seasonNumber
                airDate
                posterPath
                tmdbID
                uuid
                unwatchedEpisodesCount
                series {
                    name
                    overview
                    firstAirDate
                    status
                    backdropPath
                    posterPath
                    tmdbID
                    type
                    uuid
                    unwatchedEpisodesCount
                }
            }
        }
    }"""
    data = post_request(query=query, type='query')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on get_episode")
    else:
        return Episode(data['data']['episodes'])


def get_users():
    """
    :return: [User]
    """
    query = """{
        users {
            id
            username
            admin
        }
    }"""
    data = post_request(query=query, type='query')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on get_users")
    else:
        return [User(user) for user in data['data']['users']]


def get_recently_added():
    """
    :return: [MediaItem]
    """
    query = """{
        recentlyAdded {
            __typename
            ... on Movie {
                name
                title
                year
                overview
                imdbID
                tmdbID
                backdropPath
                posterPath
                uuid
                files {
                    fileName
                    filePath
                    libraryId
                    uuid
                    streams {
                        codecName
                        codecMime
                        profile
                        bitRate
                        streamType
                        language
                        title
                        resolution
                        totalDuration
                        streamID
                        streamURL
                    }
                    totalDuration
                    fileSize
                }
                playState {
                    finished
                    playtime
                    uuid
                }
            }
            ... on Episode {
                name
                overview
                stillPath
                airDate
                episodeNumber
                tmdbID
                uuid
                files {
                    fileName
                    filePath
                    uuid
                    streams {
                        codecName
                        codecMime
                        profile
                        bitRate
                        streamType
                        language
                        title
                        resolution
                        totalDuration
                        streamID
                        streamURL
                    }
                    totalDuration
                    fileSize
                }
                playState {
                    finished
                    playtime
                    uuid
                }
                seasons {
                    name
                    overview
                    seasonNumber
                    airDate
                    posterPath
                    tmdbID
                    uuid
                    unwatchedEpisodesCount
                    series {
                        name
                        overview
                        firstAirDate
                        status
                        backdropPath
                        posterPath
                        tmdbID
                        type
                        uuid
                        unwatchedEpisodesCount
                    }
                }
            }
        }
    }"""
    data = post_request(query=query, type='query')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on get_recently_added")
    else:
        print(data)
        return [MediaItem(mediaItem) for mediaItem in data['data']['recentlyAdded']]


def get_up_next():
    """
    :return: [MediaItem]
    """
    query = """{
        upNext {
            __typename
            ... on Movie {
                name
                title
                year
                overview
                imdbID
                tmdbID
                backdropPath
                posterPath
                uuid
                files {
                    fileName
                    filePath
                    libraryId
                    uuid
                    streams {
                        codecName
                        codecMime
                        profile
                        bitRate
                        streamType
                        language
                        title
                        resolution
                        totalDuration
                        streamID
                        streamURL
                    }
                    totalDuration
                    fileSize
                }
                playState {
                    finished
                    playtime
                    uuid
                }
            }
            ... on Episode {
                name
                overview
                stillPath
                airDate
                episodeNumber
                tmdbID
                uuid
                files {
                    fileName
                    filePath
                    uuid
                    streams {
                        codecName
                        codecMime
                        profile
                        bitRate
                        streamType
                        language
                        title
                        resolution
                        totalDuration
                        streamID
                        streamURL
                    }
                    totalDuration
                    fileSize
                }
                playState {
                    finished
                    playtime
                    uuid
                }
                seasons {
                    name
                    overview
                    seasonNumber
                    airDate
                    posterPath
                    tmdbID
                    uuid
                    unwatchedEpisodesCount
                    series {
                        name
                        overview
                        firstAirDate
                        status
                        backdropPath
                        posterPath
                        tmdbID
                        type
                        uuid
                        unwatchedEpisodesCount
                    }
                }
            }
        }
    }"""
    data = post_request(query=query, type='query')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on get_up_next")
    else:
        return [MediaItem(mediaItem) for mediaItem in data['data']]


def search(name: str):
    """
    :return: [SearchItem]
    """
    name_filter = ("name: \"{0}\",".format(name) if name else "")
    query = """{
        search(""" + name_filter + """) {
            __typename
            ... on Movie {
                name
                title
                year
                overview
                imdbID
                tmdbID
                backdropPath
                posterPath
                uuid
                files {
                    fileName
                    filePath
                    libraryId
                    uuid
                    streams {
                        codecName
                        codecMime
                        profile
                        bitRate
                        streamType
                        language
                        title
                        resolution
                        totalDuration
                        streamID
                        streamURL
                    }
                    totalDuration
                    fileSize
                }
                playState {
                    finished
                    playtime
                    uuid
                } 
            }
            ... on Series {
                name
                overview
                firstAirDate
                status
                backdropPath
                posterPath
                tmdbID
                type
                uuid
                unwatchedEpisodesCount
                seasons {
                    name
                    overview
                    seasonNumber
                    airDate
                    posterPath
                    tmdbID
                    uuid
                    unwatchedEpisodesCount
                    episodes {
                        name
                        overview
                        stillPath
                        airDate
                        episodeNumber
                        tmdbID
                        uuid
                        files {
                            fileName
                            filePath
                            uuid
                            streams {
                                codecName
                                codecMime
                                profile
                                bitRate
                                streamType
                                language
                                title
                                resolution
                                totalDuration
                                streamID
                                streamURL
                            }
                            totalDuration
                            fileSize
                        }
                        playState {
                            finished
                            playtime
                            uuid
                        }    
                    }
                }
            }        
        }
    }"""
    data = post_request(query=query, type='query')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on search")
    else:
        return [SearchItem(searchItem) for searchItem in data['data']['search']]


def get_remotes():
    """
    :return: [String]
    """
    query = """{
    remotes
    }"""
    data = post_request(query=query, type='query')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on get_remotes")
    else:
        return [Remote(remote) for remote in data['data']['remotes']]


def get_invites():
    """
    :return: [Invite]
    """
    query = """{
        invites {
            code
            user {
                id
                username
                admin    
            }
        }
    }"""
    data = post_request(query=query, type='query')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on get_invites")
    else:
        return [Invite(invite) for invite in data['data']['invites']]


def get_unidentified_movie_files(offset: int = None, limit: int = None):
    """
    :return: [MovieFile]
    """
    offset_filter = ("offset: {0},".format(offset) if offset else "")
    limit_filter = ("limit: {0},".format(limit) if limit else "")
    query = """{
        unidentifiedMovieFiles(""" + offset_filter + limit_filter + """) {
            fileName
            filePath
            libraryId
            uuid
            streams {
                codecName
                codecMime
                profile
                bitRate
                streamType
                language
                title
                resolution
                totalDuration
                streamID
                streamURL
                }
            totalDuration
            fileSize
        }
    }"""
    data = post_request(query=query, type='query')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on get_unidentified_movie_files")
    else:
        return [MovieFile(movieFile) for movieFile in data['data']['unidentifiedMovieFiles']]


def get_unindentified_episode_files(offset: int = None, limit: int = None):
    """
    :return: [EpisodeFile]
    """
    offset_filter = ("offset: {0},".format(offset) if offset else "")
    limit_filter = ("limit: {0},".format(limit) if limit else "")
    query = """{
        unidentifiedEpisodeFiles(""" + offset_filter + limit_filter + """) {
            fileName
            filePath
            uuid
            streams {
                codecName
                codecMime
                profile
                bitRate
                streamType
                language
                title
                resolution
                totalDuration
                streamID
                streamURL
            }
            totalDuration
            fileSize        
        }
    }"""
    data = post_request(query=query, type='query')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on get_unidentified_episode_files")
    else:
        return [EpisodeFile(episodeFile) for episodeFile in data['data']['unidentifiedEpisodeFiles']]


def tmdb_movie_search(keywords: str):
    """
    :return: [TmdbMovieSearchItem]
    """
    query_filter = ("query: \"{0}\",".format(keywords) if keywords else "")
    query = """{
        tmdbSearchMovies(""" + query_filter + """) {
            title
            releaseYear
            overview
            tmdbID
            backdropPath
            posterPath
        }
    }"""
    data = post_request(query=query, type='query')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on tmdb_movie_search")
    else:
        return [TmdbMovieSearchItem(item) for item in data['data']['tmdbSearchMovies']]


def tmdb_series_search(keywords: str):
    """
    :return: [TmdbSeriesSearchItem]
    """
    query_filter = ("query: \"{0}\",".format(keywords) if keywords else "")
    query = """{
        tmdbSearchSeries(""" + query_filter + """) {
            name
            firstAirYear
            tmdbID
            backdropPath
            posterPath
        }
    }"""
    data = post_request(query=query, type='query')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on tmdb_series_search")
    else:
        return [TmdbSeriesSearchItem(item) for item in data['data']['tmdbSearchSeries']]


def create_library(name: str, filePath: str, kind: int, backend: int, rcloneName: str):
    """
    :return: LibraryResponse
    """
    library_name = ("name: {0},".format(name) if name else "")
    library_filePath = ("filePath: {0},".format(filePath) if filePath else "")
    library_kind = ("kind: {0},".format(kind) if kind else "")
    library_backend = ("backend: {0},".format(backend) if backend else "")
    library_rcloneName = ("rcloneName: {0},".format(rcloneName) if rcloneName else "")
    query = """{
        createLibrary(""" + library_name + library_filePath + library_kind + library_backend + library_rcloneName + """) {
            library
            error
        }
    }"""
    data = post_request(query=query, type='mutation')
    print(data)
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on create_library")
    else:
        return LibraryResponse(data['data'])


def delete_library(id: int):
    """
    :return: LibraryResponse
    """
    id_filter = ("id: {0},".format(id) if id else "")
    query = """{
        deleteLibrary(""" + id_filter + """) {
            
        }
    }"""
    data = post_request(query=query, type='mutation')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on delete_library")
    else:
        return LibraryResponse(data['data'])


def create_user_invite():
    """
    :return: UserInviteResponse
    """
    query = """{
        createUserInvite
    }"""
    data = post_request(query=query, type='mutation')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on create_user_invite")
    else:
        return UserInviteResponse(data['data'])


def create_play_state(uuid: str, finished: bool, playtime: float):
    """
    :return: PlayStateResponse
    """
    state_uuid = ("uuid: {0},".format(uuid) if uuid else "")
    state_finished = ("finished: {0},".format(finished) if finished is not None else "")
    state_playtime = ("playtime: {0},".format(playtime) if playtime else "")
    query = """{
        createPlayState(""" + state_uuid + state_finished + state_playtime + """) {
            
        }
    }"""
    data = post_request(query=query, type='mutation')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on create_play_state")
    else:
        return PlayStateResponse(data['data'])


def create_streaming_ticket(uuid: str):
    """
    :return: CreateSTResponse
    """
    ticket_uuid = ("uuid: {0},".format(uuid) if uuid else "")
    query = """{
        createStreamingTicket(""" + ticket_uuid + """) {
            
        }
    }"""
    data = post_request(query=query, type='mutation')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on create_streaming_ticket")
    else:
        return CreateSTResponse(data['data'])


def delete_user(id: int):
    """
    :return: UserResponse
    """
    user_id = ("id: {0},".format(id) if id else "")
    query = """{
        deleteUser(""" + user_id + """) {
            
        }
    }"""
    data = post_request(query=query, type='mutation')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on delete_user")
    else:
        return UserResponse(data['data'])


def update_streams(uuid: str):
    """
    :return: Boolean
    """
    stream_uuid = ("uuid: {0},".format(uuid) if uuid else "")
    query = """{
        updateStreams(""" + stream_uuid + """) {
            
        }
    }"""
    return post_request(query=query, type='mutation')


def refresh_agent_metadata(libraryID: int, uuid: str):
    """
    :return: Boolean
    """
    library_id = ("libraryID: {0},".format(libraryID) if libraryID else "")
    agent_uuid = ("uuid: {0},".format(uuid) if uuid else "")
    query = """{
        refreshAgentMetadata(""" + library_id + agent_uuid + """) {
            
        }
    }"""
    return post_request(query=query, type='mutation')


def rescan_libraries():
    """
    :return: Boolean
    """
    query = """{
        rescanLibraries
    }"""
    return post_request(query=query, type='mutation')


def update_movie_file_metadata(uuid: str, tmdbID: int):
    """
    :return: UpdateMovieFileMetadataPayload
    """
    metadata_input = _create_movie_file_metadata_input(uuid, tmdbID)
    metadata_input = ("input: {0},".format(metadata_input) if metadata_input else "")
    query = """{
        updateMovieFileMetadata(""" + metadata_input + """) {
            
        }
    }"""
    data = post_request(query=query, type='mutation')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on update_movie_file_metadata")
    else:
        return UpdateMovieFileMetadataPayload(data['data'])


def update_episode_file_metadata(episode_uuid: str, series_uuid: str, tmdbID: int):
    """
    :return: UpdateEpisodeFileMetadataPayload
    """
    metadata_input = _create_episode_file_metadata_input(episode_uuid, series_uuid, tmdbID)
    metadata_input = ("input: {0},".format(metadata_input) if metadata_input else "")
    query = """{
        updateEpisodeFileMetadata(""" + metadata_input + """) {
            
        }
    }"""
    data = post_request(query=query, type='mutation')
    if not data or data.get('errors'):
        if data:
            print(data['errors'])
        raise Exception("Error on update_episode_file_metadata")
    else:
        return UpdateEpisodeFileMetadataPayload(data['data'])


def _create_movie_file_metadata_input(uuid: str, tmdbID: int):
    input_filter = ('movieFileUUID: {0} tmdbID: {1}'.format(uuid, tmdbID))
    return """{""" + input_filter + """}"""


def _create_episode_file_metadata_input(episode_uuid: str, series_uuid: str, tmdbID: int):
    input_filter = ('episodeFileUUID: {0} seriesUUID: {1} tmdbID {2}'.format(episode_uuid, series_uuid, tmdbID))
    return """{""" + input_filter + """}"""
