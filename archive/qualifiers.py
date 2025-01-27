from discord.ext import commands
from resources import is_channel, send_typing, connpool, is_staff


class QualifiersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @is_channel('qualifiers')
    @send_typing
    @commands.cooldown(1, 6, BucketType.channel)
    async def lobby(self, ctx, lobby_id: int):
        await ctx.message.delete()
        id = ctx.author.id
        async with connpool.acquire() as conn:
            async with conn.transaction():
                player = await conn.fetchrow('''select * from players where discord_id=$1''', id)
                if player is None:
                    await ctx.send(f'{ctx.author.mention} You don\'t appear to be registered for this tourney', delete_after=10)
                    return
                lobby = await conn.fetchrow('''select * from lobbies where lobby_id=$1''', lobby_id)
                if lobby is None:
                    await ctx.send(f'{ctx.author.mention} I can\'t find a lobby with id {lobby_id}', delete_after=10)
                    return
                lobby_signup = await conn.fetchrow('''select * from lobby_signups where osu_id=$1''', player['osu_id'])

                try:
                    # Signing up to a new lobby
                    if lobby_signup is None:
                        await conn.execute('''insert into lobby_signups values ($1, $2)''', player['osu_id'], lobby_id)
                        await ctx.send(f'{ctx.author.mention} Added you to lobby {lobby_id}', delete_after=10)
                    # Removing themselves from the lobby they are in
                    elif lobby_signup['lobby_id'] == lobby_id:
                        await conn.execute('''delete from lobby_signups where osu_id=$1''', player['osu_id'])
                        await ctx.send(f'{ctx.author.mention} Removed you from lobby {lobby_id}', delete_after=10)
                    # Switching lobbies
                    else:
                        await conn.execute('''update lobby_signups set lobby_id=$1 where osu_id=$2''', lobby_id, player['osu_id'])
                        await ctx.send(f'{ctx.author.mention} Switched you to lobby {lobby_id}', delete_after=10)
                except asyncpg.exceptions.RaiseError:
                    await ctx.send(f'{ctx.author.mention} Lobby {lobby_id} is full', delete_after=10)
        await self.update_lobbies(ctx)

    @commands.command()
    @is_channel('qualifiers')
    @commands.has_permissions(administrator=True)
    @send_typing
    @commands.cooldown(1, 6, BucketType.channel)
    async def signup(self, ctx, osu_username: str, lobby_id: int):
        await ctx.message.delete()
        async with connpool.acquire() as conn:
            async with conn.transaction():
                player = await conn.fetchrow('''select * from players where osu_username ilike $1''', osu_username)
                if player is None:
                    await ctx.send(f'{ctx.author.mention} Couldn\'t find a user named {osu_username}', delete_after=10)
                    return
                lobby = await conn.fetchrow('''select * from lobbies where lobby_id=$1''', lobby_id)
                if lobby is None:
                    await ctx.send(f'{ctx.author.mention} I can\'t find a lobby with id {lobby_id}', delete_after=10)
                    return
                lobby_signup = await conn.fetchrow('''select * from lobby_signups where osu_id=$1''', player['osu_id'])

                try:
                    # Signing up to a new lobby
                    if lobby_signup is None:
                        await conn.execute('''insert into lobby_signups values ($1, $2)''', player['osu_id'], lobby_id)
                        await ctx.send(f'{ctx.author.mention} Added {osu_username} to lobby {lobby_id}', delete_after=10)
                    # Removing them from the lobby they are in
                    elif lobby_signup['lobby_id'] == lobby_id:
                        await conn.execute('''delete from lobby_signups where osu_id=$1''', player['osu_id'])
                        await ctx.send(f'{ctx.author.mention} Removed {osu_username} from lobby {lobby_id}', delete_after=10)
                    # Switching lobbies
                    else:
                        await conn.execute('''update lobby_signups set lobby_id=$1 where osu_id=$2''', lobby_id, player['osu_id'])
                        await ctx.send(f'{ctx.author.mention} Switched {osu_username} to lobby {lobby_id}', delete_after=10)
                except asyncpg.exceptions.RaiseError:
                    await ctx.send(f'{ctx.author.mention} Lobby {lobby_id} is full', delete_after=10)
        await self.update_lobbies(ctx)

    @commands.command()
    @is_channel('qualifiers')
    @is_staff()
    @send_typing
    async def placeholders(self, ctx):
        await ctx.message.delete()
        # remove previous messages
        async with connpool.acquire() as conn:
            async with conn.transaction():
                messages = await conn.fetch('''select message_id from persistent_messages''')
                for message in messages:
                    try:
                        i = await ctx.channel.fetch_message(message['message_id'])
                        await i.delete()
                    except discord.NotFound:
                        pass
                await conn.execute('''delete from persistent_messages''')

        dates = [date(2020, 7, 10), date(2020, 7, 11), date(2020, 7, 12)]
        thumbnail_urls = ['https://i.imgur.com/Of7Z8pD.png', 'https://i.imgur.com/7Gochmd.png', 'https://i.imgur.com/EzpZz0k.png']
        ids = []
        # send the placeholder messages
        for _ in dates:
            message = await ctx.send(embed=discord.Embed(description='placeholder'))
            ids.append(message.id)
        message = await ctx.send(embed=discord.Embed(description='Use `!lobby #` to sign up for, switch to or leave a lobby E.g. !lobby 5\nAll times are in AEST (UTC+10) | @Diony in another channel for bot problems'))
        ids.append(message.id)
        # store the placeholder messages
        async with connpool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany('''insert into persistent_messages values ($1, $2, $3)''', list(zip(ids, dates, thumbnail_urls)))
                await conn.execute('''insert into persistent_messages (message_id) values ($1)''', ids[-1])

    @commands.command()
    @is_channel('qualifiers')
    @send_typing
    @commands.cooldown(1, 20, BucketType.channel)
    async def refresh(self, ctx):
        await ctx.message.delete()
        await self.update_lobbies(ctx)

    async def update_lobbies(self, ctx):
        async with connpool.acquire() as conn:
            async with conn.transaction():
                messages = await conn.fetch('''select * from persistent_messages;''')
                lobbies = await conn.fetch('''select * from lobbies;''')
                signups = await conn.fetch('''select osu_username, lobby_id from players natural join lobby_signups;''')
                staff = await conn.fetch('''select * from staff''')
        # message records that have a day associated will contain information about lobbies on that day.
        messages = [message for message in messages if message['day'] is not None]
        messages.sort(key=lambda x: x['day'])
        for i in messages:
            message = await ctx.channel.fetch_message(i['message_id'])
            lobbies_for_message = [record for record in lobbies if record['time'].date() == i['day']]
            lobbies_for_message.sort(key=lambda x: x['time'])

            embed = discord.Embed(color=discord.Colour(0x6e95fc))
            embed.set_thumbnail(url=i['thumbnail_url'])
            for lobby in lobbies_for_message:
                players = [record['osu_username'] for record in signups if record['lobby_id'] == lobby['lobby_id']]
                time = lobby['time']
                # datetime didn't have an easy way to get lowercase am/pm so I just did it manually
                timestring = f'{time.hour%12}:{str(time.minute).zfill(2)}{"am" if time.hour < 12 else "pm"}'
                # uses discord emotes to represent time with an analog clock emote
                name = f':clock{time.hour%12}: {timestring}'
                # either contains the reffs osu name or None if lobby has no reff
                referee_name = [record['staff_osu_username'] for record in staff if record['staff_osu_id'] == lobby['staff_osu_id']]

                free_spots = 16 - len(players)
                if free_spots == 0:
                    emote = ':red_circle:'
                elif free_spots == 16:
                    emote = ':orange_circle:'
                else:
                    emote = ':green_circle:'
                playerstring = '    '.join(players) if len(players) > 0 else '-'
                reff = f' | Reffed by {referee_name[0]}' if referee_name else ''
                value = f'{emote} **ID: {lobby["lobby_id"]}** | {free_spots} free spots{reff}```{playerstring}```'
                embed.add_field(name=name, inline=False, value=value)
            await message.edit(content='', embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    @send_typing
    async def pingunsigned(self, ctx):
        # Get everything after the command
        content = ctx.message.content.lstrip(ctx.prefix + ctx.invoked_with + ' ')
        await ctx.message.delete()
        if content.strip() == '':
            await ctx.send('Add what you want to say to the pingees after the command', delete_after=6)
            return
        async with connpool.acquire() as conn:
            async with conn.transaction():
                nonsigned_discord_ids = await conn.fetch('''select discord_id from players natural join (select osu_id from players except select osu_id from lobby_signups) as i;''')
        nonsigned_discord_ids = [record['discord_id'] for record in nonsigned_discord_ids]
        nonsigned_users = [bot.get_user(id) for id in nonsigned_discord_ids]
        if None in nonsigned_users:
            await ctx.send('Failed to find at least one of the pingees by discord id.', delete_after=7)
            return
        confirmed = await confirm(ctx, f'This will append your message (minus the command) with the pings of {len(nonsigned_users)} people. React with the tick to confirm within {20} seconds.')
        if confirmed:
            pings = ' '.join([user.mention for user in nonsigned_users])
            await ctx.send(f'{content}\n{pings}')

    @commands.command()
    @is_staff()
    @send_typing
    async def unsigned(self, ctx):
        await ctx.message.delete()
        async with connpool.acquire() as conn:
            async with conn.transaction():
                nonsigned_records = await conn.fetch('''select osu_username from players natural join (select osu_id from players except select osu_id from lobby_signups) as i;''')
        nonsigned_osu_usernames = [record['osu_username'] for record in nonsigned_records]
        user_list = '    '.join(nonsigned_osu_usernames) if len(nonsigned_osu_usernames) > 0 else '-'
        await ctx.send(f'{len(nonsigned_osu_usernames)} players have not yet signed up. ```{user_list}```')


def setup(bot):
    bot.add_cog(QualifiersCog(bot))
