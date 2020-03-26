from discord.ext import commands
import discord
import typing
from utils import game, checks
from utils.miniutils.minidiscord.minidiscord import minictx
import asyncio
import time


class CardsAgainstHumanity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}  # type: typing.Dict[discord.TextChannel, game.Game]
        self.maxPlayers = 25
        self.minPlayers = 3
        bot.allowStart = True
        packs = {
            "marjorie": "Pack personnel",
            "base": "Just the basic, base pack",
            "spongebob": "SpongeBob themed cards!",
            "ex1": "The first extension pack.",
            "ex2": "The sequel to the first extension pack.",
            "ex3": "The sequel to the first extension pack, the sequel!",
            "ex4": "Yet another extension pack, but the green box.",
            "ex5": "more",
            "ex6": "Same again.",
            "ex7": "The last expansion pack.",
            "pax": "The PAX convention pack.",
            "base2": "An additional base pack / alternative extension",
            "anime": "Nani?",
            "discord": "A pack we made specially for you, containing cards that we wanted but couldn't quite make an "
                       "excuse to put in the other packs.",
        }
        self.packs = []
        for position, pack_data in enumerate(packs.items()):
            pack_to_read, pack_description = pack_data
            question_cards_in_pack = open(f"packs/{pack_to_read}b.txt", "r")
            answer_cards_in_pack = open(f"packs/{pack_to_read}w.txt", "r")
            self.packs.append(
                (
                    pack_to_read,
                    [card.strip() for card in question_cards_in_pack.readlines()],
                    [card.strip() for card in answer_cards_in_pack.readlines()],
                    pack_description
                )
            )
            question_cards_in_pack.close()
            answer_cards_in_pack.close()

    @commands.command(aliases=["start"])
    @minictx()
    @commands.guild_only()
    async def play(self, ctx, *whitelist: discord.Member):
        """Play a game
Options can be selected after running this command"""
        if not self.bot.allowStart:
            return await ctx.send(
                "Unfortunately, we're about to go down and are in maintenance mode waiting for the last few games to "
                "end, you can't start anything right now...",
                title="<:bloboutage:527721625374818305> Try again later...",
                color=self.bot.colors["error"]
            )

        if self.games.get(ctx.channel, None):
            return await ctx.send(
                f"Please wait until it's finished before starting a new one...",
                title=f"<:blobfrowningbig:527721625706168331> A game is already in progress",
                color=self.bot.colors["error"]
            )

        self.games[ctx.channel] = "setup"

        await ctx.send(
            f"Waiting for players... If you want to join type `{self.bot.main_prefix}join` in this channel. To start, "
            f"either wait 1 minute or run `{self.bot.main_prefix}begin` when there are enough players",
            color=self.bot.colors["status"]
        )
        players = [ctx.author]

        begin = [
            f"{self.bot.main_prefix}begin",
            f"{self.bot.main_prefix}go",
            f"{self.bot.main_prefix}forcestart",
            f"{self.bot.main_prefix}b",
            f"{self.bot.main_prefix}g",
            f"{self.bot.main_prefix}fs"
        ]

        def check(message):
            return message.channel == ctx.channel and (((message.content.lower().strip() in [
                "imin", "i'min", f"{self.bot.main_prefix}join", "iamin"
            ]) and (
                not whitelist or message.author in whitelist) and message.author not in players
                                                        and not message.author.bot
            ) or (
                message.content.lower().strip() in begin and
                len(players) >= self.minPlayers and
                message.author == ctx.author
            ))

        expiry = time.time() + 60
        while True:
            if len(players) >= self.maxPlayers:
                break
            try:
                player_to_add = await ctx.bot.wait_for("message", check=check, timeout=expiry - time.time())
                if player_to_add.content.lower().strip() in begin:
                    break
                players.append(player_to_add.author)
                self.bot.loop.create_task(
                    ctx.send(
                        f"{player_to_add.author.mention} you've been added to the game, "
                        f"there are now {len(players)} (out of a possible {self.maxPlayers}) players",
                        title="<:blobfingerguns:527721625605636099> Welcome!",
                        color=self.bot.colors["success"]
                    )
                )
            except asyncio.TimeoutError:
                break

        if len(players) < self.minPlayers:
            del self.games[ctx.channel]
            return await ctx.send(
                "Sadly there weren't enough players to start your game",
                title="<:blobfrowningbig:527721625706168331> Oh dear!",
                color=self.bot.colors["error"]
            )

        await ctx.send(
            f"What packs do you want to include? Type `all` to include every pack and `-` before a pack name to "
            f"exclude that pack. Invalid packs will be ignored "
            f"(run {self.bot.main_prefix}packs to see what packs are valid). "
            f"If you don't choose any packs within 60 seconds, we'll hook you up with the `base` pack",
            title=f'<:blobidea:527721625563693066> The game has been created. Before we start, we need to get a few '
                  f'game settings...',
            color=self.bot.colors["info"]
        )

        def check(message):
            return message.channel == ctx.channel and message.author == ctx.author

        packs = []
        try:
            packs = (await ctx.bot.wait_for("message", check=check, timeout=60)).content.split(" ")
        except asyncio.TimeoutError:
            pass

        await ctx.send(
            f"How many points should you need in order to win? We recommend 7, but you can choose any number. "
            f"If you pick 0, we'll give you an infinite game (and you'll need to run `$end` to stop it). If you don't "
            f"choose within 60 seconds, we'll bestow 7 points upon you",
            title="<:blobidea:527721625563693066> How'dya win?",
            color=self.bot.colors["info"]
        )

        def check(message):
            try:
                int(message.content)
                return message.channel == ctx.channel and message.author == ctx.author
            except ValueError:
                return False

        points = 7
        try:
            points = int((await ctx.bot.wait_for("message", check=check, timeout=60)).content)
        except asyncio.TimeoutError:
            pass

        if not self.bot.allowStart or not self.games.get(ctx.channel, None):
            try:
                del self.games[ctx.channel]
            except KeyError:
                pass
            return await ctx.send(
                "Unfortunately, we're about to go down and are in maintenance mode waiting for the last few games to "
                "end, you can't start anything right now...",
                title="<:bloboutage:527721625374818305> Try again later...",
                color=self.bot.colors["error"]
            )

        self.games[ctx.channel] = game.Game(
            ctx,
            players,
            self.packs,
            packs,
            points if points > 0 else None,
            self.minPlayers,
            self.maxPlayers
        )
        self.bot.playing += 1
        await self.games[ctx.channel].start()
        del self.games[ctx.channel]
        self.bot.playing -= 1

    @commands.command(aliases=["lstart", "legacyplay", "legacystart"])
    @minictx()
    @commands.guild_only()
    async def lplay(self,
                    ctx,
                    players: commands.Greedy[discord.Member],
                    score_to_win: typing.Optional[int] = 7,
                    *enabled_packs
                    ):
        """The legacy play command...
Play a game
Run %%lplay [@ping as many players as you like] [number of rounds, or enter 0 for unlimited (default unlimited)] [packs]
Optionally specify how many points a player needs to win (default is 7)
Note: press 0 to have an endless game
Optionally specify which packs to include (run %%packs to view all the options or enter all to go crazy)"""
        if not self.bot.allowStart:
            return await ctx.send(
                "Unfortunately, we're about to go down and are in maintenance mode waiting for the last few games to "
                "end, you can't start anything right now...",
                title="<:bloboutage:527721625374818305> Try again later...",
                color=self.bot.colors["error"]
            )
        players = [user for user in players if not user.bot]
        players.append(ctx.author)
        players = set(players)
        if len(players) < self.minPlayers:
            return await ctx.send(
                f'<:blobfrowningbig:527721625706168331> There too few players in this game. '
                f'Please ping a minimum of {self.minPlayers - 1} '
                f'people for a {self.minPlayers} player game',
                color=self.bot.colors["error"]
            )
        if len(players) > self.maxPlayers:
            return await ctx.send(
                f'<:blobfrowningbig:527721625706168331> There too many players in this game. '
                f'Please ping a maximum of {self.maxPlayers - 1} '
                f'people for a {self.maxPlayers} player game',
                color=self.bot.colors["error"]
            )

        if self.games.get(ctx.channel, None):
            return await ctx.send(
                f'<:blobfrowningbig:527721625706168331>A game is already in progress',
                color=self.bot.colors["error"]
            )

        if not self.bot.allowStart:
            return await ctx.send(
                "Unfortunately, we're about to go down and are in maintenance mode waiting for the last few games to "
                "end, you can't start anything right now...",
                title="<:bloboutage:527721625374818305> Try again later...",
                color=self.bot.colors["error"]
            )

        self.games[ctx.channel] = game.Game(
            ctx,
            players,
            self.packs,
            enabled_packs,
            score_to_win if score_to_win > 0 else None,
            self.minPlayers,
            self.maxPlayers
        )
        self.bot.playing += 1
        await self.games[ctx.channel].start()
        del self.games[ctx.channel]
        self.bot.playing -= 1

    @commands.command()
    @minictx()
    @commands.guild_only()
    async def end(self, ctx, force=False):
        """End the game
Optionally run '%%end True' to end the game instantly - NEW :tada:
Note- You must have manage channels or be playing to end the game"""
        channel_game = self.games.get(ctx.channel, None)
        if not channel_game or isinstance(channel_game, str):
            return await ctx.send(
                f"There isn't an active game in this channel",
                color=self.bot.colors["error"]
            )
        if (
                channel_game.players and ctx.author not in [user.member for user in channel_game.players]
        ) and not ctx.author.permissions_in(ctx.channel).manage_channels:
            return await ctx.send(
                "<:blobfrowningbig:527721625706168331> You aren't playing and you don't have manage channels, so you "
                "can't end this game...",
                color=self.bot.colors["error"]
            )
        await channel_game.end(force)

    @commands.command()
    @minictx()
    async def packs(self, ctx):
        """Shows a list of packs to enable and disable in the game
    They are added when using the %%play command"""
        await ctx.send(
            'Do $play {@ people} {packs} to activate specific packs. '
            'If no packs are chosen, base only will be selected. '
            'Alternatively, setting the pack to "all" will enable all packs.\n\n'
            + "\n".join(f"{pack[0]}: {pack[3]}" for pack in self.packs),
            title=f'Packs ( {len(self.packs)} )',
            color=self.bot.colors["error"]
        )

    @commands.command()
    @minictx()
    async def legal(self, ctx):
        """Shows all the legal notices about Cards Against Humanity Creative Commons. We know you won't do this."""
        embed = discord.Embed(
            title=f'Legal notices',
            description='**This bot is not associated with Cards Against Humanity LLC.**\n'
                        '[✔ NonCommercial] Firstly, this bot is not designed to make money.\n'
                        '[✔ Attribution] This bot is based off the concept by Cards Against Humanity LLC. \n'
                        '[✔ ShareAlike] This bot uses the same licence as the original game, '
                        '[Creative Commons by-nc-sa 2.0](https://creativecommons.org/licenses/by-nc-sa/2.0/)',
            color=self.bot.colors["error"]
        )
        await ctx.channel.send(embed=embed)

    @commands.command()
    @minictx()
    async def stats(self, ctx):
        """Shows the stats of the bot."""
        await ctx.send(
            f'Servers: {len(self.bot.guilds)}\n'
            f'Members: {len(self.bot.users)}\n'
            f'Games being played: {ctx.bot.playing}\n'
            f'Games on this version: {len(self.games)}',
            title=f'Stats',
            color=self.bot.colors["status"]
        )

    @commands.command(aliases=["endall"])
    @minictx()
    @commands.check(checks.is_owner)
    async def nostart(self, ctx, endall: bool = False, force: bool = False):
        """Stops new games being created, and ends all current games."""
        self.bot.allowStart = False
        self.games = {channel: value for channel, value in self.games.items() if value != "setup"}
        if endall:
            for playingGame in list(self.games.values()):
                await playingGame.end(force, "a maintenance break")
        await ctx.send(
            ((f'Forcefully e' if force else 'E') +
             f'nded all games & disabled starting new ones') if endall else f'Disabled starting new games',
            title=(f'All games have ended' if force else f'Games will end soon')
            if endall else 'Games will continue until they have run their course',
            color=self.bot.colors["error"]
        )
        await self.bot.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(
                name="my developers in maintenance mode",
                type=discord.ActivityType.listening,
            )
        )

    @commands.command()
    @minictx()
    @commands.check(checks.is_owner)
    async def allowstart(self, ctx):
        """Allows starting games again."""
        self.bot.allowStart = True
        await ctx.send(
            f'Games can be started again',
            title=f'You can play again :tada:',
            color=self.bot.colors["error"]
        )
        await self.bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                name="your games of CAH",
                type=discord.ActivityType.watching,
            )
        )


def setup(bot: commands.Bot):
    bot.add_cog(CardsAgainstHumanity(bot))
