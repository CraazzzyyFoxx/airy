import typing as t

from enum import IntEnum

import hikari
import lightbulb
import miru

from airy.core import GroupRoleModel, HierarchyRoles, EntryRoleGroupModel, AiryPlugin, AirySlashContext
from airy.utils import utcnow, ColorEnum, RespondEmbed, FieldPageSource, AiryPages


class ChangedRoleStatus(IntEnum):
    ADDED = 0
    REMOVED = 1


class ChangedRole:
    def __init__(self, event: hikari.MemberUpdateEvent):
        raw = set(event.member.role_ids) - set(event.old_member.role_ids)
        if len(raw) == 1:
            self.id = int(raw.pop())
            self.status = ChangedRoleStatus.ADDED
        else:
            raw = set(event.old_member.role_ids) - set(event.member.role_ids)
            if len(raw) == 1:
                self.status = ChangedRoleStatus.REMOVED
                self.id = int(raw.pop())
            else:
                self.id = None
                self.status = None


class GroupRolePlugin(AiryPlugin):
    def __init__(self, name):
        super().__init__(name=name)

    def init(self):
        self.bot.subscribe(hikari.MemberUpdateEvent, self.on_member_update)

    async def on_member_update(self, event: hikari.MemberUpdateEvent):
        if event.member is None or event.old_member is None:
            return

        if len(event.member.role_ids) < 1:
            return

        changed_role = ChangedRole(event)
        if changed_role.id is None:
            return

        role_models = (await GroupRoleModel
                       .all()
                       .filter(guild_id=event.guild_id)
                       .prefetch_related("entries")
                       )

        for role_model in role_models:
            entries = {r_m.role_id for r_m in role_model.entries}

            diff = entries - set(event.member.role_ids)
            group_role = self.bot.cache.get_role(role_model.role_id)

            if diff == entries:
                await self.remove_role(event.member, role_model.role_id)

            elif changed_role.id == role_model.role_id:
                if role_model.hierarchy == HierarchyRoles.NONE:
                    return await self.add_role(event.member, role_model.role_id)

                elif role_model.hierarchy == HierarchyRoles.BottomTop:
                    min_role = self.bot.cache.get_role(event.member.role_ids[-1])
                    if group_role.position > min_role.position:
                        return await self.add_role(event.member, role_model.role_id)

                elif group_role.position <= event.member.get_top_role().position:
                    return await self.add_role(event.member, role_model.role_id)

                return await self.remove_role(event.member, role_model.role_id)

            else:
                if role_model.hierarchy == HierarchyRoles.TopDown:
                    if group_role.position < event.member.get_top_role().position:
                        await self.add_role(event.member, role_model.role_id)
                    else:
                        await self.remove_role(event.member, role_model.role_id)
                else:
                    min_role = self.bot.cache.get_role(event.member.role_ids[-1])
                    if group_role.position > min_role.position:
                        await self.add_role(event.member, role_model.role_id)
                    else:
                        await self.remove_role(event.member, role_model.role_id)

    async def add_role(self, member: hikari.Member, role_id: hikari.Snowflake):
        if role_id not in member.role_ids:
            await member.add_role(role_id)

    async def remove_role(self, member: hikari.Member, role_id: hikari.Snowflake):
        if role_id in member.role_ids:
            await member.remove_role(role_id)


group_role_plugin = GroupRolePlugin('GroupRole')


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


class Modal(miru.Modal):
    def __init__(self, ) -> None:
        super().__init__("Enter Role")
        self.data: t.Optional[str] = None
        self.item = miru.TextInput(label="Role name or Role id",
                                   placeholder="For example: Airy or 947964654230052876")
        self.add_item(self.item)

    async def callback(self, ctx: miru.ModalContext) -> None:
        self.data = ctx.values[self.item]


class State(IntEnum):
    ADD = 0
    DELETE = 1
    EXIT = 2
    DESTROY = 3


