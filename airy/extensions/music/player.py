from __future__ import annotations

import asyncio
import typing as t

import hikari
import lavacord
import miru

from airy.core import AirySlashContext, Airy
from airy.core.models.errors import *
from airy.utils import RespondEmbed, helpers
from .buttons import *
from .checks import _can_edit_player_buttons


class PlayerMenu(miru.View):
    def __init__(self, player: AiryPlayer):
        super().__init__()
        self.player: AiryPlayer = player

        self.currently_editing = asyncio.Lock()

        default_buttons = self.get_default_buttons
        for default_button in default_buttons():
            self.add_item(default_button)

    async def forced_release(self):
        await asyncio.sleep(5)
        self.currently_editing.release()

    async def __aenter__(self):
        self.forced_release_task: asyncio.Task = self.player.node.bot.create_task(self.forced_release())  # type: ignore
        await self.currently_editing.acquire()

    async def __aexit__(self, exc_type, exc, tb):
        self.currently_editing.release()
        self.forced_release_task.cancel()

    async def view_check(self, ctx: miru.ViewContext) -> bool:
        try:
            status = await _can_edit_player_buttons(ctx)
            return status
        except NoVoiceChannel:
            embed = RespondEmbed.error(title="You not in voice channel",
                                       description=f"You must be in the same channel with bot")
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return False
        except MissingPermissionsToEditPlayer:
            embed = RespondEmbed.error(title="You don't have permissions to interact with player ",
                                       description="This can be done by Administrators and people "
                                                   "whose track is currently playing. \n"
                                                   "But this does not apply to the `play` command.")
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return False

    def get_default_buttons(self) -> t.List[PlayerButton[PlayerMenuT]]:
        guild_id = self.player.voice_state.guild_id
        return [
            SkipToButton(guild_id),
            PreviousButton(guild_id),
            PlayOrPauseButton(guild_id),
            NextButton(guild_id),
            RepeatButton(guild_id),
        ]

    async def maybe_resend(self):
        if not self._message:
            return True

        channel = await self.bot.rest.fetch_channel(self.player.text_channel_id)
        return self.message.id != channel.last_message_id

    async def get_kwargs(self):
        for button in self.children:
            if isinstance(button, PlayerButton):
                await button.before_update_menu()
        return dict(embed=self.create_embed(), components=self.build())

    async def send_menu_component(self, ctx: miru.ViewContext):
        async with self:
            kwargs = await self.get_kwargs()

            if await self.maybe_resend():
                await self.player.resend_menu()
            else:
                await ctx.edit_response(**kwargs)

    async def send_menu(self):
        async with self:
            kwargs = await self.get_kwargs()

            if await self.maybe_resend():
                await self.player.resend_menu()
            else:
                await self._message.edit(**kwargs)

    async def stop(self) -> None:
        await helpers.maybe_delete(self._message)
        super().stop()

    def create_embed(self):
        track = self.player.queue.current_track
        if not track:
            return

        duration = f'{self.player.position}/{track.length}' if not track.is_stream else "Infinity"

        queue = self.player.queue
        embed = hikari.Embed(title=f'Currently playing', description=track.title, url=track.uri)
        embed.add_field(name='In queue', value=f'{len(self.player.queue)}', inline=True)
        embed.add_field(name='Position',
                        value=f'{queue.current_index}/{queue.current_index + len(queue)}', inline=True)
        embed.add_field(name='Duration', value=duration, inline=True)
        embed.add_field(name='Author', value=track.author, inline=True)
        embed.add_field(name='Queue Duration', value=queue.estimated_duration(self.player.position), inline=True)
        embed.add_field(name='Requester', value=f"<@{track.requester}>", inline=True)
        if track.thumbnail:
            embed.set_thumbnail(track.thumbnail)

        return embed

    async def start(
            self,
            channel_id: hikari.Snowflake,
    ) -> None:
        kwargs = await self.get_kwargs()
        message = await self.bot.rest.create_message(channel=channel_id, **kwargs)
        super().start(message)


class AiryPlayer(lavacord.Player):
    def __init__(self,
                 guild_id: hikari.Snowflake,
                 channel_id:
                 hikari.Snowflake,
                 *,
                 node: lavacord.Node,
                 text_channel: hikari.Snowflake = None):
        super().__init__(guild_id, channel_id, node=node)
        self.menu: t.Optional[PlayerMenu] = None
        self.text_channel_id = text_channel

    @property
    def text_channel(self) -> hikari.TextableGuildChannel:
        return self.node.bot.cache.get_guild_channel(self.text_channel_id)  # type: ignore

    @property
    def bot(self) -> Airy:
        return self.node.bot  # type: ignore

    async def resend_menu(self, ):
        await self.menu.stop()
        self.menu = PlayerMenu(self)
        await self.menu.start(self.text_channel_id)

    async def send_menu(self, ctx: AirySlashContext = None):
        if self.menu:
            await self.menu.send_menu()
        else:
            self.menu = PlayerMenu(self)
            await self.menu.start(ctx.channel_id)

    async def destroy(self):
        await super().destroy()
        await self.menu.stop()
