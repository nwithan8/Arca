#CREATE DATABASE PlexDiscord;
USE PlexDiscord;
CREATE TABLE users (DiscordID BIGINT, PlexUsername VARCHAR(100), PlexEmail VARCHAR(100), ExpirationStamp INT);
#CREATE TABLE regular_users (DiscordID BIGINT, PlexUsername VARCHAR(100));
#CREATE USER plexbot@localhost IDENTIFIED BY 'plexbot';
#GRANT ALL PRIVILEGES ON PlexDiscord.* to 'plexbot'@'localhost';
