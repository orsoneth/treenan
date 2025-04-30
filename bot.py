import os
import discord
import requests
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TOKEN')
EVENT_PING_ROLE_ID = int(os.getenv('EVENT_PING_ROLE_ID'))
TRUSTED_ROLE_ID = int(os.getenv('TRUSTED_ROLE_ID'))
MODERATOR_ROLE_ID = int(os.getenv('MODERATOR_ROLE_ID'))
REGISTRATION_CHANNEL_ID = int(os.getenv('REGISTRATION_CHANNEL_ID'))
EVENT_BLACKLIST_ROLE_ID = int(os.getenv('EVENT_BLACKLIST_ROLE_ID'))
MUTE_ROLE_ID = int(os.getenv('MUTE_ROLE_ID'))
HYPIXEL_API_KEY = "1b8246b7-69ce-426d-b71c-19d18832f02c"

# Event modes
VALID_EVENT_MODES = ['bedwars', 'bedfight', 'ranked']

# Embed colors
ERROR_COLOR = 0x535353       # Gray
MUTE_COLOR = 0xFF4F4F        # Red
UNMUTE_COLOR = 0x00FF7F      # Green
EVENT_COLOR = 0x00FF7F       # Green
BAN_COLOR = 0xA00000         # Dark red
LINK_COLOR = 0x535353        # Gray
BLACKLIST_COLOR = 0xFFA500   # Orange

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='-', intents=intents)

# Track event numbers
event_counters = {mode: 1 for mode in VALID_EVENT_MODES}

@bot.event
async def on_ready():
    print(f'{bot.user.name} is ready!')
    # Initialize event counters from existing categories
    for guild in bot.guilds:
        for category in guild.categories:
            if "Event #" in category.name:
                mode = category.name.split()[0].lower()
                if mode in VALID_EVENT_MODES:
                    try:
                        event_num = int(category.name.split('#')[-1])
                        event_counters[mode] = max(event_counters[mode], event_num + 1)
                    except (IndexError, ValueError):
                        continue

@bot.event
async def on_command_error(ctx, error):
    error_embed = discord.Embed(title="**ERROR!**", color=ERROR_COLOR)
    
    if isinstance(error, (commands.MissingRole, commands.MissingPermissions)):
        error_embed.description = "You don't have permission for this command."
    elif isinstance(error, commands.MemberNotFound):
        error_embed.description = "Member not found."
    elif isinstance(error, commands.RoleNotFound):
        error_embed.description = "Role not found."
    elif isinstance(error, commands.BadArgument):
        error_embed.description = "Invalid arguments provided."
    else:
        error_embed.description = f"An error occurred: {str(error)}"
    
    await ctx.send(embed=error_embed)

# Add to your .env file:
# RESULTS_CHANNEL_ID=your_channel_id_here

@bot.command(name='event_score')
@commands.has_role(TRUSTED_ROLE_ID)  # Or whatever role should have access
async def event_score(ctx, event_mode: str, event_number: str, *, winner: str):
    """Record event results and announce winners"""
    # Get results channel from env
    results_channel_id = int(os.getenv('RESULTS_CHANNEL_ID'))
    results_channel = bot.get_channel(results_channel_id)
    
    if not results_channel:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description="Results channel not found!",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)
        return
    
    if event_mode.lower() not in VALID_EVENT_MODES:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description=f"Invalid event mode. Valid modes: {', '.join(VALID_EVENT_MODES)}",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)
        return
    
    # Create and send results embed
    results_embed = discord.Embed(
        title=f"**A {event_mode.capitalize()} event has ended**",
        color=EVENT_COLOR  # Same green as other event embeds
    )
    results_embed.add_field(
        name="Winners:",
        value=winner,
        inline=False
    )
    results_embed.add_field(
        name="ID:",
        value=f"#{event_number}",
        inline=True
    )
    results_embed.add_field(
        name="Host:",
        value=ctx.author.mention,
        inline=True
    )
    
    try:
        await results_channel.send(embed=results_embed)
        success_embed = discord.Embed(
            description=f"Successfully scored a {event_mode} event #{event_number}!",
            color=0x00FF00  # Green checkmark color
        )
        await ctx.send(embed=success_embed)
    except Exception as e:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description=f"Failed to send results: {e}",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)

