import asyncio
import logging
import random
import typing as t
from enum import IntEnum
from io import BytesIO
from pathlib import Path
from textwrap import fill

import aiohttp
import hikari
import Levenshtein as lev
import lightbulb
import miru

import airy
from airy.core import Airy, AirySlashContext, AiryUserContext
from airy.utils import helpers, utcnow, RespondEmbed, ColorEnum

logger = logging.getLogger(__name__)

fun = lightbulb.Plugin("Fun")


class WinState(IntEnum):
    PLAYER_X = 0
    PLAYER_O = 1
    TIE = 2


class TicTacToeButton(miru.Button):
    def __init__(self, x: int, y: int) -> None:
        super().__init__(style=hikari.ButtonStyle.SECONDARY, label="\u200b", row=y)
        self.x: int = x
        self.y: int = y

    async def callback(self, ctx: miru.Context) -> None:
        if isinstance(self.view, TicTacToeView) and self.view.current_player.id == ctx.user.id:
            view: TicTacToeView = self.view
            value: int = view.board[self.y][self.x]

            if value in (view.size, -view.size):  # If already clicked
                return

            if view.current_player.id == view.playerx.id:
                self.style = hikari.ButtonStyle.DANGER
                self.label = "X"
                self.disabled = True
                view.board[self.y][self.x] = -1
                view.current_player = view.playero
                embed = hikari.Embed(
                    title="Tic Tac Toe!",
                    description=f"It is **{view.playero.display_name}**'s turn!",
                    color=0x009DFF,
                )
                embed.set_thumbnail(view.playero.display_avatar_url)

            else:
                self.style = hikari.ButtonStyle.SUCCESS
                self.label = "O"
                self.disabled = True
                view.board[self.y][self.x] = 1
                view.current_player = view.playerx
                embed = hikari.Embed(
                    title="Tic Tac Toe!",
                    description=f"It is **{view.playerx.display_name}**'s turn!",
                    color=0x009DFF,
                )
                embed.set_thumbnail(view.playerx.display_avatar_url)

            winner = view.check_winner()

            if winner is not None:

                if winner == WinState.PLAYER_X:
                    embed = hikari.Embed(
                        title="Tic Tac Toe!",
                        description=f"**{view.playerx.display_name}** won!",
                        color=0x77B255,
                    )
                    embed.set_thumbnail(view.playerx.display_avatar_url)

                elif winner == WinState.PLAYER_O:
                    embed = hikari.Embed(
                        title="Tic Tac Toe!",
                        description=f"**{view.playero.display_name}** won!",
                        color=0x77B255,
                    )
                    embed.set_thumbnail(view.playero.display_avatar_url)

                else:
                    embed = hikari.Embed(title="Tic Tac Toe!", description=f"It's a tie!", color=0x77B255)
                    embed.set_thumbnail(None)

                for button in view.children:
                    assert isinstance(button, miru.Button)
                    button.disabled = True

                view.stop()

            await ctx.edit_response(embed=embed, components=view.build())


