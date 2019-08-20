CREATE DATABASE JellyfinDiscord;
USE JellyfinDiscord;
CREATE TABLE users (DiscordID VARCHAR(100), JellyfinUsername VARCHAR(100), JellyfinID VARCHAR(200), ExpirationStamp INT, Note VARCHAR(5));
CREATE USER DiscordBot@localhost IDENTIFIED BY 'DiscordBot';
GRANT ALL PRIVILEGES ON JellyfinDiscord.* to 'DiscordBot'@'%' WITH GRANT OPTION;