class MainView(miru.View):
    def __init__(self, ctx: AirySlashContext):
        super().__init__(timeout=20)
        self.ctx = ctx
        self.state: t.Optional[State] = None
        self.target_role: t.Optional[hikari.Role] = None

    async def prepare_role(self, data: str):
        roles = self.ctx.bot.cache.get_roles_view_for_guild(self.ctx.guild_id)

        def resolve(data):
            if data.isdigit():
                data = hikari.Snowflake(data)
                for role_id in roles.keys():
                    if role_id == data:
                        return roles[role_id]
            else:
                for role in roles.values():
                    if role.name == data:
                        return role

            return None

        role = resolve(data)
        if role:
            self.target_role = role
        else:
            roles = await self.ctx.bot.rest.fetch_roles(self.ctx.guild_id)
            role = resolve(data)
            self.target_role = role

    async def view_check(self, context: miru.ViewContext) -> bool:
        return self.ctx.author.id == context.author.id

    async def on_timeout(self):
        self.state = State.EXIT
        self.stop()

    @miru.button(label="Add Sub Role", style=hikari.ButtonStyle.PRIMARY)
    async def add(self, button: miru.Button, ctx: miru.ViewContext) -> None:
        self.state = State.ADD
        modal = Modal()
        await ctx.respond_with_modal(modal)
        await modal.wait()
        await self.prepare_role(modal.data)
        self.stop()

    @miru.button(label="Delete Sub Role", style=hikari.ButtonStyle.DANGER)
    async def delete(self, button: miru.Button, ctx: miru.ViewContext) -> None:
        self.state = State.DELETE
        modal = Modal()
        await ctx.respond_with_modal(modal)
        await modal.wait()
        await self.prepare_role(modal.data)
        self.stop()

    @miru.button(label="Destroy", style=hikari.ButtonStyle.SECONDARY)
    async def destroy(self, button: miru.Button, ctx: miru.ViewContext) -> None:
        self.state = State.DESTROY
        self.stop()

    @miru.button(label="Exit", style=hikari.ButtonStyle.SUCCESS)
    async def exit(self, button: miru.Button, ctx: miru.ViewContext) -> None:
        self.state = State.EXIT
        self.stop()


@group_role_plugin.command()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MANAGE_ROLES),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS)
)
@lightbulb.command("grouprole", "Shows configuration of the mute role.")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def group_role_(_: AirySlashContext):
    pass


