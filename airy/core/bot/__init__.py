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
from lightbulb.app import BotApp
from tortoise import Tortoise

from airy.config import tortoise_config, bot_config, BotConfig
from airy.utils.time import utcnow, format_dt
from ..api.client import HttpServer
from ..log import log_config
from ..models.context import *
from ..scheduler import Scheduler
from ...utils import db_backup

log = logging.getLogger(__name__)


class Airy(BotApp, ABC):
    def __init__(self):
        super(Airy, self).__init__(
            bot_config.token,
            prefix="dev",
            default_enabled_guilds=bot_config.dev_guilds if bot_config.dev_guilds else (),
            intents=hikari.Intents.ALL,
            help_slash_command=False,
            logs=log_config,
            banner=None,
            cache_settings=hikari.impl.config.CacheSettings(
                components=(hikari.api.CacheComponents.GUILDS
                            | hikari.api.CacheComponents.GUILD_CHANNELS
                            | hikari.api.CacheComponents.MEMBERS
                            | hikari.api.CacheComponents.ROLES
                            | hikari.api.CacheComponents.INVITES
                            | hikari.api.CacheComponents.VOICE_STATES
                            | hikari.api.CacheComponents.MESSAGES),
                max_messages=1000,
            ),

        )
        self._started = asyncio.Event()
        self._user_id: t.Optional[hikari.Snowflake] = None
        self._is_started = False
        self.skip_first_db_backup = True  # Set to False to backup DB on bot startup too
        self._config = bot_config

        self.redis = aioredis.from_url(url="redis://localhost:6379")
        self._scheduler = Scheduler(self)
        # self.http_server = HttpServer()
        self.load_extensions_from("./airy/extensions")
        self.create_subscriptions()
        miru.load(self)

    @property
    def config(self) -> BotConfig:
        return self._config

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

    @property
    def scheduler(self) -> Scheduler:
        return self._scheduler

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

    @staticmethod
    async def connect_db() -> None:
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
        loop = asyncio.get_event_loop()
        # loop.create_task(self.http_server.start())
        await self.connect_db()
        await self.scheduler.start()

    async def on_started(self, event: hikari.StartedEvent) -> None:
        user = self.get_me()
        print(user)
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

    async def on_guild_available(self, _: hikari.GuildAvailableEvent) -> None:
        if self.is_started:
            return

    async def on_lightbulb_started(self, _: lightbulb.LightbulbStartedEvent) -> None:
        self._started.set()
        self._is_started = True

    async def on_message(self, event: hikari.MessageCreateEvent) -> None:
        if not event.content:
            return

        if self.is_ready and event.is_human:
            mentions = [f"<@{self.user_id}>", f"<@!{self.user_id}>"]

            if event.content in mentions:
                embed = hikari.Embed(
                    title="Beep Boop!",
                    description="Use `/` to access my commands and see what I can do!",
                    color=0xFEC01D,
                )
                user = self.get_me()
                embed.set_thumbnail(user.avatar_url if user else None)
                await event.message.respond(embed=embed)
                return

    async def backup_db(self) -> None:
        if self.skip_first_db_backup:
            logging.info("Skipping database backup for this day...")
            self.skip_first_db_backup = False
            return

        file = await db_backup.backup_database()
        await self.wait_until_started()

        if bot_config.info_channel:
            await self.rest.create_message(
                bot_config.info_channel,
                f"Database Backup: {format_dt(utcnow())}",
                attachment=file,
            )
            return logging.info("Database backup complete, database backed up to specified Discord channel.")

        logging.info("Database backup complete.")

    def run(self, *args, **kwargs) -> None:
        if os.name != "nt":
            try:
                import uvloop
            except ImportError:
                logging.warn(
                    "Failed to import uvloop! "
                    "Make sure to install it via 'pip install uvloop' for enhanced performance!"
                )
            else:
                uvloop.install()
        super().run()
