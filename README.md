<h2 align=center>
<img src="https://i.imgur.com/Ds4qF7F.png" width=64 height=64 valign=middle>ANZTBot</h2>

<p align=center><i>A Discord bot made for the ANZT Discord server to assist with the running of <a href="https://osu.ppy.sh/home">osu!</a> tournaments.</i></p>

## Features:
### Match result reporting
See [`match-result-posting.py`](cogs/match-result-posting.py) for implementation.

The feature is triggered by the match ID being posted in our referee's channel.<br>It fetches data from Google Sheets and the osu! API.

![Screenshot of bot's message in discord](images/match-result.png)

### Twitch channel ping
See [`twitch-pickem.py`](cogs/twitch-pickem.py) for implementation.

Includes a command to opt-in or out of receiving these pings by giving or removing the relevant discord role.

![Screenshot of bot's message in discord](images/stream-ping.png)

### Discord Error reporting
See [`error-reporting.py`](cogs/error-reporting.py) for implementation.

Pings a set user in a set channel for uncaught errors providing a full traceback and context.

![Screenshot of bot's message in discord](images/error-report.png)

## Requirements
See [`requirements.txt`](requirements.txt) for specific packages.

The following can be set in the [`settings.py`](settings_template.py) file.
- A Discord bot's token. See [`discord.py`'s documentation](https://discordpy.readthedocs.io/en/latest/discord.html)
- A Google service account's credentials to read spreadsheets. See [`gpsread`'s documentation](https://gspread.readthedocs.io/en/latest/oauth2.html) which also applies to `gspread_asyncio`
- A Twitch Application's ID and secret. See [`python-twitch-client`'s documentation](https://python-twitch-client.readthedocs.io/en/latest/#authentication).
- ~PostgreSQL database credentials for the qualifier lobbies feature~

## Important
If you want to use this bot, you'll have to host it yourself and adapt the code to your use-case. Some coding knowledge will be required.