class TicTacToeView(miru.View):
    def __init__(self, size: int, playerx: hikari.Member, playero: hikari.Member, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current_player: hikari.Member = playerx
        self.size: int = size
        self.playerx: hikari.Member = playerx
        self.playero: hikari.Member = playero

        if size in [3, 4, 5]:
            # Create board
            self.board = [[0 for _ in range(size)] for _ in range(size)]

        else:
            raise TypeError("Invalid size specified. Must be either 3, 4, 5.")

        for x in range(size):
            for y in range(size):
                self.add_item(TicTacToeButton(x, y))

    async def on_timeout(self) -> None:
        for item in self.children:
            assert isinstance(item, miru.Button)
            item.disabled = True

        embed = hikari.Embed(
            title="Tic Tac Toe!",
            description="This game timed out! Try starting a new one!",
            color=0xFF0000,
        )
        assert self.message is not None
        await self.message.edit(embed=embed, components=self.build())

    def check_blocked(self) -> bool:
        """
        Check if the board is blocked
        """
        blocked_list = [False, False, False, False]

        # Check rows
        blocked = []
        for row in self.board:
            if not (-1 in row and 1 in row):
                blocked.append(False)
            else:
                blocked.append(True)

        if blocked.count(True) == len(blocked):
            blocked_list[0] = True

        # Check columns
        values = []
        for col in range(self.size):
            values.append([])
            for row in self.board:
                values[col].append(row[col])

        blocked = []
        for col in values:
            if not (-1 in col and 1 in col):
                blocked.append(False)
            else:
                blocked.append(True)
        if blocked.count(True) == len(blocked):
            blocked_list[1] = True

        # Check diagonals
        values = []
        diag_offset = self.size - 1
        for i in range(0, self.size):
            values.append(self.board[i][diag_offset])
            diag_offset -= 1
        if -1 in values and 1 in values:
            blocked_list[2] = True

        values = []
        diag_offset = 0
        for i in range(0, self.size):
            values.append(self.board[i][diag_offset])
            diag_offset += 1
        if -1 in values and 1 in values:
            blocked_list[3] = True

        if blocked_list.count(True) == len(blocked_list):
            return True

        return False

    def check_winner(self) -> t.Optional[WinState]:
        """
        Check if there is a winner
        """

        # Check rows
        for row in self.board:
            value = sum(row)
            if value == self.size:
                return WinState.PLAYER_O
            elif value == -self.size:
                return WinState.PLAYER_X

        # Check columns
        for col in range(self.size):
            value = 0
            for row in self.board:
                value += row[col]
            if value == self.size:
                return WinState.PLAYER_O
            elif value == -self.size:
                return WinState.PLAYER_X

        # Check diagonals
        diag_offset_1 = self.size - 1
        diag_offset_2 = 0
        value_1 = 0
        value_2 = 0
        for i in range(0, self.size):
            value_1 += self.board[i][diag_offset_1]
            value_2 += self.board[i][diag_offset_2]
            diag_offset_1 -= 1
            diag_offset_2 += 1
        if value_1 == self.size or value_2 == self.size:
            return WinState.PLAYER_O
        elif value_1 == -self.size or value_2 == -self.size:
            return WinState.PLAYER_X

        # Check if board is blocked
        if self.check_blocked():
            return WinState.TIE


@fun.command
@lightbulb.option("size", "The size of the board. Default is 3.", required=False, choices=["3", "4", "5"])
@lightbulb.option("user", "The user to play tic tac toe with!", type=hikari.Member)
@lightbulb.command("tictactoe", "Play tic tac toe with someone!", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def tictactoe(ctx: AirySlashContext, user: hikari.Member, size: t.Optional[str] = None) -> None:
    size_int = int(size or 3)
    helpers.is_member(user)
    assert ctx.member is not None

    if user.id == ctx.author.id:
        embed = RespondEmbed.error(title="Invoking self", description=f"I'm sorry, but how would that even work?",)
        await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return

    if not user.is_bot:
        embed = hikari.Embed(
            title="Tic Tac Toe!",
            description=f"**{user.display_name}** was challenged for a round of tic tac toe by **{ctx.member.display_name}**!\nFirst to a row of **{size_int} wins!**\nIt is **{ctx.member.display_name}**'s turn!",
            color=ColorEnum.EMBED_BLUE,
        )
        embed.set_thumbnail(ctx.member.display_avatar_url)

        view = TicTacToeView(size_int, ctx.member, user)
        proxy = await ctx.respond(embed=embed, components=view.build())
        view.start(await proxy.message())

    else:
        embed = RespondEmbed.error(title="Invalid user",
                                   description="Sorry, but you cannot play with a bot.. yet...")
        await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return


# @fun.command
# @lightbulb.option(
#     "show_global",
#     "To show the global avatar or not, if applicable",
#     bool,
#     required=False,
# )
# @lightbulb.option("user", "The user to show the avatar for.", hikari.Member, required=False)
# @lightbulb.command("avatar", "Displays a user's avatar for your viewing pleasure.", pass_options=True)
# @lightbulb.implements(lightbulb.SlashCommand)
# async def avatar(
#     ctx: AirySlashContext, user: t.Optional[hikari.Member] = None, show_global: t.Optional[bool] = None
# ) -> None:
#     if user:
#         helpers.is_member(user)
#     member = user or ctx.member
#     assert member is not None
#
#     if show_global == True:
#         avatar_url = member.avatar_url
#     else:
#         avatar_url = member.display_avatar_url
#
#     embed = hikari.Embed(title=f"{member.display_name}'s avatar:", color=helpers.get_color(member))
#     embed.set_image(avatar_url)
#     await ctx.respond(embed=embed)
#
#
# @fun.command
# @lightbulb.command("showavatar", "Displays the target's avatar for your viewing pleasure.", pass_options=True)
# @lightbulb.implements(lightbulb.UserCommand)
# async def avatar_context(ctx: AirySlashContext, target: hikari.Member) -> None:
#     helpers.is_member(target)
#     embed = hikari.Embed(title=f"{target.display_name}'s avatar:", color=helpers.get_color(target))
#     embed.set_image(target.display_avatar_url)
#     await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)


@fun.command
@lightbulb.option(
    "amount", "The amount of dice to roll. 1 by default.", required=False, type=int, min_value=1, max_value=20
)
@lightbulb.option(
    "sides",
    "The amount of sides a single die should have. 6 by default.",
    required=False,
    type=int,
    min_value=6,
    max_value=100,
)
@lightbulb.command("dice", "Roll the dice!", pass_options=True, auto_defer=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def dice(ctx: AirySlashContext, sides: t.Optional[int] = None, amount: t.Optional[int] = None) -> None:
    amount = amount or 1
    sides = sides or 6

    calc = " ".join([f"`[{i+1}: {random.randint(1, sides)}]`" for i in range(0, amount)])

    embed = hikari.Embed(
        title=f"🎲 Rolled the {'die' if amount == 1 else 'dice'}!",
        description=f"**Results (`{amount}d{sides}`):** {calc}",
        color=ColorEnum.EMBED_BLUE,
    )
    await ctx.respond(embed=embed)


@fun.command
@lightbulb.option("question", "The question you want to ask of the mighty 8ball.")
@lightbulb.command("8ball", "Ask a question, and the answers shall reveal themselves.", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def eightball(ctx: AirySlashContext, question: str) -> None:
    ball_path = Path(airy.ROOT_DIR, "etc", "text", "8ball.txt")
    answers = open(ball_path, "r").readlines()
    embed = hikari.Embed(
        title=f"🎱 {question}",
        description=f"{random.choice(answers)}",
        color=ColorEnum.EMBED_BLUE,
    )
    await ctx.respond(embed=embed)


def load(bot: Airy) -> None:
    bot.add_plugin(fun)


def unload(bot: Airy) -> None:
    bot.remove_plugin(fun)
