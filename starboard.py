import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import aiosqlite
import datetime

async def main(Client: commands.Bot):
    async def on_ready():
        print("starboard.py initiated")
        try:
            # Database
            setattr(Client, "stardb", await aiosqlite.connect("starboard.db"))
                
            await asyncio.sleep(2)
            async with Client.stardb.cursor() as cursor:
                await Client.stardb.execute("CREATE TABLE IF NOT EXISTS starSetup (starLimit INTEGER, starboard_channel INTEGER, highlight_channel INTEGER, guild INTEGER)")
                await Client.stardb.execute("CREATE TABLE IF NOT EXISTS starPlayers (user INTEGER, guild INTEGER)")
            await Client.stardb.commit()

            print("starboard.py ready")
        except Exception as e:
            print(e)

    @Client.event
    async def on_raw_reaction_add(payLoad):
        emoji = payLoad.emoji
        guild = Client.get_guild(payLoad.guild_id)
        channel = await guild.fetch_channel(payLoad.channel_id)
        message = await channel.fetch_message(payLoad.message_id)

        if message.author.bot:
            return

        if emoji.name == "⭐":
            async with Client.stardb.cursor() as cursor:
                await cursor.execute("SELECT starLimit, starboard_channel, highlight_channel FROM starSetup WHERE guild = ?", (guild.id,))
                data = await cursor.fetchall()
                for x in data:
                    starData = x[0]
                    channelData = await guild.fetch_channel(x[1])
                    highlight_channelData = await guild.fetch_channel(x[2])
                    if not channelData.id == channel.id:
                        continue
                    for reaction in message.reactions:
                        if reaction.emoji == "⭐":
                            if reaction.count >= starData:
                                embed = discord.Embed(title=f"⭐ {message.author.name} | {channel.mention}", description=f"{message.content}", colour=discord.Colour.orange())
                                try:
                                    embed.set_image(url=message.attachments[0].url)
                                except:
                                    pass
                                embed.set_author(name="Click to jump to message!", url=message.jump_url, icon_url=message.author.avatar.url)
                                embed.set_footer(text=f"Message ID: {message.id} | Author: {message.author.name}")
                                await highlight_channelData.send(embed=embed)
                                await Client.stardb.execute("INSERT OR IGNORE INTO starPlayers (user, guild) VALUES (?, ?)", (message.author.id, message.guild.id))
            await Client.stardb.commit()

    @Client.tree.command(name="create_starboard", description="*DEVELOPER ONLY:* Creates a starboard to the channel given")
    @app_commands.describe(starboard_chnl="The channel that supports starboards")
    @app_commands.describe(highlight_chnl="The channel where messages that meet the star_limit will appear")
    @app_commands.describe(star_limit="How many star reacts to have the starboard featured")
    async def create_starboard(interaction: discord.Interaction, starboard_chnl: discord.TextChannel, highlight_chnl: discord.TextChannel, star_limit: int):
        try:
            starboard_channel = Client.get_channel(starboard_chnl.id)
            highlight_channel = Client.get_channel(highlight_chnl.id)
            if not starboard_channel or not highlight_channel:
                await interaction.response.send_message("starboard_channel or highlight_channel are not valid channels!", ephemeral=True)
                return
            
            # Replace starboard data if it already exists
            star_tbl = await Client.stardb.execute(f"SELECT * FROM starSetup WHERE starboard_channel={starboard_channel.id} AND guild={interaction.guild_id}")
            tbl_data = await star_tbl.fetchone()
            if tbl_data:
                await Client.stardb.execute(f"DELETE FROM starSetup WHERE starboard_channel={starboard_chnl.id} AND guild={interaction.guild_id}")

                 # TRACK THE ACTION IN A 'TRACK-HISTORY'
                channel = Client.get_channel(1099414517848481892)
                cur = await Client.db.execute("SELECT * FROM history_ids")
                data = await cur.fetchall()

                await Client.db.execute("INSERT OR IGNORE INTO history_ids (user, history_id, time_created, guild) VALUES (?, ?, ?, ?)", (interaction.user.id, len(data) + 1, str(datetime.datetime.now()), interaction.guild_id))

                cur = await Client.db.execute("SELECT * FROM history_ids WHERE user = ? AND guild = ? AND history_id = ?", (interaction.user.id, interaction.guild_id, len(data) + 1))
                data2 = await cur.fetchone()

                embed = discord.Embed(
                    colour=discord.Colour.red(),
                    description= interaction.user.mention + " removed old starboard data from " + starboard_channel.mention,
                    title="Action Committed " + f"[History ID #{len(data) + 1}]"
                )

                embed.set_thumbnail(url=interaction.user.avatar.url)
                embed.set_footer(text="User ID: " + str(interaction.user.id) + " | Committed at " + data2[2])

                await channel.send(embed=embed)


            
            # TRACK THE ACTION IN A 'TRACK-HISTORY'
            channel = Client.get_channel(1099414517848481892)
            cur = await Client.db.execute("SELECT * FROM history_ids")
            data = await cur.fetchall()

            await Client.db.execute("INSERT OR IGNORE INTO history_ids (user, history_id, time_created, guild) VALUES (?, ?, ?, ?)", (interaction.user.id, len(data) + 1, str(datetime.datetime.now()), interaction.guild_id))

            cur = await Client.db.execute("SELECT * FROM history_ids WHERE user = ? AND guild = ? AND history_id = ?", (interaction.user.id, interaction.guild_id, len(data) + 1))
            data2 = await cur.fetchone()

            embed = discord.Embed(
                colour=discord.Colour.dark_magenta(),
                description= interaction.user.mention + " added starboard data to " + starboard_channel.mention + " and set the highlight channel to " + highlight_channel.mention,
                title="Action Committed " + f"[History ID #{len(data) + 1}]"
            )

            embed.set_thumbnail(url=interaction.user.avatar.url)
            embed.add_field(name="Star Limit:", value=star_limit)
            embed.set_footer(text="User ID: " + str(interaction.user.id) + " | Committed at " + data2[2])

            await channel.send(embed=embed)
            await Client.db.commit()

            await Client.stardb.execute("INSERT OR IGNORE INTO starSetup (starLimit, starboard_channel, highlight_channel, guild) VALUES (?, ?, ?, ?)", (star_limit, starboard_channel.id, highlight_channel.id, interaction.guild_id))
            await Client.stardb.commit()

            await interaction.response.send_message(f"Created starboard database in {starboard_channel.mention}! All featured messages will be uploaded to {highlight_channel.mention}.\n\n**Creating a database with the same starboard_channel id as this starboard will cause this starboard to be deleted.**", ephemeral=True)
        except Exception as e:
            print(e)
    
    @Client.tree.command(name="delete_starboard", description="*DEVELOPER ONLY:* Deletes a starboard with the channel id given")
    @app_commands.describe(starboard_chnl="The channel that supports starboards")
    async def delete_starboard(interaction: discord.Interaction, starboard_chnl: discord.TextChannel):
        star_tbl = await Client.stardb.execute(f"SELECT * FROM starSetup WHERE starboard_channel={starboard_chnl.id} AND guild={interaction.guild_id}")
        tbl_data = await star_tbl.fetchone()
        if tbl_data:
            await Client.stardb.execute(f"DELETE FROM starSetup WHERE starboard_channel={starboard_chnl.id} AND guild={interaction.guild_id}")

            # TRACK THE ACTION IN A 'TRACK-HISTORY'
            channel = Client.get_channel(1099414517848481892)
            cur = await Client.db.execute("SELECT * FROM history_ids")
            data = await cur.fetchall()

            await Client.db.execute("INSERT OR IGNORE INTO history_ids (user, history_id, time_created, guild) VALUES (?, ?, ?, ?)", (interaction.user.id, len(data) + 1, str(datetime.datetime.now()), interaction.guild_id))

            cur = await Client.db.execute("SELECT * FROM history_ids WHERE user = ? AND guild = ? AND history_id = ?", (interaction.user.id, interaction.guild_id, len(data) + 1))
            data2 = await cur.fetchone()

            embed = discord.Embed(
                colour=discord.Colour.red(),
                description= interaction.user.mention + " removed old starboard data from " + starboard_chnl.mention,
                title="Action Committed " + f"[History ID #{len(data) + 1}]"
            )

            embed.set_thumbnail(url=interaction.user.avatar.url)
            embed.set_footer(text="User ID: " + str(interaction.user.id) + " | Committed at " + data2[2])

            await channel.send(embed=embed)
            await interaction.response.send_message(f"Successfully removed starboard data for {starboard_chnl.mention}!\n\n**Use /create_starboard slash command if you want to create a starboard for the given channel.**", ephemeral=True)
            await Client.db.commit()
            await Client.stardb.commit()
        else:
            await interaction.response.send_message(f"No starboard data found for {starboard_chnl.mention}!\n\n**Use /create_starboard slash command if you want to create a starboard for the given channel.**", ephemeral=True)

    @Client.listen()
    async def on_message(message: discord.Message):
        if type(message.channel) is not discord.TextChannel or message.author.bot: return
        try:
            cur = await Client.stardb.execute("SELECT * FROM starSetup WHERE guild = ?", (message.guild.id, ))
            data = await cur.fetchall()
            if data:
                for x in data:
                    channelData = await message.guild.fetch_channel(x[1])
                    if message.channel.id == channelData.id:
                        await message.add_reaction("⭐")
        except Exception as e:
            print(e)
        async with Client.stardb.cursor() as cursor:
            try:
                cur = await Client.stardb.execute("SELECT * FROM starPlayers WHERE guild = ?", (message.guild.id, ))
                data = await cur.fetchall()
                if data:
                    searched = {}
                    for x in data:
                        user: discord.User = await Client.fetch_user(x[0])
                        if user.name in searched.values():
                            continue
                        if message.author.id == user.id:
                            searched[len(searched)] = user.name
                            # Check how many times the person has gotten on the featured tabs
                            userCur = await Client.stardb.execute("SELECT * FROM starPlayers WHERE user = ? AND guild = ?", (user.id, message.guild.id))
                            userData = await userCur.fetchall()
                            if data:
                                amountOfFeatures = len(userData)
                                if amountOfFeatures >= 5:

                                    # Advanced roles
                                    has_role = discord.utils.get(message.author.roles, name = "Star Creator II")
                                    if has_role == None:
                                        role_to_give = discord.utils.get(message.author.guild.roles, name="Star Creator II")
                                        await message.author.add_roles(role_to_give)
                                        await message.channel.send(f"{user.mention} You've reached the feature channels FIVE TIMES! You've earned the {role_to_give.mention} achievement role. CONGRATULATIONS!")
                                else:

                                    # Basic roles
                                    has_role = discord.utils.get(message.author.roles, name = "Star Creator")
                                    if has_role == None:
                                        role_to_give = discord.utils.get(message.author.guild.roles, name="Star Creator")
                                        await message.author.add_roles(role_to_give)
                                        await message.channel.send(f"{user.mention} Congratulations on reaching any featured channel! You've earned the {role_to_give.mention} achievement role.")
            except Exception as e:
                print(e)
    
    await on_ready()