# nwithan8 Cogs

Cog Function

| Name | Status | Description (Click for full details)
| --- | --- | --- |
| espn | 2.1.0 | <details><summary>Get live data from ESPN.com</summary><p>Commands:<p><ul><li><b>score</b> - Get live score(s) for a team</li><li><b>prob</b> - Get ESPN's win probability for a team's current game</li><li><b>sched</b> - Get a team's schedule</li><li><b>stats</b> - Get a team's record and ranking</li><li><b>top</b> - Top ranked teams of a league (Supported: CFB)</li><li><b>leagues</b> - List supported leagues</li></ul><p>Supported leagues: NFL, NBA, MLB, NHL, CFB, CBBM, CBBW</p> |
| plex | 1.6.0 | <details><summary>Interact with a Plex Media Server (via Tautulli)</summary><p>Commands:<p><ul><li><b>size</b> - Get Plex library statistics</li><li><b>stats</b> - Get watch statistics for a specific user</li><li><b>top</b> - Get the most popular media or most active users</li><li><b>rec</b> - Get a recommendation of what to watch</li><li><b>new</b> - Get an interactive catalog of newly-added content</li><li><b>search</b> - Search for Plex content</li><li><b>now</b> - View and manage live Plex streams</li></ul> |
| plex_manager | 2.0.0 | <details><summary>Manage a Plex Media Server</summary><p>Commands:<p><ul><li><b>add</b> - Invite Plex user to Plex server </li><li><b>remove</b> - Remove Plex user from Plex server </li><li><b>import</b> - Import existing Plex users to database</li><li><b>trial</b> - Start a trial of the Plex server</li><li><b>winner</b> - List winner Plex usernames</li><li><b>purge</b> - Remove inactive winners</li><li><b>cleandb</b> - Delete outdated database entries if users were removed manually from Plex</li>li><b>blacklist</b> - Blacklist a Discord user or Plex username</li><li><b>count</b> - Get the number of Plex Friends with access to the Plex server</li><li><b>access</b> - Check if a user has access to the Plex server</li><li><b>find</b> - Find a user based on Plex or Discord username</li><li><b>info</b> - Get database entry for a user</li><li><b>status</b> - Check if Plex is up and running</li></ul> |
| jellyfin_manager | 2.1.1 | <details><summary>Manage a Jellyfin Media Server</summary><p>Commands:<p><ul><li><b>add</b> - Create Jellyfin user </li><li><b>remove</b> - Disable Jellyfin user </li><li><b>import</b> - Import existing Jellyfin users to database</li><li><b>trial</b> - Start a trial of the Jellyfin server</li><li><b>winner</b> - List winner Jellyfin usernames</li><li><b>purge</b> - Remove inactive winners</li><li><b>cleandb</b> - Delete outdated database entries if users were removed manually from Jellyfin</li><li><b>blacklist</b> - Blacklist a Discord user or Jellyfin username</li><li><b>count</b> - Get the number of Jellyfin users with access to the Jellyfin server</li><li><b>access</b> - Check if a user has access to the Jellyfin server</li><li><b>find</b> - Find a user based on Jellyfin or Discord username</li><li><b>info</b> - Get database entry for a user</li><li><b>status</b> - Check if Jellyfin is up and running</li></ul> |
| emby_manager | 2.1.1 | <details><summary>Manage an Emby Media Server</summary><p>Commands:<p><ul><li><b>add</b> - Create Emby user (optionally link to Emby Connect username)</li><li><b>remove</b> - Disable Emby user </li><li><b>import</b> - Import existing Emby users to database</li><li><b>trial</b> - Start a trial of the Emby server</li><li><b>winner</b> - List winner Emby usernames</li><li><b>purge</b> - Remove inactive winners</li><li><b>cleandb</b> - Delete outdated database entries if users were removed manually from Emby</li><li><b>blacklist</b> - Blacklist a Discord user or Emby username</li><li><b>count</b> - Get the number of Emby users with access to the Emby server</li><li><b>access</b> - Check if a user has access to the Emby server</li><li><b>find</b> - Find a user based on Emby or Discord username</li><li><b>info</b> - Get database entry for a user</li><li><b>status</b> - Check if Emby is up and running</li></ul> |
| cog_handler | 0.2.0 | <details><summary>Manage cogs for Discord bot</summary><p>Commands:<p><ul><li><b>enable</b> - Enable cogs without restarting the bot (incompatible with RedBot cogs)</li><li><b>disable</b> - Disable cogs without restarting the bot</li><li><b>restart</b> - Reload a cog without restarting the bot</li><li><b>download</b> - Download cogs from Dropbox</li><li><b>upload</b> - Upload cogs to Dropbox</li><li><b>repo</b> - Clone repos from .git URLs</li></ul> |
| news | 1.0.0 | <details><summary>Get news headlines</summary><p>Commands:<p><ul><li><b>brief</b> - Get 5 top headlines</li><li><b>top</b> - Top headlines from a specific media outlet</li><li><b>sports</b> - Sports news headlines</li><li><b>u.s.</b> - U.S. news headlines</li><li><b>world</b> - World news headlines</li></ul> |
| marta | 1.1.0 | <details><summary>Get MARTA train info</summary><p>MARTA is the Metro Atlanta Rapid Transit Authority, the light-rail system in Atlanta, Georgia</p><p>Commands:<p><ul><li><b>trains</b> - Get live train arrival times</li><li><b>time</b> - How long to go from one station to another</li><li><b>stations</b> - List available stations</li></ul> |
| roles | 1.0.0 | <details><summary>Mass-add and remove Discord roles</summary><p>Commands:<p><ul><li><b>add</b> - Add roles to users</li><li><b>remove</b> - Remove roles from users</li><li><b>list</b> - List available roles to add/remove</li></ul> |
| sengled | 1.0.0 | <details><summary>Control Sengled smart lights</summary><p>Commands:<p><ul><li><b>lights</b> - Toggle light on/off states and brightness</li></ul> |
| wink | 1.0.0 | <details><summary>Control Wink Hub-connected smart lights</summary><p>Commands:<p><ul><li><b>wink</b> - List and toggle device and group on/off states</li><li><b>color</b> - Alter light color</li></ul> |
	
 # Installation
 1. ```git clone https://github.com/nwithan8/nwithan8-cogs.git```
 2. Edit settings in respective 'settings.py' files.
 3. Install required packages with ```pip3 install -r requirements.txt```
 5. Run with ```./bot.py```
 
 ```bot.py``` has some cogs activated by default. Cogs can be deactivated by being commented out.
 
 Individual cogs can also be installed to pre-existing bots as well.
 
 Demo video: https://www.youtube.com/watch?v=6etsv5b0IRs
 
 Setup Tutorial: https://www.youtube.com/watch?v=G0iw7aRXB3M (Note: Setup video is outdated, ignore environmental variables)
 
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
[callmekory](https://github.com/callmekory)

The people in the [r/Discord_Bots server](https://discord.gg/49wYxqk)
