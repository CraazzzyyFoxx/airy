from __future__ import annotations

import typing as t

import hikari
import miru

from airy.core import QuitButton, AuthorOnlyView, AirySlashContext, EntryRoleGroupModel, GroupRoleModel
from airy.utils import ColorEnum, utcnow, helpers, RespondEmbed


class Modal(miru.Modal):
    def __init__(self, ) -> None:
        super().__init__("Enter Role")
        self.data: t.Optional[str] = None
        self.item = miru.TextInput(label="Role name or Role id",
                                   placeholder="For example: Airy or 947964654230052876")
        self.add_item(self.item)

    async def callback(self, ctx: miru.ModalContext) -> None:
        self.data = ctx.values[self.item]


class MainEmbed(hikari.Embed):
    def __init__(self, ctx: AirySlashContext, role: hikari.Role, entries: t.List[EntryRoleGroupModel]):
        super().__init__(title="Group Role",
                         color=ColorEnum.teal,
                         timestamp=utcnow())

        entries_description = []

        for index, entry in enumerate(entries, 1):
            entry_role = ctx.bot.cache.get_role(entry.role_id)
            entries_description.append(f"**{index}.** {entry_role.mention} (ID: {entry_role.id})")

        description = f'{role.mention} (ID: {role.id}) \n>>> '
        description += '\n'.join(entries_description)

        self.description = description


class MainView(AuthorOnlyView):
    def __init__(self, lctx: AirySlashContext, role: hikari.Role):
        super().__init__(lctx)
        self.role = role
        for item in self.default_buttons():
            self.add_item(item)

    def default_buttons(self):
        return [AddRoleButton(), RemoveRoleButton(), DestroyButton(), QuitButton()]

    async def send(self, ctx: miru.ViewContext):
        embed = hikari.Embed(title="Group Role",
                             color=ColorEnum.teal,
                             timestamp=utcnow())

        entries_description = []

        for index, entry in enumerate(self.model.entries, 1):
            entry_role = ctx.bot.cache.get_role(entry.role_id)
            entries_description.append(f"**{index}.** {entry_role.mention} (ID: {entry_role.id})")

        description = f'{self.role.mention} (ID: {self.role.id}) \n>>> '
        description += '\n'.join(entries_description)

        embed.description = description

        await ctx.respond(embed=embed, component=self.build())

    async def start(self, message: hikari.Message) -> None:
        self.model = await GroupRoleModel.filter(guild_id=self.lctx.guild_id, role_id=self.role.id).first().prefetch_related("entries")
        if not self.model:
            await self.lctx.respond(embed=RespondEmbed.error("Provided group role missing"))

        embed = hikari.Embed(title="Group Role",
                             color=ColorEnum.teal,
                             timestamp=utcnow())

        entries_description = []

        for index, entry in enumerate(self.model.entries, 1):
            entry_role = self.lctx.bot.cache.get_role(entry.role_id)
            entries_description.append(f"**{index}.** {entry_role.mention} (ID: {entry_role.id})")

        description = f'{self.role.mention} (ID: {self.role.id}) \n>>> '
        description += '\n'.join(entries_description)

        embed.description = description

        await self.lctx.respond(embed=embed, components=self.build())
        super(MainView, self).start(message)


ViewT = t.TypeVar("ViewT", bound=MainView)


class AddRoleButton(miru.Button[ViewT]):
    def __init__(self):
        super().__init__(label="Role", style=hikari.ButtonStyle.SUCCESS, emoji="✔️")

    async def callback(self, context: miru.ViewContext) -> None:
        modal = Modal()
        await context.respond_with_modal(modal)
        await modal.wait()
        role = await helpers.is_role(context, modal.data)

        if role:
            entry_model = EntryRoleGroupModel(id_id=self.view.model.id, role_id=role.id)
            await entry_model.save()
            self.view.model.entries.related_objects.append(entry_model)


class RemoveRoleButton(miru.Button):
    def __init__(self):
        super().__init__(label="Role", style=hikari.ButtonStyle.SUCCESS, emoji="✖️")

    async def callback(self, context: miru.ViewContext) -> None:
        modal = Modal()
        await context.respond_with_modal(modal)
        await modal.wait()
        role = await helpers.is_role(context, modal.data)

        if role.id in [entry.role_id for entry in self.view.model.entries]:
            if len(self.view.model.entries.related_objects) == 1:
                await self.view.model.delete()
                await context.respond(embed=RespondEmbed.success("Group role was deleted"))
                return

            await EntryRoleGroupModel.filter(id_id=self.view.model.id, role_id=self.view.target_role.id).delete()
            for entry in self.view.model.entries.related_objects:
                if entry.role_id == self.view.target_role.id:
                    self.view.model.entries.related_objects.remove(entry)


class DestroyButton(miru.Button[ViewT]):
    def __init__(self):
        super().__init__(label="Destroy", style=hikari.ButtonStyle.DANGER)

    async def callback(self, context: miru.ViewContext) -> None:
        await self.view.model.delete()
        await context.respond("Group role was deleted", components=[], embed=None)
        return