@event_score.error
async def event_score_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        error_embed = discord.Embed(
            title="**ERROR!**",
            description="You don't have permission to use this command.",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        error_embed = discord.Embed(
            title="**ERROR!**",
            description="Missing required arguments. Usage: `-event_score <mode> <number> <winner>`",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)
    else:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description=f"An error occurred: {error}",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)

import aiohttp
from async_timeout import timeout

# Add to your .env:
# GEXP_CHANNEL_ID=your_channel_id_for_gexp_results

async def fetch_json(session, url):
    async with session.get(url) as response:
        return await response.json()

@bot.command(name='gexp')
async def gexp_top(ctx):
    """Show top 10 GEXP earners this week (optimized)"""
    try:
        async with aiohttp.ClientSession() as session:
            # Get guild data first
            async with timeout(10):
                guild_data = await fetch_json(
                    session,
                    f"https://api.hypixel.net/guild?key={HYPIXEL_API_KEY}&name=teamtreenan"
                )
                
            if not guild_data.get('success'):
                await ctx.send(embed=discord.Embed(
                    title="**ERROR!**",
                    description="Failed to fetch guild data!",
                    color=ERROR_COLOR
                ))
                return
                
            # Process members in batches
            members = guild_data.get('guild', {}).get('members', [])
            gexp_data = []
            
            # Batch UUID lookups
            uuid_cache = {}
            batch_size = 5  # Process 5 members at a time
            
            for i in range(0, len(members), batch_size):
                batch = members[i:i+batch_size]
                tasks = []
                
                for member in batch:
                    uuid = member.get('uuid')
                    weekly_gexp = sum(member.get('expHistory', {}).values())
                    
                    if uuid not in uuid_cache:
                        tasks.append(
                            fetch_json(session, f"https://api.mojang.com/user/profile/{uuid}")
                        )
                    else:
                        gexp_data.append((uuid_cache[uuid], weekly_gexp))
                
                # Process batch responses
                try:
                    async with timeout(15):
                        responses = await asyncio.gather(*tasks, return_exceptions=True)
                        
                    for j, response in enumerate(responses):
                        if isinstance(response, dict):
                            ign = response.get('name', 'Unknown')
                            uuid = batch[j].get('uuid')
                            uuid_cache[uuid] = ign
                            gexp_data.append((ign, sum(batch[j].get('expHistory', {}).values())))
                            
                except asyncio.TimeoutError:
                    continue
                    
            # Sort and format results
            gexp_data.sort(key=lambda x: x[1], reverse=True)
            top_10 = gexp_data[:10]
            
            formatted = "\n".join(
                f"{i+1}. {name}: {gexp:,} GEXP" 
                for i, (name, gexp) in enumerate(top_10)
            )
            
            embed = discord.Embed(
                title="**Weekly GEXP Leaders**",
                description=f"```{formatted}```",
                color=0x535353
            )
            embed.set_footer(text="Results may take a moment to load")
            
            # Send to designated channel if available
            gexp_channel = bot.get_channel(int(os.getenv('GEXP_CHANNEL_ID', 0))) or ctx
            await gexp_channel.send(embed=embed)
            
    except Exception as e:
        await ctx.send(embed=discord.Embed(
            title="**ERROR!**",
            description=f"An error occurred: {str(e)}",
            color=ERROR_COLOR
        ))

