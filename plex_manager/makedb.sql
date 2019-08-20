CREATE DATABASE PlexDiscord;
USE PlexDiscord;
CREATE TABLE users (DiscordID BIGINT, PlexUsername VARCHAR(100), PlexEmail VARCHAR(100), ExpirationStamp INT, Note VARCHAR(5));
CREATE USER DiscordBot@localhost IDENTIFIED BY 'DiscordBot';
GRANT ALL PRIVILEGES ON PlexDiscord.* to 'DiscordBot'@'localhost';
