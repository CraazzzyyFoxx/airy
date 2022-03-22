from __future__ import annotations

import typing as t

import hikari
import lightbulb
import miru


from .views import AuthorOnlyView

__all__ = ["AiryContext", "AirySlashContext", "AiryMessageContext", "AiryUserContext", "AiryPrefixContext"]

if t.TYPE_CHECKING:
    from ..bot import Airy


class ConfirmView(AuthorOnlyView):
    """View that drives the confirm prompt button logic."""

    def __init__(
        self,
        lctx: lightbulb.Context,
        timeout: int,
        confirm_resp: t.Optional[t.Dict[str, t.Any]] = None,
        cancel_resp: t.Optional[t.Dict[str, t.Any]] = None,
    ) -> None:
        super().__init__(lctx, timeout=timeout)
        self.confirm_resp = confirm_resp
        self.cancel_resp = cancel_resp
        self.value: t.Optional[bool] = None

    @miru.button(label="Confirm", emoji="✔️", style=hikari.ButtonStyle.SUCCESS)
    async def confirm_button(self, button: miru.Button, ctx: miru.ViewContext) -> None:
        self.value = True
        if self.confirm_resp:
            await ctx.edit_response(**self.confirm_resp)
        self.stop()

    @miru.button(label="Cancel", emoji="✖️", style=hikari.ButtonStyle.DANGER)
    async def cancel_button(self, button: miru.Button, ctx: miru.ViewContext) -> None:
        self.value = False
        if self.cancel_resp:
            await ctx.edit_response(**self.cancel_resp)
        self.stop()


class AiryContext(lightbulb.Context):
    async def confirm(
        self,
        *args,
        confirm_payload: t.Optional[t.Dict[str, t.Any]] = None,
        cancel_payload: t.Optional[t.Dict[str, t.Any]] = None,
        timeout: int = 120,
        edit: bool = False,
        message: t.Optional[hikari.Message] = None,
        **kwargs,
    ) -> t.Optional[bool]:
        """Confirm a given action.

        Parameters
        ----------
        confirm_payload : Optional[Dict[str, Any]], optional
            Optional keyword-only payload to send if the user confirmed, by default None
        cancel_payload : Optional[Dict[str, Any]], optional
            Optional keyword-only payload to send if the user cancelled, by default None
        edit : bool
            If True, tries editing the initial response or the provided message.
        message : Optional[hikari.Message], optional
            A message to edit & transform into the confirm prompt if provided, by default None
        *args : Any
            Arguments for the confirm prompt response.
        **kwargs : Any
            Keyword-only arguments for the confirm prompt response.

        Returns
        -------
        bool
            Boolean determining if the user confirmed the action or not.
            None if no response was given before timeout.
        """

        view = ConfirmView(self, timeout, confirm_payload, cancel_payload)

        kwargs.pop("components", None)
        kwargs.pop("component", None)

        if message and edit:
            message = await message.edit(*args, components=view.build(), **kwargs)
        elif edit:
            resp = await self.edit_last_response(*args, components=view.build(), **kwargs)
        else:
            resp = await self.respond(*args, components=view.build(), **kwargs)
            message = await resp.message()

        assert message is not None
        view.start(message)
        await view.wait()
        return view.value

    @t.overload
    async def mod_respond(
        self,
        content: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED,
        delete_after: t.Union[int, float, None] = None,
        *,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[t.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[t.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[t.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        nonce: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        reply: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialMessage]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        mentions_reply: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            t.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            t.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> t.Union[lightbulb.ResponseProxy, hikari.Message]:
        ...

    @t.overload
    async def mod_respond(
        self,
        response_type: hikari.ResponseType,
        content: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED,
        delete_after: t.Union[int, float, None] = None,
        *,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[t.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[t.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[t.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        nonce: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        reply: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialMessage]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        mentions_reply: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            t.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            t.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> t.Union[lightbulb.ResponseProxy, hikari.Message]:
        ...

    async def mod_respond(self, *args, **kwargs) -> t.Union[lightbulb.ResponseProxy, hikari.Message]:
        # """Respond to the command while taking into consideration the current moderation command settings.
        # This should not be used outside the moderation plugin, and may fail if it is not loaded."""
        # mod = self.app.get_plugin("Moderation")
        #
        # if mod:
        #     is_ephemeral = (await mod.d.actions.get_settings(self.guild_id))["is_ephemeral"]
        #     flags = hikari.MessageFlag.EPHEMERAL if is_ephemeral else hikari.MessageFlag.NONE
        # else:
        #     flags = kwargs.get("flags") or hikari.MessageFlag.NONE

        return await self.respond(*args, **kwargs)

    @property
    def app(self) -> Airy:
        return super().app  # type: ignore

    @property
    def bot(self) -> Airy:
        return super().bot  # type: ignore


class AirySlashContext(AiryContext, lightbulb.SlashContext):
    """Custom SlashContext for Airy."""


class AiryUserContext(AiryContext, lightbulb.UserContext):
    """Custom UserContext for Airy."""


class AiryMessageContext(AiryContext, lightbulb.MessageContext):
    """Custom MessageContext for Airy."""


class AiryPrefixContext(AiryContext, lightbulb.PrefixContext):
    """Custom PrefixContext for Airy."""
