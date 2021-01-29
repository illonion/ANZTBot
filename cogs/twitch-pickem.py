from discord.ext import commands
from discord import Embed
from resources import is_channel
from settings import twitchannel, clientID, clientSecret
import twitch
import asyncio
from datetime import datetime


class TwitchAndPickemsCog(commands.Cog):
    delete_delay = 10
    twitchAPI_delay = 22

    def __init__(self, bot):
        self.bot = bot
        self.client = twitch.TwitchHelix(client_id=clientID, client_secret=clientSecret, scopes=[twitch.constants.OAUTH_SCOPE_ANALYTICS_READ_EXTENSIONS])
        bot.loop.create_task(self.check_if_live())

    async def cog_before_invoke(self, ctx):
        await ctx.message.channel.trigger_typing()

    async def check_if_live(self):
        await self.bot.wait_until_ready()
        # Give the error reporting cog a few seconds to do what's in it's on_ready listener before it's ready to handle errors
        await asyncio.sleep(5)
        while True:
            try:
                self.client.get_oauth()
                data = self.client.get_streams(user_logins=[twitchannel])
                live = str(data) != '[]'
                # print("Live") if live else print("Offline")
                if live:
                    data = data[0]
                    # Determine if we should ping people based on our last saved stream start time
                    stream_start = data['started_at']
                    with open('last_stream_start.txt', 'r') as f:
                        last_stream_start = datetime.fromisoformat(f.read())
                    # print("Stream started at: " + str(stream_start))
                    # print("Last ping at: " + str(last_stream_start))
                    # print('------------------------------------')
                    if last_stream_start < stream_start:
                        await self.do_stream_ping(data)
                        with open('last_stream_start.txt', 'w') as f:
                            f.write(str(stream_start))
                        # print("Pinged")
            except Exception:
                errorcog = self.bot.get_cog('ErrorReportingCog')
                await errorcog.on_error('anzt.twitch.loop')
            await asyncio.sleep(self.twitchAPI_delay)

    async def do_stream_ping(self, data):
        for guild in self.bot.guilds:
            url = f'https://www.twitch.tv/{data["user_name"]}'
            embed = Embed(title=f'**{data["title"]}**', url=url, color=0x9146ff)
            embed.set_author(name=f'{data["user_name"]} is live!',
                             url=url, icon_url='https://www.iconsdb.com/icons/preview/red/circle-xxl.png')
            # embed.set_thumbnail(url='https://i.imgur.com/XbO4hoK.png')
            embed.set_image(url='https://static-cdn.jtvnw.net/previews-ttv/live_user_osuanzt-960x540.jpg')

            pingrole = [role for role in guild.roles if role.name == 'Stream Ping'][0]
            await pingrole.edit(mentionable=True)
            await guild.system_channel.send(f'{pingrole.mention}', embed=embed)
            await pingrole.edit(mentionable=False)

    @commands.command()
    @is_channel('bot')
    async def pickemping(self, ctx):
        await self.toggle_role(ctx, 'Pickem Ping')

    @commands.command()
    @is_channel('bot')
    async def streamping(self, ctx):
        await self.toggle_role(ctx, 'Stream Ping')

    async def toggle_role(self, ctx, rolename):
        pingrole = [role for role in ctx.guild.roles if role.name == rolename][0]
        if pingrole in ctx.author.roles:
            await ctx.author.remove_roles(pingrole)
            await ctx.send(f'{ctx.author.mention}, Removed your `{rolename}` role.')
        else:
            await ctx.author.add_roles(pingrole)
            await ctx.send(f'{ctx.author.mention}, Gave you the `{rolename}` role.')


def setup(bot):
    bot.add_cog(TwitchAndPickemsCog(bot))