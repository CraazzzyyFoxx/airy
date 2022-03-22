import asyncio
import logging
import os
import pathlib
import typing as t

from abc import ABC

import aioredis
import hikari
import lightbulb
import miru

from lightbulb import errors, events
from lightbulb.app import BotApp
from tortoise import Tortoise

from airy.config import tortoise_config, bot_config
from ..models.context import *

log = logging.getLogger(__name__)


class Airy(BotApp):
    def __init__(self):
        super(Airy, self).__init__(
            bot_config.token,

            default_enabled_guilds=bot_config.dev_guilds,
            intents=hikari.Intents.ALL,
            help_slash_command=True,
            cache_settings=hikari.CacheSettings(
                components=hikari.CacheComponents.ALL,
                max_dm_channel_ids=300

            ),
            logs={
                "version": 1,
                "incremental": True,
                "loggers": {
                    "lightbulb": {"level": "INFO"},
                    "hikari.gateway": {"level": "INFO"},
                    "hikari.ratelimits": {"level": "INFO"},
                    "lavacord": {"level": "INFO"},
                    "airy": {"level": "INFO"}
                },
            }
        )
        self._started = asyncio.Event()
        self._user_id: t.Optional[hikari.Snowflake] = None
        self._is_started = False
        self.redis = aioredis.from_url(url="redis://localhost:6379")
        self.load_extensions_from("./airy/extensions")
        self.create_subscriptions()

        miru.load(self)

    @property
    def user_id(self) -> hikari.Snowflake:
        """The application user's ID."""
        if self._user_id is None:
            raise hikari.ComponentStateConflictError("The bot is not yet initialized, user_id is unavailable.")

        return self._user_id

    @property
    def is_ready(self) -> bool:
        """Indicates if the application is ready to accept instructions or not.
        Alias for BotApp.is_alive"""
        return self.is_alive

    @property
    def is_started(self) -> bool:
        """Boolean indicating if the bot has started up or not."""
        return self._is_started

    async def wait_until_started(self) -> None:
        """
        Wait until the bot has started up
        """
        await asyncio.wait_for(self._started.wait(), timeout=None)

    def create_subscriptions(self):
        self.subscribe(hikari.StartingEvent, self.on_starting)
        self.subscribe(hikari.StartedEvent, self.on_started)
        self.subscribe(hikari.GuildAvailableEvent, self.on_guild_available)
        self.subscribe(lightbulb.LightbulbStartedEvent, self.on_lightbulb_started)
        self.subscribe(hikari.StoppingEvent, self.on_stopping)
        # self.subscribe(hikari.GuildJoinEvent, self.on_guild_join)
        # self.subscribe(hikari.GuildLeaveEvent, self.on_guild_leave)

    async def connect_db(self) -> None:
        log.info("Connecting to Database...")
        await Tortoise.init(config=tortoise_config)
        await Tortoise.generate_schemas(safe=True)
        log.info("Connected to Database.")

    def load_extensions_from(
            self, *paths: t.Union[str, pathlib.Path], recursive: bool = False, must_exist: bool = True
    ) -> None:
        if len(paths) > 1 or not paths:
            for path_ in paths:
                self.load_extensions_from(path_, recursive=recursive, must_exist=must_exist)
            return

        path = paths[0]

        if isinstance(path, str):
            path = pathlib.Path(path)

        try:
            path = path.resolve().relative_to(pathlib.Path.cwd())
        except ValueError:
            raise ValueError(f"'{path}' must be relative to the working directory") from None

        if not path.is_dir():
            if must_exist:
                raise FileNotFoundError(f"'{path}' is not an existing directory")
            return

        for ext_path in path.iterdir():
            if ext_path.is_dir():
                glob = ext_path.rglob if recursive else ext_path.glob
                for ext_path_2 in glob("__init__.py"):
                    ext = str(ext_path_2.with_suffix("")).replace(os.sep, ".")
                    try:
                        self.load_extensions(ext)
                    except lightbulb.errors.ExtensionMissingLoad:
                        pass

    async def on_starting(self, _: hikari.StartingEvent) -> None:
        await self.connect_db()

    async def on_started(self, event: hikari.StartedEvent) -> None:
        user = self.get_me()
        self._user_id = user.id if user else None

    async def on_stopping(self, event: hikari.StoppingEvent) -> None:
        pass

    async def get_slash_context(
            self,
            event: hikari.InteractionCreateEvent,
            command: lightbulb.SlashCommand,
            cls: t.Type[lightbulb.SlashContext] = AirySlashContext,
    ) -> AirySlashContext:
        return await super().get_slash_context(event, command, cls)  # type: ignore

    async def get_user_context(
            self,
            event: hikari.InteractionCreateEvent,
            command: lightbulb.UserCommand,
            cls: t.Type[lightbulb.UserContext] = AiryUserContext,
    ) -> AiryUserContext:
        return await super().get_user_context(event, command, cls)  # type: ignore

    async def get_message_context(
            self,
            event: hikari.InteractionCreateEvent,
            command: lightbulb.MessageCommand,
            cls: t.Type[lightbulb.MessageContext] = AiryMessageContext,
    ) -> AiryMessageContext:
        return await super().get_message_context(event, command, cls)  # type: ignore

    async def get_prefix_context(
            self, event: hikari.MessageCreateEvent, cls: t.Type[lightbulb.PrefixContext] = AiryPrefixContext
    ) -> t.Optional[AiryPrefixContext]:
        return await super().get_prefix_context(event, cls)  # type: ignore

    async def on_guild_available(self, event: hikari.GuildAvailableEvent) -> None:
        if self.is_started:
            return

    async def on_lightbulb_started(self, event: lightbulb.LightbulbStartedEvent) -> None:
        self._started.set()
        self._is_started = True

    # async def on_message(self, event: hikari.MessageCreateEvent) -> None:
    #     if not event.content:
    #         return
    #
    #     if self.is_ready and event.is_human:
    #         mentions = [f"<@{self.user_id}>", f"<@!{self.user_id}>"]
    #
    #         if event.content in mentions:
    #             embed = hikari.Embed(
    #                 title="Beep Boop!",
    #                 description="Use `/` to access my commands and see what I can do!",
    #                 color=0xFEC01D,
    #             )
    #             user = self.get_me()
    #             embed.set_thumbnail(user.avatar_url if user else None)
    #             await event.message.respond(embed=embed)
    #             return
    #
    #         elif not event.content in await get_prefix(self, event.message) and event.content.startswith(
    #                 await get_prefix(self, event.message)):
    #             embed = hikari.Embed(
    #                 title="Uh Oh!",
    #                 description="This bot has transitioned to slash commands, to see a list of all commands, type `/`!\nIf you have any questions, or feel lost, feel free to join the [support server](https://discord.gg/KNKr8FPmJa)!",
    #                 color=const.ERROR_COLOR,
    #             )
    #             user = self.get_me()
    #             embed.set_thumbnail(user.avatar_url if user else None)
    #             await event.message.respond(embed=embed)
    #             return

    # async def on_guild_join(self, event: hikari.GuildJoinEvent) -> None:
    #     """Guild join behaviour"""
    #     await self.pool.execute("INSERT INTO global_config (guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING",
    #                             event.guild_id)
    #
    #     if event.guild.system_channel_id is None:
    #         return
    #
    #     me = event.guild.get_my_member()
    #     channel = event.guild.get_channel(event.guild.system_channel_id)
    #
    #     assert me is not None
    #     assert isinstance(channel, hikari.TextableGuildChannel)
    #
    #     if not channel or not (hikari.Permissions.SEND_MESSAGES & lightbulb.utils.permissions_in(channel, me)):
    #         return
    #
    #     try:
    #         embed = hikari.Embed(
    #             title="Beep Boop!",
    #             description="""I have been summoned to this server. Type `/` to see what I can do!\n\nIf you have `Manage Server` permissions, you may configure the bot via `/settings`!""",
    #             color=0xFEC01D,
    #         )
    #         embed.set_thumbnail(me.avatar_url)
    #         await channel.send(embed=embed)
    #     except hikari.ForbiddenError:
    #         pass
    #     logging.info(f"Bot has been added to new guild: {event.guild.name} ({event.guild_id}).")

    # async def on_guild_leave(self, event: hikari.GuildLeaveEvent) -> None:
    #     """Guild removal behaviour"""
    #     await self.pool.execute("""DELETE FROM global_config WHERE guild_id = $1""", event.guild_id)
    #     await self.db_cache.wipe(event.guild_id)
    #     logging.info(f"Bot has been removed from guild {event.guild_id}, correlating data erased.")

    def run(self, *args, **kwargs) -> None:
        if os.name != "nt":
            import uvloop

            uvloop.install()
        super().run()
