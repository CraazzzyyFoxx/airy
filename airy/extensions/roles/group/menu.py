from __future__ import annotations

import typing as t

import hikari
import miru

from airy.core import AirySlashContext, EntryRoleGroupModel, GroupRoleModel, MenuViewAuthorOnly
from airy.utils import ColorEnum, utcnow, helpers, RespondEmbed, MenuEmojiEnum


class RoleModal(miru.Modal):
    def __init__(self, ) -> None:
        super().__init__("Enter Role")
        self.data: t.Optional[str] = None
        self.item = miru.TextInput(label="Role (name or id)",
                                   placeholder="For example: Airy or 947964654230052876")
        self.add_item(self.item)

    async def callback(self, ctx: miru.ModalContext) -> None:
        self.data = ctx.values[self.item]


class MenuView(MenuViewAuthorOnly):
    def __init__(self, ctx: AirySlashContext, role: hikari.Role):
        super().__init__(ctx)
        self.role = role
        self.model: t.Optional[GroupRoleModel] = None
        for item in self.default_buttons:
            self.add_item(item)

    @property
    def default_buttons(self):
        return [AddRoleButton(), RemoveRoleButton(), DestroyButton(), QuitButton()]

    def get_kwargs(self):
        embed = hikari.Embed(title="Group Role",
                             color=ColorEnum.teal,
                             timestamp=utcnow())
        entries_description = []

        for index, entry in enumerate(self.model.entries, 1):
            entry_role = self.ctx.bot.cache.get_role(entry.role_id)
            entries_description.append(f"**{index}.** {entry_role.mention} (ID: {entry_role.id})")

        embed.description = '\n'.join(entries_description)
        return dict(embed=embed, components=self.build(), flags=self.flags)

    async def send(self, ctx: t.Union[miru.ViewContext, miru.ModalContext]):
        kwargs = self.get_kwargs()
        await ctx.edit_response(**kwargs)

    async def initial_send(self) -> None:
        self.model = (await GroupRoleModel
                      .filter(guild_id=self.ctx.guild_id, role_id=self.role.id)
                      .first()
                      .prefetch_related("entries"))

        if not self.model:
            await self.ctx.respond(embed=RespondEmbed.error("Provided group role missing"))
            return
        kwargs = self.get_kwargs()
        await self.ctx.interaction.create_initial_response(hikari.ResponseType.MESSAGE_CREATE, **kwargs)
        message = await self.ctx.interaction.fetch_initial_response()
        super(MenuView, self).start(message)


ViewT = t.TypeVar("ViewT", bound=MenuView)


class AddRoleButton(miru.Button[ViewT]):
    def __init__(self):
        super().__init__(label="Role", style=hikari.ButtonStyle.SUCCESS, emoji=MenuEmojiEnum.ADD)

    async def callback(self, context: miru.ViewContext) -> None:
        modal = RoleModal()
        await context.respond_with_modal(modal)
        await modal.wait()
        role = await helpers.is_role(context, modal.data)

        if role and role.id not in [entry.role_id for entry in self.view.model.entries]:
            entry_model = EntryRoleGroupModel(id_id=self.view.model.id, role_id=role.id)
            await entry_model.save()
            self.view.model.entries.related_objects.append(entry_model)

        await self.view.send(modal.get_response_context())


class RemoveRoleButton(miru.Button):
    def __init__(self):
        super().__init__(label="Role", style=hikari.ButtonStyle.SECONDARY, emoji=MenuEmojiEnum.REMOVE)

    async def callback(self, context: miru.ViewContext) -> None:
        modal = RoleModal()
        await context.respond_with_modal(modal)
        await modal.wait()
        role = await helpers.is_role(context, modal.data)

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
        await context.edit_response(embed=RespondEmbed.success("Group role was deleted"),
                                    components=[],
                                    flags=self.view.flags)
        self.view.stop()


class QuitButton(miru.Button[ViewT]):
    def __init__(self) -> None:
        super().__init__(style=hikari.ButtonStyle.DANGER, label="Quit", emoji=MenuEmojiEnum.SAVE)

    async def callback(self, context: miru.ViewContext) -> None:
        for item in self.view.children:
            item.disabled = True
        kwargs = self.view.get_kwargs()
        await context.edit_response(**kwargs)
        self.view.stop()
