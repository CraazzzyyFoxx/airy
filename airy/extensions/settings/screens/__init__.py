from __future__ import annotations

import asyncio
import typing as t

import hikari
import lightbulb
import miru

from lightbulb.utils.parser import CONVERTER_TYPE_MAPPING

from airy.core import OptionsSelect, Airy
from airy.utils import helpers
from .. import SettingsView, T


class BaseScreen:
    def __init__(self, settings_view: SettingsView):
        self.view = settings_view

    @property
    def ephemeral(self):
        return self.view.ephemeral

    @property
    def last_ctx(self):
        return self.view.last_ctx

    @property
    def app(self) -> Airy:
        return self.view.app  # type: ignore

    async def ask_settings(
            self,
            view: SettingsView,
            ctx: miru.Context,
            *,
            options: t.List[miru.SelectOption],
            return_type: T,
            embed_or_content: t.Union[str, hikari.Embed],
            placeholder: t.Optional[str] = None,
            ignore: t.Optional[t.List[t.Any]] = None,
            ephemeral: bool = False,
    ) -> t.Union[T, t.Any]:
        """Ask a question from the user, while taking into account the select menu limitations.

        Parameters
        ----------
        view : SettingsView
            The view to interact with and return interactions to.
        ctx : miru.Context
            The last context object seen by the view.
        options : t.List[miru.SelectOption]
            The list of options to present to the user.
        return_type : T
            The expected return type.
        embed_or_content : t.Union[str, hikari.Embed]
            The content or attached embed of the message to send.
        placeholder : str, optional
            The placeholder text on the select menu, by default None
        ignore : t.Optional[t.List[t.Any]], optional
            Values that will not be converted and returned directly, by default None
        ephemeral : bool, optional
            If the query should be done ephemerally, by default False

        Returns
        -------
        t.Union[T, t.Any]
            Returns T unless it is in ignore.

        Raises
        ------
        TypeError
            embed_or_content was not of type str or hikari.Embed
        asyncio.TimeoutError
            The query exceeded the given timeout.
        """

        if return_type not in CONVERTER_TYPE_MAPPING.keys():
            return TypeError(
                f"return_type must be of types: {' '.join(list(CONVERTER_TYPE_MAPPING.keys()))}, not {return_type}"
                # type: ignore
            )

        # Get appropiate converter for return type
        converter: lightbulb.BaseConverter = CONVERTER_TYPE_MAPPING[return_type](view.ctx)  # type: ignore
        flags = hikari.MessageFlag.EPHEMERAL if ephemeral else hikari.MessageFlag.NONE

        # If the select will result in a Bad Request or not
        invalid_select: bool = False
        if len(options) > 25:
            invalid_select = True
        else:
            for option in options:
                if len(option.label) > 100 or (option.description and len(option.description) > 100):
                    invalid_select = True

        if isinstance(embed_or_content, str):
            content = embed_or_content
            embeds = []
        elif isinstance(embed_or_content, hikari.Embed):
            content = ""
            embeds = [embed_or_content]
        else:
            raise TypeError(f"embed_or_content must be of type str or hikari.Embed, not {type(embed_or_content)}")

        if not invalid_select:
            view.clear_items()
            view.add_item(OptionsSelect(placeholder=placeholder, options=options))
            await ctx.edit_response(content=content, embeds=embeds, components=view.build(), flags=flags)
            await view.wait_for_input()

            if view.value:
                if ignore and view.value.casefold() in ignore:
                    return view.value.casefold()
                return await converter.convert(view.value)

            await view.quit_settings()

        else:
            await ctx.defer(flags=flags)
            if embeds:
                embeds[0].description = f"{embeds[0].description}\n\nPlease type your response below!"
            elif content:
                content = f"{content}\n\nPlease type your response below!"

            await ctx.edit_response(content=content, embeds=embeds, components=[], flags=flags)

            predicate = lambda e: e.author.id == ctx.user.id and e.channel_id == ctx.channel_id

            assert isinstance(ctx.app, Airy) and ctx.guild_id is not None

            try:
                event = await ctx.app.wait_for(hikari.GuildMessageCreateEvent, timeout=300.0, predicate=predicate)
            except asyncio.TimeoutError:
                return await view.quit_settings()

            me = ctx.bot.get_me()
            channel = event.get_channel()
            assert me is not None and channel is not None
            perms = lightbulb.utils.permissions_in(channel, me)

            if helpers.includes_permissions(perms, hikari.Permissions.MANAGE_MESSAGES):
                await helpers.maybe_delete(event.message)

            if event.content:
                if ignore and event.content.casefold() in ignore:
                    return event.content.casefold()
                return await converter.convert(event.content)

    async def start(self, parent: str = "MAIN"):
        return NotImplemented
