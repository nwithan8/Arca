CREATE DATABASE EmbyDiscord;
USE EmbyDiscord;
CREATE TABLE users (DiscordID BIGINT, EmbyUsername VARCHAR(100), EmbyID VARCHAR(100), ExpirationStamp INT, Note VARCHAR(5));
CREATE USER DiscordBot@localhost IDENTIFIED BY 'DiscordBot';
GRANT ALL PRIVILEGES ON EmbyDiscord.* to 'DiscordBot'@'localhost';
