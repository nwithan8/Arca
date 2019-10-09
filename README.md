# nwithan8 Cogs

Cog Function

| Name | Status | Description (Click for full details)
| --- | --- | --- |
| espn | 2.1.0 | <details><summary>Get live data from ESPN.com</summary><p>Commands:<p><ul><li><b>score</b> - Get live score(s) for a team</li><li><b>prob</b> - Get ESPN's win probability for a team's current game</li><li><b>sched</b> - Get a team's schedule</li><li><b>stats</b> - Get a team's record and ranking</li><li><b>top</b> - Top ranked teams of a league (Supported: CFB)</li><li><b>leagues</b> - List supported leagues</li></ul><p>Supported leagues: NFL, NBA, MLB, NHL, CFB, CBBM, CBBW</p> |
| plex | 1.5.0 | <details><summary>Interact with a Plex Media Server (via Tautulli)</summary><p>Commands:<p><ul><li><b>size</b> - Get Plex library statistics</li><li><b>stats</b> - Get watch statistics for a specific user</li><li><b>top</b> - Get the most popular media or most active users</li><li><b>rec</b> - Get a recommendation of what to watch</li><li><b>new</b> - Get an interactive catalog of newly-added content</li><li><b>search</b> - Search for Plex content</li><li><b>now</b> - View and manage live Plex streams</li></ul> |
| plex_manager | 1.6.0 | <details><summary>Manage a Plex Media Server</summary><p>Commands:<p><ul><li><b>add</b> - Invite Plex user to Plex server (also done by adding a specific emoji to a message)</li><li><b>remove</b> - Remove Plex user from Plex server (also done by removing a specific emoji from a message)</li><li><b>trial</b> - Start a trial of the Plex server</li><li><b>winner</b> - List winner Plex usernames</li><li><b>purge</b> - Remove inactive winners</li><li><b>count</b> - Get the number of Plex Friends with access to the Plex server</li><li><b>access</b> - Check if a user has access to the Plex server</li><li><b>find</b> - Find a user based on Plex or Discord username</li><li><b>info</b> - Get database entry for a user</li><li><b>status</b> - Check if Plex is up and running</li></ul> |
| emby_manager | 1.2.0 | <details><summary>Manage an Emby Media Server</summary><p>Commands:<p><ul><li><b>add</b> - Create local Emby user</li><li><b>remove</b> - Delete local Emby user</li><li><b>count</b> - Get the number of enabled users on the Emby server</li><li><b>find</b> - Lookup a Plex or Discord user</li><li><b>info</b> - Get database entry for a user</li></ul> |
| jellyfin_manager | 1.2.0 | <details><summary>Manage a Jellyfin Media Server</summary><p>Commands:<p><ul><li><b>add</b> - Create Jellyfin user</li><li><b>remove</b> - Delete Jellyfin user</li><li><b>count</b> - Get the number of enabled users on the Jellyfin server</li></ul> |
| core | 0.3.0 | <details><summary>Manage cogs for Discord bot</summary><p>Commands:<p><ul><li><b>import</b> - Import new cogs</li><li><b>add</b> - Add new cog repo (.git links)</li><li><b>load</b> - Load a cog from a downloaded repo</li></ul> |
| news | 1.0.0 | <details><summary>Get news headlines</summary><p>Commands:<p><ul><li><b>brief</b> - Get 5 top headlines</li><li><b>top</b> - Top headlines from a specific media outlet</li><li><b>sports</b> - Sports news headlines</li><li><b>u.s.</b> - U.S. news headlines</li><li><b>world</b> - World news headlines</li></ul> |
| marta | 1.1.0 | <details><summary>Get MARTA train info</summary><p>MARTA is the Metro Atlanta Rapid Transit Authority, the light-rail system in Atlanta, Georgia</p><p>Commands:<p><ul><li><b>trains</b> - Get live train arrival times</li><li><b>time</b> - How long to go from one station to another</li><li><b>stations</b> - List available stations</li></ul> |
	
 # Installation
 1. ```git clone https://github.com/nwithan8/nwithan8-cogs.git```
 2. Set <a href="https://askubuntu.com/questions/58814/how-do-i-add-environment-variables">environmental variables</a> (see allEnv.txt, or individual env.txt in each cog folder)
 3. Install required packages with ```pip3 install -r requirements.txt```
 4. Set up databases with ```mysql -u root -p < makePEJdb.sql```
 5. Run with ```./bot.py```
 
 ```bot.py``` has all cogs activated by default. Cogs can be deactivated by being commented out.
 
 Individual cogs can also be installed to pre-existing bots as well.
 
 Demo video: https://www.youtube.com/watch?v=6etsv5b0IRs
 
 Setup Tutorial: https://www.youtube.com/watch?v=G0iw7aRXB3M
 
 # Usage
 Default bot prefix is ```*```
 Prefix can be changed in ```bot.py```
 
 Type ```*help``` to get overview of installed cogs.
 
 # Contact
Join the #cogs channel on my Discord server:

<div align="center">
	<p>
		<a href="https://discord.gg/ygRDVE9"><img src="https://discordapp.com/api/guilds/472537215457689601/widget.png?style=banner2" alt="" /></a>
	</p>
</div>

I'm also often floating around on other developer Discord servers.

Discord: nwithan8#8438

# Credits
Thanks to the great people in the [r/Discord_Bots server](https://discord.gg/49wYxqk)