@bot.command(name='membergexp')
async def member_gexp(ctx, member: discord.Member = None):
    """Show a member's weekly GEXP (optimized)"""
    member = member or ctx.author
    
    try:
        # Check linked role
        linked_role = ctx.guild.get_role(int(os.getenv('LINKED_ROLE_ID')))
        if not linked_role or linked_role not in member.roles:
            await ctx.send(embed=discord.Embed(
                title="**ERROR!**",
                description=f"{member.display_name} hasn't linked their account!",
                color=ERROR_COLOR
            ))
            return
            
        # Get cached data from -gexp command if available
        if hasattr(bot, 'last_gexp_data'):
            for ign, gexp in bot.last_gexp_data:
                if ign.lower() == member.nick.lower():
                    await ctx.send(embed=discord.Embed(
                        title=f"**Weekly GEXP for {ign}**",
                        description=f"```{gexp:,} GEXP```",
                        color=GEXP_COLOR
                    ))
                    return
                    
        # Fallback to direct lookup
        async with aiohttp.ClientSession() as session:
            async with timeout(10):
                uuid_data = await fetch_json(
                    session,
                    f"https://api.mojang.com/users/profiles/minecraft/{member.nick}"
                )
                
            if not uuid_data:
                await ctx.send(embed=discord.Embed(
                    title="**ERROR!**",
                    description="Couldn't find Minecraft account!",
                    color=ERROR_COLOR
                ))
                return
                
            async with timeout(10):
                guild_data = await fetch_json(
                    session,
                    f"https://api.hypixel.net/guild?key={HYPIXEL_API_KEY}&name=teamtreenan"
                )
                
            if not guild_data.get('success'):
                await ctx.send(embed=discord.Embed(
                    title="**ERROR!**",
                    description="Failed to fetch guild data!",
                    color=ERROR_COLOR
                ))
                return
                
            # Find member in guild data
            for guild_member in guild_data.get('guild', {}).get('members', []):
                if guild_member.get('uuid') == uuid_data.get('id'):
                    weekly_gexp = sum(guild_member.get('expHistory', {}).values())
                    await ctx.send(embed=discord.Embed(
                        title=f"**Weekly GEXP for {member.nick}**",
                        description=f"```{weekly_gexp:,} GEXP```",
                        color=0x535353
                    ))
                    return
                    
        await ctx.send(embed=discord.Embed(
            title="**ERROR!**",
            description="Player not found in guild data!",
            color=ERROR_COLOR
        ))
        
    except Exception as e:
        await ctx.send(embed=discord.Embed(
            title="**ERROR!**",
            description=f"An error occurred: {str(e)}",
            color=ERROR_COLOR
        ))

@bot.command(name='link')
async def link(ctx, mc_username: str):
    """Link your Minecraft account and get the verified role"""
    if ctx.channel.id != REGISTRATION_CHANNEL_ID:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description="This command can only be used in the registration channel.",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)
        return
    
    try:
        # Get role ID from .env
        LINKED_ROLE_ID = int(os.getenv('LINKED_ROLE_ID'))
        linked_role = ctx.guild.get_role(LINKED_ROLE_ID)
        
        if not linked_role:
            error_embed = discord.Embed(
                title="**ERROR!**",
                description="Verified role not configured!",
                color=ERROR_COLOR
            )
            await ctx.send(embed=error_embed)
            return

        # Step 1: Get Minecraft UUID
        uuid_response = requests.get(
            f"https://api.mojang.com/users/profiles/minecraft/{mc_username}",
            timeout=10
        )
        
        if uuid_response.status_code != 200:
            error_embed = discord.Embed(
                title="**ERROR!**",
                description="Minecraft account not found!",
                color=ERROR_COLOR
            )
            await ctx.send(embed=error_embed)
            return
            
        uuid_data = uuid_response.json()
        minecraft_uuid = uuid_data['id']
        
        # Step 2: Get Hypixel data
        hypixel_response = requests.get(
            f"https://api.hypixel.net/player?key={HYPIXEL_API_KEY}&uuid={minecraft_uuid}",
            timeout=15
        )
        
        if not hypixel_response.ok:
            error_embed = discord.Embed(
                title="**ERROR!**",
                description="Failed to verify Hypixel link!",
                color=ERROR_COLOR
            )
            await ctx.send(embed=error_embed)
            return
            
        hypixel_data = hypixel_response.json()
        
        # Step 3: Verify Discord link
        social_media = hypixel_data.get('player', {}).get('socialMedia', {})
        hypixel_discord = social_media.get('links', {}).get('DISCORD', "").lower()
        
        if not hypixel_discord:
            error_embed = discord.Embed(
                title="**ERROR!**",
                description="No Discord account linked!\n\nLink your account with:\n1. Go to Hypixel lobby\n2. Type `/profile`\n3. Click 'Social Media'\n4. Select Discord",
                color=ERROR_COLOR
            )
            await ctx.send(embed=error_embed)
            return
            
        # Step 4: Compare usernames
        user_discord_name = ctx.author.name.lower()
        hypixel_discord_clean = hypixel_discord.split('#')[0].lower()
        
        if hypixel_discord_clean != user_discord_name:
            error_embed = discord.Embed(
                title="**ERROR!**",
                description=f"Linked Discord ({hypixel_discord}) doesn't match yours ({ctx.author.name})!",
                color=ERROR_COLOR
            )
            await ctx.send(embed=error_embed)
            return
            
        # Step 5: Update nickname and assign role
        try:
            await ctx.author.edit(nick=mc_username)
            await ctx.author.add_roles(linked_role)
            
            success_embed = discord.Embed(
                title="**SUCCESS!**",
                description=(
                    f"You are now linked to {mc_username}"
                ),
                color=UNMUTE_COLOR
            )
            await ctx.send(embed=success_embed)
            
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="**ERROR!**",
                description="I need these permissions:\n- `Manage Nicknames`\n- `Manage Roles`",
                color=ERROR_COLOR
            )
            await ctx.send(embed=error_embed)
            
    except Exception as e:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description=f"An error occurred: {str(e)}",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)

