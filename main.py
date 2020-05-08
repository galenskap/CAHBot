from discord.ext import commands
from utils import help
import discord

with open('token.txt', 'r') as f:
    token = [line.strip() for line in f]

production = False
try:
    open("devmode", "r").close()
except FileNotFoundError:
    production = True

main_prefix = "$" if production else "£"
cogs = [
    "jishaku",
    "cogs.cah",
    "guildmanager.cog",
    "cogs.errors"
]

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(main_prefix),
    case_insensitive=True,
    help_command=help.HelpCommand(),
    owner_ids=[317731855317336067, 438733159748599813, 261900651230003201],
    activity=discord.Activity(
        name="vos conneries passer",
        type=discord.ActivityType.watching
    ),  # We create a discord activity to start up with
    status=discord.Status.idle
)

bot.playing = 0
bot.admins = [] + bot.owner_ids
bot.skips = []

bot.main_prefix = main_prefix

bot.owners = [
    "PineappleFan#9955",
    "Minion3665#6456",
    "TheCodedProf#2583",
]
bot.helpers = {
    "Waldigo#6969": "Programming help",
    "nwunder#4018": "Programming help",
    "Mine#4200": "Tester & legend",
}

bot.colors = {
    "error": discord.Color(0xf44336),
    "success": discord.Color(0x8bc34a),
    "status": discord.Color(0x3f51b5),
    "info": discord.Color(0x212121)
}


@bot.event
async def on_ready():
    print(f'Logged in successfully as {bot.user}')
    success = 0
    for position, cog in enumerate(cogs):
        try:
            bot.load_extension(cog)
            success += 1
            print(f"Loaded {cog} (cog {position + 1}/{len(cogs)}, {success} successful)")
        except Exception as e:
            print(f"Failed to load {cog} (cog {position + 1}/{len(cogs)}), Here's the error: {e}")
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            name="your games of CAH",
            type=discord.ActivityType.watching,
        )
    )


@bot.command()
async def info(ctx):
    """View some information about the bot's owners"""
    embed = discord.Embed(
        title='Cards Against Humanity - Owner information',
        description="> **STAFF**\n**Co-owners:**\n" + "\n".join("> " + user for user in bot.owners) +
                    "\n**Helpers (Good people):**\n" + "\n".join(
                    "> " + user + ": " + reason for user, reason in bot.helpers.items()) +
                    "\n\n> **INVITE ME**\n[discordapp.com]"
                    "(https://discordapp.com/oauth2/authorize?client_id=679361555732627476&scope=bot&permissions=130048"
                    ")\n\n> **SERVER**\n[Cards Against Humanity Bot](https://discord.gg/bPaNnxe)",
        color=bot.colors["success"]
    )
    await ctx.send(embed=embed)


file = open('token.txt', 'r')
bot.tokens = [line.strip() for line in file]
file.close()

bot.run(bot.tokens[0])
