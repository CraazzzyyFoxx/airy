from __future__ import annotations

import typing as t

import hikari
import miru

from airy.core import AirySlashContext, MenuViewAuthorOnly, ActionType, ActionMenusModel, ActionMenusButtonModel
from airy.utils import ColorEnum, utcnow, helpers, RespondEmbed, MenuEmojiEnum

from .enums import button_styles

class Modal(miru.Modal):
    def __init__(self, ) -> None:
        super().__init__("Enter action menus button")
        self.data: t.Optional[dict] = None
        self.add_item(miru.TextInput(label="Role (name or id)",
                                     placeholder="For example: Airy or 947964654230052876",
                                     min_length=1,
                                     custom_id="ROLE"))
        self.add_item(miru.TextInput(label="Enter button label",
                                     min_length=1,
                                     max_length=80,
                                     custom_id="LABEL"))
        self.add_item(miru.TextInput(label="Button style",
                                     placeholder="The style of the button. "
                                                 "It's can be Blurple, Grey, Red, Green",
                                     custom_id="STYLE"))

    async def callback(self, ctx: miru.ModalContext) -> None:
        self.data = {item.custom_id: value for item, value in ctx.values.items()}


class MenuView(MenuViewAuthorOnly):
    def __init__(self, ctx: AirySlashContext, channel_id: hikari.Snowflake, message_id: hikari.Snowflake):
        self.channel_id = channel_id
        self.message_id = message_id
        super().__init__(ctx)
        self.model: t.Optional[ActionMenusModel] = None
        for item in self.default_buttons:
            self.add_item(item)

    @property
    def default_buttons(self):
        return [AddButtonButton(), RemoveButtonButton(), DestroyButton(), PreviewButton(), QuitButton()]

    def get_kwargs(self):
        embed = hikari.Embed(title="Action Menus",
                             color=ColorEnum.teal,
                             timestamp=utcnow())
        entries_description = []

        for index, entry in enumerate(self.model.buttons, 1):
            entry_role = self.ctx.bot.cache.get_role(hikari.Snowflake(entry.payload))
            entries_description.append(f"**{index}.** {entry.label} - {entry_role.mention} "
                                       f"(Button ID: {entry.id}, Role ID: {entry_role.id})")

        embed.description = '\n'.join(entries_description)
        return dict(embed=embed, components=self.build(), flags=self.flags)

    async def send(self, ctx: t.Union[miru.ViewContext, miru.ModalContext]):
        kwargs = self.get_kwargs()
        await ctx.edit_response(**kwargs)

    async def initial_send(self) -> None:
        self.model = (await ActionMenusModel
                      .filter(guild_id=self.ctx.guild_id, messge_id=self.message_id, channel_id=self.channel_id)
                      .first()
                      .prefetch_related("buttons"))

        if not self.model:
            await self.ctx.respond(embed=RespondEmbed.error("Provided action menus missing"))
            return
        kwargs = self.get_kwargs()
        await self.ctx.interaction.create_initial_response(hikari.ResponseType.MESSAGE_CREATE, **kwargs)
        message = await self.ctx.interaction.fetch_initial_response()
        super(MenuView, self).start(message)


ViewT = t.TypeVar("ViewT", bound=MenuView)


class AddButtonButton(miru.Button[ViewT]):
    def __init__(self):
        super().__init__(style=hikari.ButtonStyle.SUCCESS, emoji=MenuEmojiEnum.ADD)

    async def callback(self, context: miru.ViewContext) -> None:
        modal = Modal()
        await context.respond_with_modal(modal)
        await modal.wait()
        role = await helpers.is_role(context, modal.data)

        if role and role.id not in [entry.role_id for entry in self.view.model.buttons]:
            entry_model = ActionMenusButtonModel(id_id=self.view.model.id, role_id=role.id)
            await entry_model.save()
            self.view.model.buttons.related_objects.append(entry_model)

        await self.view.send(modal.get_response_context())


class RemoveButtonButton(miru.Button):
    def __init__(self):
        super().__init__(style=hikari.ButtonStyle.SECONDARY, emoji=MenuEmojiEnum.REMOVE)

    async def callback(self, context: miru.ViewContext) -> None:
        modal = Modal()
        await context.respond_with_modal(modal)
        await modal.wait()
        if not modal.data:
            await self.view.send(modal.get_response_context())
            return

        role = await helpers.is_role(context, modal.data["ROLE"])
        if not role:
            await self.view.send(modal.get_response_context())
            return

        label = modal.data["LABEL"]
        style = modal.data["STYLE"]
        if style not in button_styles.keys():
            await self.view.send(modal.get_response_context())
            return

        if role.id in [entry.role_id for entry in self.view.model.entries]:
            if len(self.view.model.entries.related_objects) == 1:
                await self.view.model.delete()
                await context.respond(embed=RespondEmbed.success("Group role was deleted"))
            else:
                await EntryRoleGroupModel.filter(id_id=self.view.model.id, role_id=role.id).delete()
                for entry in self.view.model.entries.related_objects:
                    if entry.role_id == role.id:
                        self.view.model.entries.related_objects.remove(entry)

        await self.view.send(modal.get_response_context())


class DestroyButton(miru.Button[ViewT]):
    def __init__(self):
        super().__init__(label="Destroy", style=hikari.ButtonStyle.PRIMARY, emoji=MenuEmojiEnum.TRASHCAN)

    async def callback(self, context: miru.ViewContext) -> None:
        await self.view.model.delete()
        await context.respond(embed=RespondEmbed.success("Group role was deleted"),
                              components=[],
                              flags=self.view.flags)
        self.view.stop()


class PreviewButton(miru.Button[ViewT]):
    pass


class QuitButton(miru.Button[ViewT]):
    def __init__(self) -> None:
        super().__init__(style=hikari.ButtonStyle.DANGER, label="Quit", emoji=MenuEmojiEnum.SAVE)

    async def callback(self, context: miru.ViewContext) -> None:
        for item in self.view.children:
            item.disabled = True
        kwargs = self.view.get_kwargs()
        await context.edit_response(**kwargs)
        self.view.stop()