@bot.command(name='forcelink')
@commands.has_role(MODERATOR_ROLE_ID)
async def forcelink(ctx, member: discord.Member, in_game_name: str):
    """Force change a member's nickname"""
    try:
        await member.edit(nick=in_game_name)
        success_embed = discord.Embed(
            title=f"**{member.display_name}'s nickname changed to {in_game_name}!**",
            color=LINK_COLOR
        )
        await ctx.send(embed=success_embed)
    except Exception as e:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description=f"Couldn't change nickname: {e}",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)

@bot.command(name='start_event')
@commands.has_role(TRUSTED_ROLE_ID)
async def start_event(ctx, event_mode: str):
    """Start a new event"""
    if event_mode.lower() not in VALID_EVENT_MODES:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description=f"Invalid event mode. Valid modes: {', '.join(VALID_EVENT_MODES)}",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)
        return
    
    event_mode = event_mode.lower()
    event_number = event_counters[event_mode]
    blacklist_role = ctx.guild.get_role(EVENT_BLACKLIST_ROLE_ID)
    
    # Create category
    category_name = f"{event_mode.capitalize()} Event #{event_number}"
    category = await ctx.guild.create_category(category_name)
    
    # Block blacklisted users
    if blacklist_role:
        await category.set_permissions(
            blacklist_role,
            view_channel=False,
            connect=False,
            send_messages=False,
            read_message_history=False
        )
    
    # Create channels
    text_channel = await ctx.guild.create_text_channel(
        f"{event_mode}-{event_number}",
        category=category
    )
    
    stage_channel = await ctx.guild.create_stage_channel(
        f"{event_mode.capitalize()} {event_number} LIVE",
        category=category
    )
    
    # Send announcement
    ping_role = ctx.guild.get_role(EVENT_PING_ROLE_ID)
    event_embed = discord.Embed(
        title=f"**A {event_mode.capitalize()} event has started!**",
        color=EVENT_COLOR
    )
    event_embed.add_field(name="Event Host", value=ctx.author.mention)
    event_embed.add_field(name="Event Date", value=datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    if ping_role:
        await text_channel.send(ping_role.mention, embed=event_embed)
    else:
        await text_channel.send(embed=event_embed)
    
    event_counters[event_mode] += 1
    await ctx.send(embed=event_embed)

@bot.command(name='end_event')
@commands.has_role(TRUSTED_ROLE_ID)
async def end_event(ctx, event_mode: str, event_number: int):
    """End an existing event"""
    category_name = f"{event_mode.capitalize()} Event #{event_number}"
    category = discord.utils.get(ctx.guild.categories, name=category_name)
    
    if not category:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description=f"Event {category_name} not found!",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)
        return
    
    # Delete all channels
    for channel in category.channels:
        try:
            await channel.delete()
        except Exception as e:
            error_embed = discord.Embed(
                title="**ERROR!**",
                description=f"Failed to delete channel: {e}",
                color=ERROR_COLOR
            )
            await ctx.send(embed=error_embed)
            return
    
    # Delete category
    try:
        await category.delete()
        end_embed = discord.Embed(
            title=f"**Ended {event_mode.capitalize()} Event #{event_number}!**",
            color=MUTE_COLOR
        )
        end_embed.add_field(name="Host", value=ctx.author.mention)
        await ctx.send(embed=end_embed)
    except Exception as e:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description=f"Failed to delete category: {e}",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)

