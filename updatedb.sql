USE PlexDiscord;
ALTER TABLE trial_users ADD PlexEmail VARCHAR(320);
ALTER TABLE regular_users ADD PlexEmail VARCHAR(320);
ALTER TABLE regular_users ADD JoinTimestamp INT;
ALTER TABLE regular_users ADD EndOfMonth INT;
ALTER TABLE regular_users ADD SubType VARCHAR(5);
