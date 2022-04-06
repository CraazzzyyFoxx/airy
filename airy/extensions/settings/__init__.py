from __future__ import annotations

import asyncio
import logging
import typing as t

import lightbulb

from airy.core import AirySlashContext
from airy.core import models
from airy.core.models.components import *
from airy.etc import ColorEnum, EmojisEnum
from airy.etc.settings_static import *

logger = logging.getLogger(__name__)

settings = lightbulb.Plugin("Settings")


def get_key(dictionary: dict, value: t.Any) -> t.Any:
    """
    Get key from value in dict, too lazy to copy this garbage
    """
    return list(dictionary.keys())[list(dictionary.values()).index(value)]


class SettingsView(models.AuthorOnlyView):
    """God objects go brr >_<"""

    def __init__(
        self,
        ctx: lightbulb.Context,
        *,
        timeout: t.Optional[float] = 300,
        ephemeral: bool = False,
        autodefer: bool = False,
    ) -> None:
        super().__init__(ctx, timeout=timeout, autodefer=autodefer)

        # Last received context object
        self.last_ctx: t.Optional[miru.Context] = None
        # Last component interacted with
        self.last_item: t.Optional[miru.Item] = None

        # Last value received as input
        self.value: t.Optional[str] = None
        # If True, provides the menu ephemerally
        self.ephemeral: bool = ephemeral

        self.flags = hikari.MessageFlag.EPHEMERAL if self.ephemeral else hikari.MessageFlag.NONE
        self.input_event: asyncio.Event = asyncio.Event()

        # Mapping of custom_id/label, menu action
        self.menu_actions = {
            "Main": self.settings_main,
            # "Reports": self.settings_report,
            # "Moderation": self.settings_mod,
            # "Auto-Moderation": self.settings_automod,
            # "Auto-Moderation Policies": self.settings_automod_policy,
            # "Logging": self.settings_logging,
            # "Starboard": self.settings_starboard,
            "Quit": self.quit_settings,
        }

    # Transitions
    def add_buttons(self, buttons: t.Sequence[miru.Button], parent: t.Optional[str] = None, **kwargs) -> None:
        """Add a new set of buttons, clearing previous components."""
        self.clear_items()

        if parent:
            self.add_item(BackButton(parent, **kwargs))
        else:
            self.add_item(QuitButton())

        for button in buttons:
            self.add_item(button)

    def select_screen(self, select: OptionsSelect, parent: t.Optional[str] = None, **kwargs) -> None:
        """Set view to a new select screen, clearing previous components."""
        self.clear_items()

        if not isinstance(select, OptionsSelect):
            logging.warning("Stop being an idiot, pass an OptionSelect, thx c:")

        self.add_item(select)

        if parent:
            self.add_item(BackButton(parent))
        else:
            self.add_item(QuitButton())

    async def error_screen(self, embed: hikari.Embed, parent: str, **kwargs) -> None:
        """
        Show an error screen with only a back button, and wait for input on it.
        """
        assert self.last_ctx is not None
        self.clear_items()
        self.add_item(BackButton(parent=parent, **kwargs))
        await self.last_ctx.edit_response(embed=embed, components=self.build(), flags=self.flags)
        await self.wait_for_input()

    async def on_timeout(self) -> None:
        """Stop waiting for input events after the view times out."""
        self.value = None
        self.input_event.set()

        if not self.last_ctx:
            return

        for item in self.children:
            assert isinstance(item, (miru.Button, miru.Select))
            item.disabled = True

        try:
            await self.last_ctx.edit_response(components=self.build(), flags=self.flags)
        except hikari.NotFoundError:
            pass

    async def wait_for_input(self) -> None:
        """Wait until a user input is given, then reset the event.
        Other functions should check if view.value is None and return if so after waiting for this event."""
        self.input_event.clear()
        await self.input_event.wait()

        if self._stopped.is_set():
            raise asyncio.CancelledError

    async def quit_settings(self) -> None:
        """Exit settings menu."""

        assert self.last_ctx is not None
        for item in self.children:
            assert isinstance(item, (miru.Button, miru.Select))
            item.disabled = True

        try:
            await self.last_ctx.edit_response(components=self.build(), flags=self.flags)
        except hikari.NotFoundError:
            pass

        self.value = None
        self.stop()
        self.input_event.set()

    async def start_settings(self) -> None:
        await self.settings_main(initial=True)

    async def settings_main(self, initial: bool = False) -> None:
        """Show and handle settings main menu."""

        embed = hikari.Embed(
            title="Airy Configuration",
            description="""**Welcome to settings!**
                            Here you can configure various aspects of the bot, such as moderation settings, 
                            automod, logging options, and more. 
                            Click one of the buttons below to get started!""",
            color=ColorEnum.EMBED_BLUE,
        )

        buttons = [
            OptionButton(label="Moderation", emoji=EmojisEnum.MOD_SHIELD),
            OptionButton(label="Auto-Moderation", emoji="🤖"),
            OptionButton(label="Logging", emoji="🗒️"),
            OptionButton(label="Reports", emoji="📣", row=1),
            OptionButton(label="Starboard", emoji="⭐", row=1),
        ]

        self.add_buttons(buttons)
        if initial:
            resp = await self.ctx.respond(embed=embed, components=self.build(), flags=self.flags)
            message = await resp.message()
            self.start(message)
        else:
            assert self.last_ctx is not None
            await self.last_ctx.edit_response(embed=embed, components=self.build(), flags=self.flags)

        await self.wait_for_input()
        if self.value is None:
            return

        await self.menu_actions[self.value]()


T = t.TypeVar("T")


@settings.command
@lightbulb.set_max_concurrency(1, lightbulb.GuildBucket)
@lightbulb.add_checks(
    lightbulb.bot_has_guild_permissions(hikari.Permissions.SEND_MESSAGES, hikari.Permissions.READ_MESSAGE_HISTORY)
)
@lightbulb.add_checks(lightbulb.has_guild_permissions(hikari.Permissions.MANAGE_GUILD))
@lightbulb.command("settings", "Adjust different settings of the bot via an interactive menu.")
@lightbulb.implements(lightbulb.SlashCommand)
async def settings_cmd(ctx: AirySlashContext) -> None:
    view = SettingsView(ctx, timeout=300, ephemeral=True)
    await view.start_settings()


# def load(bot: Airy) -> None:
#     bot.add_plugin(settings)
#
#
# def unload(bot: Airy) -> None:
#     bot.remove_plugin(settings)