@group_role_.child()
@lightbulb.option('group_role', 'Group role.', type=hikari.OptionType.ROLE)
@lightbulb.option('sub_role', 'Sub role.', type=hikari.OptionType.ROLE)
@lightbulb.option('hierarchy', 'Sub role.', choices=HierarchyRoles.to_choices())
@lightbulb.command("create", "Creates Group Role.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def group_role_create(ctx: AirySlashContext):
    model = GroupRoleModel(guild_id=ctx.guild_id,
                           role_id=ctx.options.group_role.id,
                           hierarchy=HierarchyRoles.try_value(ctx.options.hierarchy)
                           )
    await model.save()
    await EntryRoleGroupModel.create(id_id=model.id, role_id=ctx.options.sub_role.id)
    await ctx.respond(embed=RespondEmbed.success('Successfully created.'), flags=hikari.MessageFlag.EPHEMERAL)


@group_role_.child()
@lightbulb.option('group_role', 'Group role.', type=hikari.OptionType.ROLE, required=True)
@lightbulb.command("delete", "Deletes Group Role.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def group_role_delete(ctx: lightbulb.SlashContext):
    await GroupRoleModel.filter(guild_id=ctx.guild_id,
                                role_id=ctx.options.group_role.id).delete()
    await ctx.respond(embed=RespondEmbed.success('Successfully deleted.'), flags=hikari.MessageFlag.EPHEMERAL)


@group_role_.child()
@lightbulb.option('group_role', 'Group role.', type=hikari.OptionType.ROLE)
@lightbulb.option('sub_role', 'If the role is added, then it is removed and vice versa',
                  type=hikari.OptionType.ROLE,
                  required=False)
@lightbulb.command("manage", "Manages Group Role.", ephemeral=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def group_role_manage(ctx: AirySlashContext):
    group_role = ctx.options.group_role
    model: GroupRoleModel = (await GroupRoleModel
                             .filter(guild_id=ctx.guild_id, role_id=ctx.options.group_role.id)
                             .first()
                             .prefetch_related("entries"))

    if model is None:
        return await ctx.respond(embed=RespondEmbed.error("Group role does not exist"))

    if ctx.options.sub_role:
        if ctx.options.sub_role == ctx.options.group_role:
            return await ctx.respond(embed=RespondEmbed.error("Group role and Sub role must be different"))
        if ctx.options.sub_role.id in [entry.role_id for entry in model.entries]:
            if len(model.entries) == 1:
                await model.delete()
                return await ctx.respond(embed=RespondEmbed.success("Group role was deleted"))
            else:
                await EntryRoleGroupModel.filter(id_id=model.id, role_id=ctx.options.sub_role.id).delete()
                for entry in model.entries.related_objects:
                    if entry.role_id == ctx.options.sub_role.id:
                        model.entries.related_objects.remove(entry)
                return await ctx.respond(embed=MainEmbed(ctx, group_role, model.entries.related_objects))

    view = MainView(ctx)
    embed = MainEmbed(ctx, group_role, model.entries.related_objects)
    resp = await ctx.respond(embed=embed, components=view.build())
    view.start(await resp.message())
    while view.state != State.EXIT:
        await view.wait()
        if view.target_role:
            if view.state == State.ADD:
                if view.target_role.id not in [entry.role_id for entry in model.entries]:
                    entry_model = EntryRoleGroupModel(id_id=model.id, role_id=view.target_role.id)
                    await entry_model.save()
                    model.entries.related_objects.append(entry_model)
            elif view.state == State.DELETE:
                if view.target_role.id in [entry.role_id for entry in model.entries]:
                    if len(model.entries.related_objects) == 1:
                        await model.delete()
                        return await ctx.respond(embed=RespondEmbed.success("Group role was deleted"))

                    await EntryRoleGroupModel.filter(id_id=model.id, role_id=view.target_role.id).delete()
                    for entry in model.entries.related_objects:
                        if entry.role_id == view.target_role.id:
                            model.entries.related_objects.remove(entry)

            view = MainView(ctx)
            embed = MainEmbed(ctx, group_role, model.entries.related_objects)
            resp = await ctx.edit_last_response(embed=embed, components=view.build())
            view.start(resp)

        if view.state == State.DESTROY:
            await model.delete()
            return await ctx.edit_last_response("Group role was deleted", components=[], embed=None)

    await ctx.edit_last_response("Aborting...", components=[], embed=None)


@group_role_.child()
@lightbulb.command("list", "Shows list of the group roles.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def group_role_list(ctx: AirySlashContext):
    models = await GroupRoleModel.filter(guild_id=ctx.guild_id).all().prefetch_related("entries")
    if len(models) == 0:
        return await ctx.respond(embed=RespondEmbed.error("Group roles missing"))
    entries = []
    for model in models:
        entries_description = []
        role = ctx.bot.cache.get_role(model.role_id)
        for index, entry in enumerate(model.entries, 1):
            entry_role = ctx.bot.cache.get_role(entry.role_id)
            entries_description.append(f"**{index}.** {entry_role.mention} (ID: {entry_role.id})")

        description = f'{role.mention} (ID: {role.id}) \n>>> '
        description += '\n'.join(entries_description)
        entries.append(hikari.EmbedField(name='\u200b', value=description, inline=True))

    source = FieldPageSource(entries, per_page=2)
    source.embed.title = 'Group Roles'
    pages = AiryPages(source=source, ctx=ctx, compact=True)
    await ctx.respond(hikari.ResponseType.DEFERRED_MESSAGE_CREATE)
    await pages.send(ctx.interaction, responded=True)
