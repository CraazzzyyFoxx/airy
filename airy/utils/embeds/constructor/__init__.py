from __future__ import annotations


import typing as t

import hikari
import lightbulb
import miru

from .enums import EmbedSettings, select_options


if t.TYPE_CHECKING:
    from airy.core import AirySlashContext


EmbedConstructorT = t.TypeVar("EmbedConstructorT", bound="EmbedConstructor")


class MainSelect(miru.Select[EmbedConstructorT]):
    def __init__(self, view: EmbedConstructorT):
        options = [value for name, value in select_options.items()
                   if view.is_action_enabled_for(name)]
        super().__init__(options=options, row=2)

    async def callback(self, context: miru.Context) -> None:
        await context.respond(self.values)


class DefaultEmbed(hikari.Embed):
    def __init__(self, view: EmbedConstructorT):
        super().__init__()
        self.view = view
        if view.is_action_enabled_for(EmbedSettings.TITLE):
            self.title = "itle"
        if view.is_action_enabled_for(EmbedSettings.DESCRIPTION):
            self.description = "Description"
        if view.is_action_enabled_for(EmbedSettings.AUTHOR):
            self.set_author(name="author")
        if view.is_action_enabled_for(EmbedSettings.IMAGE):
            self.set_image("https://cdn.discordapp.com/attachments/84319995256905728/252292324967710721/embed.png")


class EmbedConstructor(miru.View):
    def __init__(self,
                 ctx: AirySlashContext,
                 settings: EmbedSettings = EmbedSettings.ALL,
                 default_embed=None,
                 ephemeral=True):
        super().__init__()
        self._settings = settings
        self.ctx = ctx
        self._ephemeral: bool = ephemeral

        self._main_inter: t.Optional[hikari.MessageResponseMixin[t.Any]] = None
        self._inter: t.Optional[hikari.MessageResponseMixin[t.Any]] = None

        self.add_item(MainSelect(self))

        self.embed = DefaultEmbed(self)

    def get_default_items(self):
        self.add_item(MainSelect(self))

    def is_action_enabled_for(self, required_flag: EmbedSettings) -> bool:
        return (self._settings & required_flag) == required_flag

    @property
    def settings(self):
        return self._settings

    async def send_embed(self):
        self._main_inter = await self.ctx.respond(components=self.build(),
                                                  flags=hikari.MessageFlag.EPHEMERAL,
                                                  embed=self.embed)

    async def start_embed(self):
        await self.send_embed()
        await self.wait()
        return