@bot.command(name='ban')
@commands.has_role(MODERATOR_ROLE_ID)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    """Ban a member"""
    try:
        await member.ban(reason=reason)
        ban_embed = discord.Embed(
            title=f"**{member.display_name} has been banned!**",
            color=BAN_COLOR
        )
        ban_embed.add_field(name="Reason", value=reason)
        ban_embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=ban_embed)
    except Exception as e:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description=f"Failed to ban member: {e}",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)

@bot.command(name='mute')
@commands.has_role(MODERATOR_ROLE_ID)
async def mute(ctx, member: discord.Member, duration: str, *, reason="No reason provided"):
    """Mute a member"""
    mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
    if not mute_role:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description="Mute role not configured!",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)
        return
    
    # Parse duration
    try:
        time_amount = int(duration[:-1])
        unit = duration[-1].lower()
        
        if unit == 'm':
            delta = timedelta(minutes=time_amount)
        elif unit == 'h':
            delta = timedelta(hours=time_amount)
        elif unit == 'd':
            delta = timedelta(days=time_amount)
        else:
            raise ValueError
        
        expiry = datetime.utcnow() + delta
    except (ValueError, IndexError):
        error_embed = discord.Embed(
            title="**ERROR!**",
            description="Invalid duration format. Use like: 30m, 2h, 1d",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)
        return
    
    try:
        await member.add_roles(mute_role)
        mute_embed = discord.Embed(
            title=f"{member.display_name} has been muted",
            color=MUTE_COLOR
        )
        mute_embed.add_field(name="Duration", value=duration)
        mute_embed.add_field(name="Expires", value=expiry.strftime('%Y-%m-%d %H:%M UTC'))
        mute_embed.add_field(name="Reason", value=reason, inline=False)
        mute_embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=mute_embed)
    except Exception as e:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description=f"Failed to mute member: {e}",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)

@bot.command(name='unmute')
@commands.has_role(MODERATOR_ROLE_ID)
async def unmute(ctx, member: discord.Member):
    """Unmute a member"""
    mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
    if not mute_role:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description="Mute role not configured!",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)
        return
    
    if mute_role not in member.roles:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description=f"{member.display_name} is not muted!",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)
        return
    
    try:
        await member.remove_roles(mute_role)
        unmute_embed = discord.Embed(
            title=f"{member.display_name} has been unmuted",
            color=UNMUTE_COLOR
        )
        unmute_embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=unmute_embed)
    except Exception as e:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description=f"Failed to unmute member: {e}",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)

@bot.command(name='event_blacklist')
@commands.has_role(MODERATOR_ROLE_ID)
async def event_blacklist(ctx, member: discord.Member):
    """Add member to event blacklist"""
    blacklist_role = ctx.guild.get_role(EVENT_BLACKLIST_ROLE_ID)
    if not blacklist_role:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description="Event blacklist role not configured!",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)
        return
    
    try:
        await member.add_roles(blacklist_role)
        blacklist_embed = discord.Embed(
            title=f"**{member.display_name} added to event blacklist!**",
            color=BLACKLIST_COLOR
        )
        blacklist_embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=blacklist_embed)
    except Exception as e:
        error_embed = discord.Embed(
            title="**ERROR!**",
            description=f"Failed to blacklist member: {e}",
            color=ERROR_COLOR
        )
        await ctx.send(embed=error_embed)

bot.run(TOKEN)