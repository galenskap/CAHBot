import asyncio
import random
import discord
import typing
import re


class Player:
    def __init__(self, member, game):
        self.member = member
        self.score = 0
        self.cards = []
        self.first_card = 0
        self.second_card = 0
        self.coroutines = []
        if len(game.answer_cards) < 10:
            game.answer_cards += game.used_answer_cards.copy()
            game.used_answer_cards = []
        self.cards += random.sample(game.answer_cards, 10)
        for card in self.cards:
            game.answer_cards.remove(card)
            game.used_answer_cards.append(card)
        self.tsar_count = 0


class Game:
    def __init__(self, context, players, available_packs, enabled_packs, score_to_win: typing.Optional[int],
                 min_players,
                 max_players):
        enabled_packs = [pack.lower() for pack in enabled_packs]

        # Initialize basic game variables (Round number, which turn the players are on, etc.)
        self.active = False
        self.skip_round = True
        self.round_number = 0
        self.min = min_players
        self.max = max_players

        # Initialize context related game variables (Channel, creator, etc.)
        self.creator = context.author
        self.ctx = context

        # Initialize our possible question and answer cards
        self.answer_cards = []
        self.question_cards = []
        self.used_question_cards = []
        self.used_answer_cards = []

        for pack, questions, answers, _ in available_packs:
            if (pack in enabled_packs or "all" in enabled_packs) and f"-{pack}" not in enabled_packs:
                self.question_cards += questions  # Add our questions to the possible questions...
                self.answer_cards += answers  # ...and do the same for answers

        if len(self.answer_cards) < 15 or len(self.question_cards) == 0:
            for pack, questions, answers, _ in available_packs:
                if pack == "base":
                    self.question_cards += questions
                    self.answer_cards += answers

        # Create a Player for everyone who's playing
        self.players = [Player(member, self) for member in players]
        random.shuffle(self.players)

        if self.answer_cards:
            self.used_answer_cards = []

        # Initialize user-defined options, including the number of points to win
        self.score_to_win = score_to_win

    async def start(self):
        self.active = True
        self.round_number = 0
        while self.active and \
                (self.score_to_win is None or not any([user.score >= self.score_to_win for user in self.players])):
            self.round_number += 1
            self.skip_round = False
            await self.begin_round()
            if self.active:
                await asyncio.sleep(10)
        final_scores = "\n".join(
            [
                f'{user.member}: {user.score}' for user in
                sorted(self.players, key=lambda user: user.score, reverse=True)
            ]
        )
        await self.ctx.send(
            final_scores,
            title=f"Le jeu est terminé ! Voici les scores : \nScoreboard:",
            color=self.ctx.bot.colors["status"]
        )

    async def end(self, force, reason=None):
        if self.active:
            self.active = False
            if force:
                self.skip_round = True
                for player in self.players:
                    for coroutine in player.coroutines:
                        coroutine.cancel()
            await self.ctx.send(
                'Le jeu ' +
                ('s\'est arrêté' if force else 'et se terminera après ce round') +
                (f" à cause de {reason}." if reason else "."),
                color=self.ctx.bot.colors["success"]
            )

    async def quit(self, player):
        self.players.remove(player)
        for coroutine in player.coroutines:
            coroutine.cancel()
        embed = await self.ctx.send(
            f'{player.member} a quitté le jeu, bye bye...',
            color=self.ctx.bot.colors["success"]
        )
        if len(self.players) < self.min:
            if not self.active:
                return embed
            self.active = False
            embed = await self.ctx.send(
                f'Il n\'y a pas assez de joueurs pour continuer...',
                color=self.ctx.bot.colors["success"]
            )
            await self.end(True, "il n'y a  pas assez de joueurs")
        return embed

    async def begin_round(self):
        if len(self.question_cards) == 0:
            self.question_cards = self.used_question_cards.copy()
            self.used_question_cards = []
        question = self.question_cards.pop(random.randint(0, len(self.question_cards) - 1))
        self.used_question_cards.append(question)
        tsar = sorted(self.players, key=lambda plr: (plr.tsar_count, random.random))[0]
        tsar.tsar_count += 1
        scores = "\n".join(
            [
                f'{user.member}: {user.score}' for user in
                sorted(self.players, key=lambda user: user.score, reverse=True)
            ]
        )
        await self.ctx.send(
            scores,
            title=f"Tableau des scores (avant le round {self.round_number}" +
                  (f", {self.score_to_win} point{'s' if self.score_to_win != 1 else ''}"
                   f" pour gagner):" if self.score_to_win is not None else ")"),
            color=self.ctx.bot.colors["status"]
        )
        await asyncio.sleep(5)
        await self.ctx.send(
            f"{question}\n\n Vérifiez dans vos messages privés pour voir vos cartes. "
            f"Le tsar est {tsar.member.name}",
            color=self.ctx.bot.colors["info"]
        )

        coroutines = []
        for user in self.players:
            if user != tsar:
                cards = f"In {self.ctx.mention}\n\n{question}\nLe tsar est {tsar.member.name}\n\n" + \
                        "\n".join(
                            [f"{card_position + 1}: {card}" for card_position, card in enumerate(user.cards)]
                        )
                await user.member.send(
                    embed=discord.Embed(
                        title=f"Cards for {user.member}:", description=cards,
                        color=self.ctx.bot.colors["info"]
                    )
                )

                async def wait_for_message(player_to_wait_for):
                    messages_to_ignore = []

                    def wait_check(message: discord.Message):
                        try:
                            return 0 <= int(message.content) <= 10 \
                                   and message.author == player_to_wait_for.member \
                                   and message.guild is None \
                                   and message.content not in messages_to_ignore
                        except ValueError:
                            return False

                    await player_to_wait_for.member.send(
                        embed=discord.Embed(
                            title=f"Choisis un numéro de carte de 1 à 10. Tu as 2min30 pour te décider" +
                                  (" (1/2)" if question.count(r"\_\_") == 2 else ""),
                            color=self.ctx.bot.colors["info"]
                        )
                    )
                    try:
                        player_to_wait_for.first_card = (
                            await self.ctx.bot.wait_for('message', check=wait_check, timeout=150)
                        ).content
                        player_to_wait_for.first_card = player_to_wait_for.first_card \
                            if player_to_wait_for.first_card != "0" \
                            else "10"
                        messages_to_ignore = [
                            player_to_wait_for.first_card] if player_to_wait_for.first_card != "10" else \
                            ["0", "10"]
                    except asyncio.TimeoutError:
                        player_to_wait_for.coroutines = []
                        await self.quit(player_to_wait_for)
                        return await player_to_wait_for.member.send(
                            embed=discord.Embed(
                                title=f"Tu as été retiré du jeu pour "
                                      f"inactivité.",
                                color=self.ctx.bot.colors["success"]
                            )
                        )
                    if question.count(r"\_\_") == 2:
                        await player_to_wait_for.member.send(
                            embed=discord.Embed(
                                title=f"Choisis un numéro de carte de 1 à 10. Tu as 2min30 pour te décider. Tu"
                                      f" ne peux pas choisir la même carte que la 1ère (2/2)",
                                color=self.ctx.bot.colors["info"]
                            )
                        )
                        try:
                            player_to_wait_for.second_card = (
                                await self.ctx.bot.wait_for('message', check=wait_check, timeout=150)
                            ).content
                            player_to_wait_for.second_card = player_to_wait_for.second_card \
                                if player_to_wait_for.second_card != "0" \
                                else "10"
                        except asyncio.TimeoutError:
                            await self.quit(player_to_wait_for)
                            await player_to_wait_for.member.send(
                                embed=discord.Embed(
                                    title=f"Tu as été retiré du jeu pour "
                                          f"inactivité.",
                                    color=self.ctx.bot.colors["success"]
                                )
                            )
                    await player_to_wait_for.member.send(
                        embed=discord.Embed(
                            title=f"Attends que tous les joueurs aient choisi leurs cartes",
                            description=f'Le jeu continuera dans {self.ctx.mention}',
                            color=self.ctx.bot.colors["success"]
                        )
                    )
                    s = "s" if question.count(r'\_\_') == 2 else ""
                    await self.ctx.send(
                        f"{player_to_wait_for.member} a choisi ses carte{s}",
                        color=self.ctx.bot.colors["success"]
                    )
                    player_to_wait_for.coroutines = []
                    return None

                wfm_user = self.ctx.bot.loop.create_task(wait_for_message(user))
                coroutines.append(wfm_user)
                user.coroutines.append(wfm_user)
            else:
                await user.member.send(
                    embed=discord.Embed(
                        title=f"Tu es le tsar durant ce round",
                        description="Prends un bol de pop-corn et attend que tout le monde ait choisi ses cartes...",
                        color=self.ctx.bot.colors["info"]
                    )
                )

        if self.skip_round:
            for player in self.players:
                for coroutine in player.coroutines:
                    coroutine.cancel()
                player.coroutines = []
            return
        await asyncio.gather(*coroutines, return_exceptions=True)
        await self.ctx.send(
            "Tout le monde a soumis ses cartes"
        )
        if self.skip_round:
            for player in self.players:
                for coroutine in player.coroutines:
                    coroutine.cancel()
                player.coroutines = []
            return
        playing_users = self.players.copy()
        playing_users.remove(tsar)
        playing_users.sort(key=lambda user: random.random())

        responses = ""
        if question.count(r"\_\_") < 2:
            for user_position, user in enumerate(playing_users):
                responses += f'{user_position + 1}: {user.cards[int(user.first_card) - 1]}\n'
        else:
            for user_position, user in enumerate(playing_users):
                responses += f'{user_position + 1}: {user.cards[int(user.first_card) - 1]} ' \
                             f'| {user.cards[int(user.second_card) - 1]}\n'

        embed = discord.Embed(
            title=f'Choisis ta carte préférée, {tsar.member.name}',
            description=f'{question}\n\n{responses}',
            color=self.ctx.bot.colors["info"]
        )
        if self.skip_round:
            for player in self.players:
                for coroutine in player.coroutines:
                    coroutine.cancel()
                player.coroutines = []
            return
        await tsar.member.send(embed=embed)
        await self.ctx.channel.send(embed=embed)
        await self.ctx.send(
            title=f"Tu as 5 minutes pour répondre en messages privés ",
            color=self.ctx.bot.colors["success"]
        )

        def check(message: discord.Message):
            try:
                return 1 <= int(message.content) <= len(playing_users) \
                       and message.author == tsar.member \
                       and message.guild is None
            except ValueError:
                return False

        if not playing_users:
            return

        if self.skip_round:
            for player in self.players:
                for coroutine in player.coroutines:
                    coroutine.cancel()
                player.coroutines = []
            return

        winner = None
        try:
            wf_tsar = self.ctx.bot.loop.create_task(self.ctx.bot.wait_for('message', check=check, timeout=300))
            tsar.coroutines.append(wf_tsar)
            winner = (
                await wf_tsar
            ).content
            await tsar.member.send(
                embed=discord.Embed(
                    description=f"Selected. Le jeu continue dans {self.ctx.mention}",
                    color=self.ctx.bot.colors["success"]
                )
            )
        except asyncio.TimeoutError:
            if not playing_users:
                return
            winner = random.randint(1, len(playing_users))
            await self.quit(tsar)
            await tsar.member.send(
                embed=discord.Embed(
                    title=f"Vous avez été retiré de la partie pour inactivité.",
                    color=self.ctx.bot.colors["success"]
                )
            )
        except asyncio.CancelledError:
            return

        winner = playing_users[int(winner) - 1]

        winner.score += 1

        card_in_context = question
        if question.count(r"\_\_") == 0:
            card_in_context = card_in_context + " " + winner.cards[int(winner.first_card) - 1]
        card_in_context = card_in_context.replace(
            "\_\_", re.sub("\.$", "", winner.cards[int(winner.first_card) - 1]), 1)
        card_in_context = card_in_context.replace(
            "\_\_", re.sub("\.$", "", winner.cards[int(winner.second_card) - 1]), 1)
        await self.ctx.send(
            f"**{winner.member.mention}** with **{card_in_context}**",
            title=f"Et notre vainqueur est :",
            color=self.ctx.bot.colors["success"]
        )

        if question.count(r"\_\_") < 2:
            for player in self.players:
                if player != tsar:
                    player.cards.pop(int(player.first_card) - 1)
                    if len(self.answer_cards) == 0:
                        self.answer_cards = self.used_answer_cards.copy()
                        self.used_answer_cards = []
                    new_card = self.answer_cards.pop(random.randint(0, len(self.answer_cards) - 1))
                    player.cards.append(new_card)
                    self.used_answer_cards.append(new_card)
        else:
            for player in self.players:
                if player != tsar:
                    self.used_answer_cards.append(player.cards.pop(int(player.first_card) - 1))
                    if int(player.first_card) < int(player.second_card):
                        player.cards.pop(int(player.second_card) - 2)
                    else:
                        self.used_answer_cards.append(player.cards.pop(int(player.second_card) - 1))
                    for _ in range(2):
                        if len(self.answer_cards) == 0:
                            self.answer_cards = self.used_answer_cards.copy()
                            self.used_answer_cards = []
                        new_card = self.answer_cards.pop(random.randint(0, len(self.answer_cards) - 1))
                        player.cards.append(new_card)

        for player in self.players:
            for coroutine in player.coroutines:
                coroutine.cancel()
            player.coroutines = []
