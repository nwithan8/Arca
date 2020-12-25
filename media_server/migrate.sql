BEGIN TRANSACTION;

ATTACH DATABASE 'plex/PlexDiscord.db' AS old_plex;
CREATE TABLE IF NOT EXISTS plex (
DiscordID VARCHAR(100) NOT NULL,
plex_username VARCHAR(100) NOT NULL,
Email VARCHAR(100),
ExpirationStamp INT(11),
WhichPlexServer INT(11),
WhichTautServer INT(11),
PayMethod VARCHAR(5),
SubType VARCHAR(5)
);
INSERT INTO plex(DiscordID, plex_username, Email, ExpirationStamp, WhichPlexServer, WhichTautServer, PayMethod, SubType) SELECT DiscordID, plex_username, email, ExpirationStamp, whichPlexServer, whichTautServer, method, Note FROM old_plex.users;

ATTACH DATABASE 'jellyfin/JellyfinDiscord.db' AS old_jellyfin;
CREATE TABLE IF NOT EXISTS jellyfin (
DiscordID VARCHAR(100) NOT NULL,
JellyfinUsername VARCHAR(100),
JellyfinID VARCHAR(200) NOT NULL,
ExpirationStamp INT(11),
PayMethod VARCHAR(5),
SubType VARCHAR(5)
);
INSERT INTO jellyfin(DiscordID, JellyfinUsername, JellyfinID, ExpirationStamp, SubType) SELECT DiscordID, JellyfinUsername, JellyfinID, ExpirationStamp, Note FROM old_jellyfin.users;

ATTACH DATABASE 'emby/EmbyDiscord.db' AS old_emby;
CREATE TABLE IF NOT EXISTS emby (
DiscordID VARCHAR(100) NOT NULL,
EmbyUsername VARCHAR(100),
EmbyID VARCHAR(200) NOT NULL,
ExpirationStamp INT(11),
PayMethod VARCHAR(5),
SubType VARCHAR(5)
);
INSERT INTO emby(DiscordID, EmbyUsername, EmbyID, ExpirationStamp, SubType) SELECT DiscordID, EmbyUsername, EmbyID, ExpirationStamp, Note FROM old_emby.users;

ATTACH DATABASE 'blacklist.db' AS old_blacklist;
CREATE TABLE IF NOT EXISTS blacklist(IDorUsername VARCHAR(200));
INSERT INTO blacklist(IDorUsername) SELECT id_or_username FROM old_blacklist.blacklist;

COMMIT;
