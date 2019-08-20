CREATE DATABASE JellyfinDiscord;
USE JellyfinDiscord;
CREATE TABLE users (DiscordID BIGINT, JellyfinUsername VARCHAR(100), JellyfinID VARCHAR(100), ExpirationStamp INT, Note VARCHAR(5));
CREATE USER DiscordBot@localhost IDENTIFIED BY 'DiscordBot';
GRANT ALL PRIVILEGES ON JellyfinDiscord.* to 'DiscordBot'@'localhost';
