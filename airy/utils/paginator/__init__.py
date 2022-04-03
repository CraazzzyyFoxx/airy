from __future__ import annotations

from typing import Any, Dict, Optional, Union, List, TYPE_CHECKING

import hikari
import miru

from airy.utils import ColorEnum

from . import menus
from .utils import Paginator, maybe_coroutine

from .buttons import (AiryPagesT,
                      FirstButton,
                      IndicatorButton,
                      LastButton,
                      NavButton,
                      AiryPagesT,
                      NextButton,
                      PrevButton,
                      StopButton,
                      )

if TYPE_CHECKING:
    from airy.core import AirySlashContext, AiryPrefixContext


class AiryPages(miru.View):
    def __init__(
            self,
            source: menus.PageSource,
            *,
            ctx: Union[AirySlashContext, AiryPrefixContext],
            check_embeds: bool = True,
            compact: bool = False,
    ):
        super().__init__()
        self.source: menus.PageSource = source
        self.check_embeds: bool = check_embeds
        self.ctx: AirySlashContext = ctx
        self._current_page: int = 0
        self.compact: bool = compact
        self._ephemeral: bool = False
        # The last interaction used, used for ephemeral handling
        self._inter: Optional[hikari.MessageResponseMixin[Any]] = None

        default_buttons = self.get_default_buttons
        for default_button in default_buttons:
            self.add_item(default_button)

    @property
    def ephemeral(self) -> bool:
        """
        Value determining if the navigator is sent ephemerally or not.
        This value will be ignored if the navigator is not sent on an interaction.
        """
        return self._ephemeral

    @property
    def inter(self) -> hikari.MessageResponseMixin[Any]:
        return self._inter

    @property
    def get_default_buttons(self: AiryPagesT) -> List[NavButton[AiryPagesT]]:
        """Returns the default set of buttons.

        Returns
        -------
        List[NavButton[NavigatorViewT]]
            A list of the default navigation buttons.
        """
        return [FirstButton(), PrevButton(), IndicatorButton(), NextButton(), LastButton(), StopButton()]

    @property
    def current_page(self) -> int:
        """
        The current page of the navigator, zero-indexed integer.
        """
        return self._current_page

    @current_page.setter
    def current_page(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError("Expected type int for property current_page.")

        # Ensure this value is always correct
        self._current_page = max(0, min(value, self.source.get_max_pages() - 1))

    async def _get_kwargs_from_page(self, page: int) -> Dict[str, Any]:
        value = await maybe_coroutine(self.source.format_page, self, page)

        content = value if isinstance(value, str) else ""
        embeds = [value] if isinstance(value, hikari.Embed) else []

        if self.ephemeral:
            return dict(content=content, embeds=embeds, components=self.build(), flags=hikari.MessageFlag.EPHEMERAL)
        else:
            return dict(content=content, embeds=embeds, components=self.build())

    async def send_page(self, context: miru.Context[Any], page_index: Optional[int] = None) -> None:
        """Send a page, editing the original message.

        Parameters
        ----------
        context : Context
            The context object that should be used to send this page
        page_index : Optional[int], optional
            The index of the page to send, if not specified, sends the current page, by default None
        """
        if page_index:
            self.current_page = page_index

        page = await self.source.get_page(self.current_page)

        for button in self.children:
            if isinstance(button, NavButton):
                await button.before_page_change()

        kwargs = await self._get_kwargs_from_page(page)
        self._inter = context.interaction  # Update latest inter
        await context.edit_response(**kwargs)

    async def interaction_check(self, ctx: miru.ViewContext) -> bool:
        if ctx.user and ctx.user.id == self.ctx.author.id:
            return True
        await ctx.respond('This pagination menu cannot be controlled by you, sorry!',
                          flags=hikari.MessageFlag.EPHEMERAL)
        return False

    async def on_timeout(self) -> None:
        if self.message is None:
            return

        for button in self.children:
            assert isinstance(button, NavButton)
            button.disabled = True

        if self._ephemeral and self._inter:
            await self._inter.edit_initial_response(components=self.build())
        else:
            await self.message.edit(components=self.build())

    async def on_error(self, error: Exception, item: miru.Item = None, context: miru.ViewContext = None) -> None:
        await context.respond('An unknown error occurred, sorry', flags=hikari.MessageFlag.EPHEMERAL)

    async def send(
            self,
            channel_or_interaction: Union[
                hikari.SnowflakeishOr[hikari.TextableChannel], hikari.MessageResponseMixin[Any]],
            start_at: int = 0,
            ephemeral: bool = False,
            responded: bool = False,
    ) -> None:
        """Start up the navigator, send the first page, and start listening for interactions.

        Parameters
        ----------
        channel_or_interaction : Union[hikari.SnowflakeishOr[hikari.PartialChannel], hikari.MessageResponseMixin[Any]]
            A channel or interaction to use to send the navigator.
        start_at : int
            If provided, the page number to start the pagination at.
        ephemeral : bool
            If an interaction was provided, determines if the navigator will be sent ephemerally or not.
        responded : bool
            If an interaction was provided, determines if the interaction was previously acknowledged or not.
        """
        self.current_page = start_at
        self._ephemeral = ephemeral if not isinstance(channel_or_interaction, (int, hikari.TextableChannel)) else False

        await self.source.prepare_once()
        page = await self.source.get_page(0)

        for button in self.children:
            if isinstance(button, NavButton):
                await button.before_page_change()

        kwargs = await self._get_kwargs_from_page(page)

        if isinstance(channel_or_interaction, (int, hikari.TextableChannel)):
            channel = hikari.Snowflake(channel_or_interaction)
            message = await self.app.rest.create_message(channel, **kwargs)
        else:
            self._inter = channel_or_interaction
            if not responded:
                await channel_or_interaction.create_initial_response(
                    hikari.ResponseType.MESSAGE_CREATE,
                    **kwargs,
                )
                message = await channel_or_interaction.fetch_initial_response()
            else:
                message = await channel_or_interaction.execute(**kwargs)

        self.start(message)


class FieldPageSource(menus.ListPageSource):
    """A page source that requires (field_name, field_value, inline_value) tuple items."""

    def __init__(self, entries: List[hikari.EmbedField], *, per_page: int = 12):
        super().__init__(entries, per_page=per_page)
        self.embed = hikari.Embed(colour=ColorEnum.blurple)

    async def format_page(self, menu, entries):
        self.embed._fields = []
        self.embed.description = None

        for entry in entries:
            self.embed._fields.append(entry)

        maximum = self.get_max_pages()
        if maximum > 1:
            self.embed.set_footer(text=f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)')

        return self.embed


class TextPageSource(menus.ListPageSource):
    def __init__(self, text, *, prefix='```', suffix='```', max_size=2000):
        pages = Paginator(prefix=prefix, suffix=suffix, max_size=max_size - 200)
        for line in text.split('\n'):
            pages.add_line(line)

        super().__init__(entries=pages.pages, per_page=1)

    async def format_page(self, menu, content):
        maximum = self.get_max_pages()
        if maximum > 1:
            return f'{content}\nPage {menu.current_page + 1}/{maximum}'
        return content


class SimplePageSource(menus.ListPageSource):
    async def format_page(self, menu, entries):
        pages = []
        for index, entry in enumerate(entries, start=menu.current_page * self.per_page):
            pages.append(f'{index + 1}. {entry}')

        maximum = self.get_max_pages()
        if maximum > 1:
            footer = f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)'
            menu.embed.set_footer(text=footer)

        menu.embed.description = '\n'.join(pages)
        return menu.embed


class SimplePages(AiryPages):
    """A simple pagination session reminiscent of the old Pages interface.

    Basically an embed with some normal formatting.
    """

    def __init__(self, entries, *, ctx: AirySlashContext, per_page: int = 12):
        super().__init__(SimplePageSource(entries, per_page=per_page), ctx=ctx)
        self.embed = hikari.Embed(colour=ColorEnum.blurple)
