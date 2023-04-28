import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, View
import aiosqlite
import asyncio
from dotenv import load_dotenv
import datetime
import pytz

# TODO [MODERATION SYSTEM]
# Add a record system of users who've broken rules, as well as track their user id + damage taken ✅
# Create a way for people with specified roles (Moderator, Owner) to track the data of a certain user ✅
# Create a way for people with specified roles (Moderator, Owner) to apply damage to a certain user ✅
    # PARAMETERS MUST CONTAIN:
        # - Rule (The rule that they broke, ect. Rule #1 - No spamming)
        # - Description (Text that is sent to the person that broke the role, alongside damage parameter)
        # - Damage (Select 1 of 4 buttons that determine the damage the user will take)
        
    # Every time the command is activated it will be recorded in a specific channel that only the owner or trusted people can see (to inform of any abuse or incorrect use)
# Add a system that bans the user if they reach a certain amount of damage. Also notify the user in their DMs so they don't get confused ✅
# (OPTIONAL): Create an appeal system via the user's DMs that is sent over to an appeal channel in the server, buttons that determine whether the user is unbanned or banned ✅
    # When appealed successfully, the user's damage record will be set to 15
    # USERS CAN ONLY APPEAL ONCE, IF THEY ARE BANNED AGAIN THEY ARE FORBIDDEN FROM APPEALING
# Add a system that makes all damage for users go down by 1 every hour ✅

