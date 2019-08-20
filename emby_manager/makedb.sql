CREATE DATABASE EmbyDiscord;
USE EmbyDiscord;
CREATE TABLE users (DiscordID VARCHAR(100), EmbyUsername VARCHAR(100), EmbyID VARCHAR(200), ExpirationStamp INT, Note VARCHAR(5));
CREATE USER DiscordBot@localhost IDENTIFIED BY 'DiscordBot';
GRANT ALL PRIVILEGES ON EmbyDiscord.* to 'DiscordBot'@'localhost';
