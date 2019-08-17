CREATE DATABASE JellyfinDiscord;
USE JellyfinDiscord;
CREATE TABLE users (DiscordID BIGINT, JellyfinUsername VARCHAR(100), JellyfinID VARCHAR(100));
#CREATE TABLE regular_users (DiscordID BIGINT, PlexUsername VARCHAR(100));
CREATE USER DiscordBot@localhost IDENTIFIED BY 'DiscordBot';
GRANT ALL PRIVILEGES ON JellyfinDiscord.* to 'DiscordBot'@'localhost';