async def main(Client: commands.Bot):
    # Client events
    async def on_ready():
        print("moderation.py initiated")
        try:
            # Database
            Client.db = await aiosqlite.connect("moderation.db")
            await asyncio.sleep(3)
            async with Client.db.cursor() as cursor:
                await cursor.execute("CREATE TABLE IF NOT EXISTS moderation (user INTEGER, rule1 TEXT, rule2 TEXT, rule3 TEXT, rule4 TEXT, rule5 TEXT, rule6 TEXT, rule7 TEXT, rule8 TEXT, rule9 TEXT, rule10 TEXT, damage INTEGER, guild INTEGER)")
                await cursor.execute("CREATE TABLE IF NOT EXISTS history_ids (user INTEGER, history_id INTEGER, time_created TEXT, guild INTEGER)")
                await cursor.execute("CREATE TABLE IF NOT EXISTS ban_history (user INTEGER, time_created TEXT)")
            await Client.db.commit()

            print("moderation.py ready")

            # Run loops
            if not lower_damage.is_running():
                lower_damage.start()
        except Exception as e:
            print(e)

    rule_charges = {
        "rule1": {
            1: 25,
        },
        "rule2": {
            1: 15,
            2: 25,
        },
        "rule3": {
            1: 5,
            2: 15,
        },
        "rule4": {
            1: 2,
            2: 8,
        },
        "rule5": {
            1: 2,
            2: 10,
        },
        "rule6": {
            1: 25,
        },
        "rule7": {
            1: 5,
            2: 10,
            3: 15,
            4: 25
        },
        "rule8": {
            1: 5,
            2: 10,
            3: 15,
            4: 25
        },
        "rule9": {
            1: 15,
            2: 25,
        },
        "rule10": {
            1: 25
        },
    }

    mute_times = {
        1: {
            "min": 3,
            "max": 3,
            "dur": datetime.timedelta(hours=1),
        },
        2: {
            "min": 4,
            "max": 10,
            "dur": datetime.timedelta(hours=3),
        },
        3: {
            "min": 11,
            "max": 15,
            "dur": datetime.timedelta(hours=6),
        },
        4: {
            "min": 16,
            "max": 19,
            "dur": datetime.timedelta(hours=8),
        },
        5: {
            "min": 20,
            "max": 24,
            "dur": datetime.timedelta(hours=12),
        },
    }

    async def timeout(interaction: any, member: discord.Member, seconds: int = 0, minutes: int = 0, hours: int = 0, days: int = 0):
        duration = datetime.timedelta(seconds=seconds, minutes=minutes, hours= hours, days=days)
        await member.timeout(datetime.datetime.utcnow() + duration)
        await member.send(f'{member.mention} You were timed out until for {duration}')

    async def banUser(user: discord.User):
        try:
            channel = await user.create_dm()
            await Client.db.execute("INSERT INTO ban_history (user, time_created) VALUES (?, ?)", (user.id, str(datetime.datetime.now())))
            await channel.send("**You've been banned from Anicide Official.**\n\nJoin Appeal Server here:\nhttps://discord.gg/SVrFhRXK\n\nIf you are allowed back into the server, your damage will be set to 15- increasing the chances of you getting banned for about a week.")
            await user.ban(reason="You've reached a capacity of 25 damage")
        except Exception as e:
            print(e)

    @Client.event
    async def on_member_join(user: discord.User):
        if user.guild.id == 1000200815945986188:
            # Check to see if the user was banned before- set record to 10
            user_tbl = await Client.db.execute(f"SELECT time_created FROM ban_history WHERE user={user.id}")
            tbl_data = await user_tbl.fetchall()
            if tbl_data:
                await Client.db.execute(f"DELETE FROM moderation WHERE user={user.id}")
                await Client.db.execute("INSERT INTO moderation (user, rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, rule9, rule10, damage, guild) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (user.id, "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", 15, 1000200815945986188))
                await Client.db.commit()

    async def addDamage(interaction: any, user: discord.User, rule_type: discord.app_commands.Choice[str]):
        try:
            guild_id = interaction["guild_id"]
            rule_tbl = rule_charges[rule_type.value]
            if rule_tbl:
                cur = await Client.db.execute(f"SELECT {rule_type.value} FROM moderation WHERE guild = ? AND user = ?", (guild_id, user.id))
                data = await cur.fetchone()
                offenses = int(data[0])

                damage_count = rule_tbl[offenses > len(rule_tbl) and len(rule_tbl) or offenses]
                if damage_count:
                    await Client.db.execute(f"UPDATE moderation SET damage = damage + {damage_count} WHERE guild = ? AND user = ?", (guild_id, user.id))

                    # Check to see if the user should be banned; also apply appeals to them in their DMs
                    try:
                        cur = await Client.db.execute(f"SELECT damage FROM moderation WHERE guild = ? AND user = ?", (guild_id, user.id))
                        data = await cur.fetchone()
                        damage = data[0]

                        current_time_out = None
                        for x in mute_times.values():
                            min = x.get("min")
                            max = x.get("max")
                            dur = x.get("dur")
                            if damage >= min and damage <= max:
                                print(dur)
                                current_time_out = dur

                        if current_time_out != None:
                            await timeout(interaction, user, current_time_out)

                        if damage >= 25:
                            await banUser(user)

                    except Exception as e:
                        print(e)
        except Exception as e:
            print(e)

    async def addOffense(interaction: any, user: discord.User, rule_type: discord.app_commands.Choice[str]):
        try:
            async with Client.db.cursor() as cursor:
                guild_id = interaction["guild_id"]
                # Check to see if user's id already has a table to avoid duplicates
                user_tbl = await Client.db.execute(f"SELECT * FROM moderation WHERE user={user.id} AND guild={guild_id}")
                tbl_data = await user_tbl.fetchone()
                if not tbl_data:
                    await Client.db.execute("INSERT OR IGNORE INTO moderation (user, rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, rule9, rule10, damage, guild) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (user.id, "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", 0, interaction.guild_id))

                # Update values
                cur = await Client.db.execute(f"SELECT {rule_type.value} FROM moderation WHERE guild = ? AND user = ?", (guild_id, user.id))
                data = await cur.fetchone()
                current_offenses = int(data[0])
                new_offense_count = str(current_offenses + 1)

                await cursor.execute(f"UPDATE moderation SET {rule_type.value} = {new_offense_count} WHERE guild = ? AND user = ?", (guild_id, user.id))
                cur = await Client.db.execute(f"SELECT {rule_type.value} FROM moderation WHERE guild = ? AND user = ?", (guild_id, user.id))
                data = await cur.fetchone()
                offenses = data[0]

                await addDamage(interaction, user, rule_type)

                await Client.db.commit()
        except Exception as e:
            print(e)


    # Client commands

    rule_types = [
        discord.app_commands.Choice(name=":label: Not Safe For Work Content", value="rule1"),
        discord.app_commands.Choice(name=":label: Toxicity, Discrimination, & Immaturity", value="rule2"),
        discord.app_commands.Choice(name=":label: Provocative Topics & Drama", value="rule3"),
        discord.app_commands.Choice(name=":label: Flooding and Spamming", value="rule4"),
        discord.app_commands.Choice(name=":label: Pings", value="rule5"),
        discord.app_commands.Choice(name=":label: Unwanted Media, Piracy & Leaking", value="rule6"),
        discord.app_commands.Choice(name=":label: Language & Bypassing", value="rule7"),
        discord.app_commands.Choice(name=":label: VC Rules & Bots", value="rule8"),
        discord.app_commands.Choice(name=":label: Slander / Framing", value="rule9"),
        discord.app_commands.Choice(name=":label: Alt Accounts", value="rule10"),
    ]
    rule_headers_by_value = {
        "rule1": ":label: Not Safe For Work Content",
        "rule2": ":label: Toxicity, Discrimination, & Immaturity",
        "rule3": ":label: Provocative Topics & Drama",
        "rule4": ":label: Flooding and Spamming",
        "rule5": ":label: Pings",
        "rule6": ":label: Unwanted Media, Piracy & Leaking",
        "rule7": ":label: Language & Bypassing",
        "rule8": ":label: VC Rules & Bots",
        "rule9": ":label: Slander / Framing",
        "rule10": ":label: Alt Accounts"
    }

    @Client.tree.command(name="wasbanned", description="*MODERATOR ONLY:* Checks if the user given had a ban history")
    @app_commands.describe(user="User to check")
    async def wasbanned(interaction: any, user: discord.User):
        # Conditions
        role = discord.utils.get(interaction.user.roles, name = "Moderator")
        if not role in interaction.user.roles:
            await interaction.response.send_message(f"Failed to use action due to lack of moderator permissions", ephemeral=True)
            return
        if user.bot == True:
            await interaction.response.send_message(f"Failed to add offense to {user.name} as they are a bot.", ephemeral=True)
            return
            
        # Check to see if the user was banned before- set record to 10
        user_tbl = await Client.db.execute(f"SELECT time_created FROM ban_history WHERE user={user.id}")
        tbl_data = await user_tbl.fetchall()
        if tbl_data:
            await interaction.response.send_message(f"User {user.mention} was banned previously in Anicide Official.", ephemeral=True)
            return
        await interaction.response.send_message(f"User {user.mention} wasn't banned in Anicide Official.", ephemeral=True)

    @Client.tree.command(name="addoffense", description="*MODERATOR ONLY:* Records an offense to a user's history and adds damage to them")
    @app_commands.describe(user="User who committed an offense")
    @app_commands.describe(rule_type="The type of rule the user broke / had an offense for")
    @app_commands.choices(rule_type=rule_types)
    @app_commands.describe(reason="Reason why you added an offense to this user. This will be recorded")
    async def addoffense(interaction: discord.Interaction, user: discord.User, rule_type: discord.app_commands.Choice[str], reason: str):
        try:
            guild_id = interaction.guild_id
            # Conditions
            role = discord.utils.get(interaction.user.roles, name = "Moderator")
            if not role in interaction.user.roles:
                await interaction.response.send_message(f"Failed to use action due to lack of moderator permissions", ephemeral=True)
                return
            if user.bot == True:
                await interaction.response.send_message(f"Failed to add offense to {user.name} as they are a bot.", ephemeral=True)
                return
            
            # TRACK THE ACTION IN A 'TRACK-HISTORY'
            channel = Client.get_channel(1099414517848481892)
            cur = await Client.db.execute("SELECT * FROM history_ids")
            data = await cur.fetchall()

            await Client.db.execute("INSERT INTO history_ids (user, history_id, time_created, guild) VALUES (?, ?, ?, ?)", (user.id, len(data) + 1, str(datetime.datetime.now()), guild_id))
            
            cur = await Client.db.execute("SELECT * FROM history_ids WHERE user = ? AND guild = ? AND history_id = ?", (user.id, guild_id, len(data) + 1))
            data2 = await cur.fetchone()

            embed = discord.Embed(
                colour=discord.Colour.brand_green(),
                description= interaction.user.mention + f" added offense for {rule_headers_by_value[rule_type.value]} to user " + user.mention,
                title="Action Committed " + f"[History ID #{len(data) + 1}]"
            )
            embed.set_thumbnail(url=interaction.user.avatar.url)
            embed.add_field(name="Reason:", value=reason)
            embed.set_footer(text="User ID: " + str(interaction.user.id) + " | Committed at " + data2[2])

            await channel.send(embed=embed)

            await interaction.response.send_message(f"Successfully added offense to {user.name}.", ephemeral=True)
            await addOffense({
                "guild_id": interaction.guild_id
            }, user, rule_type)
        except Exception as e:
            print(e)

    @Client.tree.command(name="viewoffenses", description="*MODERATOR ONLY:* View how many offenses a user has for every rule as well as their damage")
    @app_commands.describe(user="User to view")
    async def viewoffenses(interaction: discord.Interaction, user: discord.User):
        try:
            # Conditions
            role = discord.utils.get(interaction.user.roles, name = "Moderator")
            if not role in interaction.user.roles:
                await interaction.response.send_message(f"Failed to use action due to lack of moderator permissions", ephemeral=True)
                return
            if user.bot == True:
                await interaction.response.send_message(f"Failed to add offense to {user.name} as they are a bot.", ephemeral=True)
                return
            
            # Check to see if user's id already has a table to avoid duplicates
            user_tbl = await Client.db.execute(f"SELECT * FROM moderation WHERE user={user.id} AND guild={interaction.guild_id}")
            tbl_data = await user_tbl.fetchone()
            if not tbl_data:
                await Client.db.execute("INSERT OR IGNORE INTO moderation (user, rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, rule9, rule10, damage, guild) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (user.id, "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", 0, interaction.guild_id))
            
            description_to_set = "No roles provided"
            for x in user.roles:
                if description_to_set == "No roles provided":
                    description_to_set = ""

                if x.name == "@everyone":
                    continue
                elif x.name == "ㅤㅤㅤㅤㅤStarter Rolesㅤㅤㅤㅤㅤ":
                    continue
                elif x.name == "ㅤㅤㅤㅤㅤAchievementsㅤㅤㅤㅤㅤ":
                    continue

                if description_to_set == "":
                    description_to_set = f"{x.mention}"
                else:
                    description_to_set = description_to_set + f" {x.mention}"
            embed = discord.Embed(
                colour=discord.Colour.orange(),
                description="**Roles: **\n" + description_to_set,
                title=user.name
            )
            embed.set_author(name="Recorded Offenses")
            embed.set_thumbnail(url=user.avatar.url)
            embed.set_footer(text="User ID: " + str(user.id))

            cur = await Client.db.execute(f"SELECT damage FROM moderation WHERE guild = ? AND user = ?", (interaction.guild_id, user.id))
            data = await cur.fetchone()
            damage = data[0]
            embed.add_field(name="Damage:", value=damage)

            # Create a field for every rule in database
            cur = await Client.db.execute("SELECT * FROM moderation WHERE guild = ? AND user = ?", (interaction.guild_id, user.id))
            data = await cur.fetchone()

            if data:
                _rulecount = 0
                for x in data:
                    if type(x) == str:
                        _rulecount = _rulecount + 1
                        _rulestr = "rule" + str(_rulecount)
                        end_sentence = x + " offenses tracked"
                        if int(x) == 1:
                            end_sentence = x + " offense tracked"
                        elif int(x) <= 0:
                            end_sentence = "No offenses tracked"

                        embed.add_field(name=rule_headers_by_value[_rulestr], value= end_sentence)
            else:
                embed.add_field(name="No history of offenses found", value="An offense must be added to a user to view their database.")

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(e)


    # IDENTCIAL AS /VIEWOFFENSES, MEANT FOR PUBLIC USE INSTEAD
    @Client.tree.command(name="myoffenses", description="View your offenses, roles, and damage")
    async def myoffenses(interaction: discord.Interaction):
        try:
            # Check to see if user's id already has a table to avoid duplicates
            user_tbl = await Client.db.execute(f"SELECT * FROM moderation WHERE user={interaction.user.id} AND guild={interaction.guild_id}")
            tbl_data = await user_tbl.fetchone()
            if not tbl_data:
                await Client.db.execute("INSERT OR IGNORE INTO moderation (user, rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, rule9, rule10, damage, guild) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (user.id, "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", 0, interaction.guild_id))

            description_to_set = "No roles provided"
            user = interaction.user
            for x in user.roles:
                if description_to_set == "No roles provided":
                    description_to_set = ""

                if x.name == "@everyone":
                    continue
                elif x.name == "ㅤㅤㅤㅤㅤStarter Rolesㅤㅤㅤㅤㅤ":
                    continue
                elif x.name == "ㅤㅤㅤㅤㅤAchievementsㅤㅤㅤㅤㅤ":
                    continue
                elif x.name == "ㅤㅤㅤㅤㅤReaction Rolesㅤㅤㅤㅤㅤ":
                    continue

                if description_to_set == "":
                    description_to_set = f"{x.mention}"
                else:
                    description_to_set = description_to_set + f" {x.mention}"
            embed = discord.Embed(
                colour=discord.Colour.orange(),
                description="**Roles: **\n" + description_to_set,
                title=user.name
            )
            embed.set_author(name="Recorded Offenses")
            embed.set_thumbnail(url=user.avatar.url)
            embed.set_footer(text="User ID: " + str(user.id))

            cur = await Client.db.execute(f"SELECT damage FROM moderation WHERE guild = ? AND user = ?", (interaction.guild_id, user.id))
            data = await cur.fetchone()
            damage = data[0]
            embed.add_field(name="Damage:", value=damage)

            # Create a field for every rule in database
            cur = await Client.db.execute("SELECT * FROM moderation WHERE guild = ? AND user = ?", (interaction.guild_id, user.id))
            data = await cur.fetchone()

            if data:
                _rulecount = 0
                for x in data:
                    if type(x) == str:
                        _rulecount = _rulecount + 1
                        _rulestr = "rule" + str(_rulecount)
                        end_sentence = x + " offenses tracked"
                        if int(x) == 1:
                            end_sentence = x + " offense tracked"
                        elif int(x) <= 0:
                            end_sentence = "No offenses tracked"

                        embed.add_field(name=rule_headers_by_value[_rulestr], value= end_sentence)
            else:
                embed.add_field(name="No history of offenses found", value="An offense must be added to a user to view their database.")

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(e)


    @Client.tree.command(name="update_rule_offense_count", description="*MODERATOR ONLY:* Sets the offense count for any given rule to the parameter given")
    @app_commands.choices(rule_type=rule_types)
    @app_commands.describe(rule_type="The type of rule an offense should be added to")
    @app_commands.describe(new_value="The number to set the new amount of offenses to")
    @app_commands.describe(reason="Reason why you added an offense to this user. This will be recorded")
    async def update_rule_offense_count(interaction: discord.Interaction, user: discord.User, rule_type: discord.app_commands.Choice[str], new_value: str, reason: str):
        try:
            # Conditions
            role = discord.utils.get(interaction.user.roles, name = "Moderator")
            if not role in interaction.user.roles:
                await interaction.response.send_message(f"Failed to use action due to lack of moderator permissions", ephemeral=True)
                return
            if user.bot == True:
                await interaction.response.send_message(f"Failed to add offense to {user.name} as they are a bot.", ephemeral=True)
                return
            
            # TRACK THE ACTION IN A 'TRACK-HISTORY'
            channel = Client.get_channel(1099414517848481892)
            cur = await Client.db.execute("SELECT * FROM history_ids")
            data = await cur.fetchall()

            await Client.db.execute("INSERT INTO history_ids (user, history_id, time_created, guild) VALUES (?, ?, ?, ?)", (user.id, len(data) + 1, str(datetime.datetime.now()), interaction.guild_id))

            cur = await Client.db.execute("SELECT * FROM history_ids WHERE user = ? AND guild = ? AND history_id = ?", (user.id, interaction.guild_id, len(data) + 1))
            data2 = await cur.fetchone()

            embed = discord.Embed(
                colour=discord.Colour.yellow(),
                description= interaction.user.mention + " changed the rule offense count for " + user.mention,
                title="Action Committed " + f"[History ID #{len(data) + 1}]"
            )

            cur = await Client.db.execute(f"SELECT {rule_type.value} FROM moderation WHERE guild = ? AND user = ?", (interaction.guild_id, user.id))
            data = await cur.fetchone()

            embed.set_thumbnail(url=interaction.user.avatar.url)
            embed.add_field(name="Reason:", value=reason)
            embed.add_field(name=f"Changes [{rule_type.value}]:", value="Before: " + str(data[0]) + " | After: " + str(new_value))
            embed.set_footer(text="User ID: " + str(interaction.user.id) + " | Committed at " + data2[2])

            await channel.send(embed=embed)
            
            await interaction.response.send_message(f"Successfully set {user.name}'s {rule_type.name} offense count to {new_value}", ephemeral=True)
            await Client.db.execute(f"UPDATE moderation SET {rule_type.value} = {new_value} WHERE guild = ? AND user = ?", (interaction.guild_id, user.id))
            await Client.db.commit()
        except Exception as e:
            print(e)

    @Client.tree.command(name="update_user_damage_count", description="*MODERATOR ONLY:* Sets the damage for any given user to the parameter given")
    @app_commands.describe(user="User to view")
    @app_commands.describe(new_value="The number to set the new damage count to")
    @app_commands.describe(reason="Reason why you added an offense to this user. This will be recorded")
    async def update_user_damage_count(interaction: discord.Interaction, user: discord.User, new_value: int, reason: str):
        try:
            # Conditions
            role = discord.utils.get(interaction.user.roles, name = "Moderator")
            if not role in interaction.user.roles:
                await interaction.response.send_message(f"Failed to use action due to lack of moderator permissions", ephemeral=True)
                return
            if user.bot == True:
                await interaction.response.send_message(f"Failed to add offense to {user.name} as they are a bot.", ephemeral=True)
                return
            
            # TRACK THE ACTION IN A 'TRACK-HISTORY'
            channel = Client.get_channel(1099414517848481892)
            cur = await Client.db.execute("SELECT * FROM history_ids")
            data = await cur.fetchall()

            await Client.db.execute("INSERT INTO history_ids (user, history_id, time_created, guild) VALUES (?, ?, ?, ?)", (user.id, len(data) + 1, str(datetime.datetime.now()), interaction.guild_id))

            cur = await Client.db.execute("SELECT * FROM history_ids WHERE user = ? AND guild = ? AND history_id = ?", (user.id, interaction.guild_id, len(data) + 1))
            data2 = await cur.fetchone()

            embed = discord.Embed(
                colour=discord.Colour.brand_red(),
                description= interaction.user.mention + " changed the damage count for " + user.mention,
                title="Action Committed " + f"[History ID #{len(data) + 1}]"
            )

            cur = await Client.db.execute(f"SELECT damage FROM moderation WHERE guild = ? AND user = ?", (interaction.guild_id, user.id))
            data = await cur.fetchone()

            embed.set_thumbnail(url=interaction.user.avatar.url)
            embed.add_field(name="Reason:", value=reason)
            embed.add_field(name="Changes:", value="Before: " + str(data[0]) + " | After: " + str(new_value))
            embed.set_footer(text="User ID: " + str(interaction.user.id) + " | Committed at " + data2[2])

            await channel.send(embed=embed)
            
            await interaction.response.send_message(f"Successfully set {user.name}'s damage to {new_value}", ephemeral=True)
            await Client.db.execute(f"UPDATE moderation SET damage = {new_value} WHERE guild = ? AND user = ?", (interaction.guild_id, user.id))
            await Client.db.commit()
        except Exception as e:
            print(e)

    @tasks.loop(hours=1)
    async def lower_damage():
        async with Client.db.cursor() as cursor:
            cur = await cursor.execute("SELECT * FROM moderation")
            data = await cur.fetchall()
            for x in data:
                # Get variables from tuple
                user = x[0]
                damage = x[len(x) - 2]
                guild = x[len(x) - 1]

                new_damage = damage - 2
                if new_damage < 0:
                    new_damage = 0

                await Client.db.execute(f"UPDATE moderation SET damage = {new_damage} WHERE guild = ? AND user = ?", (guild, user))
                await Client.db.commit()
        # TRACK THE ACTION IN A 'TRACK-HISTORY'
        channel = Client.get_channel(1099414517848481892)

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            description= "Damage count for all users has been decreased by 2",
            title="Damage Updated "
        )
        embed.set_footer(text="Committed at " + str(datetime.datetime.now()))

        await channel.send(embed=embed)

    anti_spam = commands.CooldownMapping.from_cooldown(5, 15, commands.BucketType.member)
    too_many_violations = commands.CooldownMapping.from_cooldown(4, 60, commands.BucketType.member)

    @Client.listen()
    async def on_message(message: discord.Message):
        if type(message.channel) is not discord.TextChannel or message.author.bot: return
        bucket = anti_spam.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            print("is spamming")
            await message.delete()
            await addOffense({"guild_id": message.guild.id}, message.author, discord.app_commands.Choice(name="[#1]: No Spamming", value="rule1"))
            await message.channel.send(f"{message.author.mention}, don't spam!", delete_after=10)
            violations = too_many_violations.get_bucket(message)
            check = violations.update_rate_limit()
            if check:
                await message.channel.send(f"{message.author.mention}, timed out!", delete_after=5)

    await on_ready()