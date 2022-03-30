from __future__ import annotations

import asyncio
from typing import List, TYPE_CHECKING
from typing import Optional
from typing import Union

import hikari
import miru
from miru.ext import nav


from airy.utils.embeds import RespondEmbed

if TYPE_CHECKING:
    from airy.core.models.context import AiryContext


__all__ = ("StopSelect",
           "AuthorOnlyView",
           "MenuViewAuthorOnly",
           "AuthorOnlyNavigator")


class StopSelect(miru.Select):
    """
    A select that stops the view after interaction.
    """

    async def callback(self, context: miru.Context) -> None:
        self.view.stop()


class AuthorOnlyView(miru.View):
    """
    A view that only works for the user who invoked it.
    """

    def __init__(self, ctx: AiryContext, *, timeout: Optional[float] = 120, autodefer: bool = True) -> None:
        super().__init__(timeout=timeout, autodefer=autodefer)
        self.ctx = ctx

    async def view_check(self, ctx: miru.Context) -> bool:
        if ctx.user.id != self.ctx.author.id:
            embed = RespondEmbed.error(
                title="Oops!",
                description="A magical barrier is stopping you from interacting with this component menu!",
            )
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)

        return ctx.user.id == self.ctx.author.id


class AuthorOnlyNavigator(nav.NavigatorView):
    """
    A navigator that only works for the user who invoked it.
    """

    def __init__(
        self,
        ctx: AiryContext,
        *,
        pages: List[Union[str, hikari.Embed]],
        buttons: Optional[List[nav.NavButton[nav.NavigatorView]]] = None,
        timeout: Optional[float] = 120,
        autodefer: bool = True,
    ) -> None:
        self.ctx = ctx
        super().__init__(pages=pages, buttons=buttons, timeout=timeout, autodefer=autodefer)

    async def view_check(self, ctx: miru.Context) -> bool:
        if ctx.user.id != self.ctx.author.id:
            embed = RespondEmbed.error(
                title="Oops!",
                description="A magical barrier is stopping you from interacting with this navigation menu!")
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)

        return ctx.user.id == self.ctx.author.id


class MenuViewAuthorOnly(AuthorOnlyView):
    def __init__(
            self,
            ctx: AiryContext,
            *,
            timeout: Optional[float] = 300,
            ephemeral: bool = False,
            autodefer: bool = False,
    ) -> None:
        super().__init__(ctx, timeout=timeout, autodefer=autodefer)

        # Last received context object
        self.last_ctx: Optional[miru.Context] = None
        # Last component interacted with
        self.last_item: Optional[miru.Item] = None

        # Last value received as input
        self.value: Optional[str] = None
        # If True, provides the menu ephemerally
        self.ephemeral: bool = ephemeral

        self.flags = hikari.MessageFlag.EPHEMERAL if self.ephemeral else hikari.MessageFlag.NONE
        self.input_event: asyncio.Event = asyncio.Event()


class MenuView(miru.View):
    def __init__(
            self,
            ctx: AiryContext,
            *,
            timeout: Optional[float] = 300,
            ephemeral: bool = False,
            autodefer: bool = False,
    ) -> None:
        super().__init__(timeout=timeout, autodefer=autodefer)
        self.ctx = ctx
        # Last received context object
        self.last_ctx: Optional[miru.Context] = None
        # Last component interacted with
        self.last_item: Optional[miru.Item] = None

        # Last value received as input
        self.value: Optional[str] = None
        # If True, provides the menu ephemerally
        self.ephemeral: bool = ephemeral

        self.flags = hikari.MessageFlag.EPHEMERAL if self.ephemeral else hikari.MessageFlag.NONE
        self.input_event: asyncio.Event = asyncio.Event()
