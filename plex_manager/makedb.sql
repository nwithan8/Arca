CREATE DATABASE PlexDiscord;
USE PlexDiscord;
CREATE TABLE users (DiscordID BIGINT, PlexUsername VARCHAR(100), PlexEmail VARCHAR(100));
#CREATE TABLE regular_users (DiscordID BIGINT, PlexUsername VARCHAR(100));
CREATE USER DiscordBot@localhost IDENTIFIED BY 'DiscordBot';
GRANT ALL PRIVILEGES ON PlexDiscord.* to 'DiscordBot'@'localhost';
