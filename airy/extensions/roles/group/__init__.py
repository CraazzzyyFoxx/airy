from enum import IntEnum

import hikari
import lightbulb

from airy.core import GroupRoleModel, HierarchyRoles, EntryRoleGroupModel, AiryPlugin, AirySlashContext
from airy.utils import RespondEmbed, FieldPageSource, AiryPages

from .menu import MenuView


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
        if event.member is None or event.old_member is None or len(event.member.role_ids) < 1:
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

    @staticmethod
    async def add_role(member: hikari.Member, role_id: hikari.Snowflake):
        if role_id not in member.role_ids:
            await member.add_role(role_id)

    @staticmethod
    async def remove_role(member: hikari.Member, role_id: hikari.Snowflake):
        if role_id in member.role_ids:
            await member.remove_role(role_id)


group_role_plugin = GroupRolePlugin('GroupRole')


@group_role_plugin.command()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.MANAGE_ROLES, hikari.Permissions.MODERATE_MEMBERS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MANAGE_ROLES, hikari.Permissions.MODERATE_MEMBERS),
)
@lightbulb.command("rolegroup", "grouprole")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def group_role_(_: AirySlashContext):
    pass


@group_role_.child()
@lightbulb.option('role', 'Group role.', type=hikari.OptionType.ROLE)
@lightbulb.option('subrole', 'Sub role.', type=hikari.OptionType.ROLE)
@lightbulb.option('hierarchy', 'Sub role.', choices=HierarchyRoles.to_choices())
@lightbulb.command("create", "Creates role with subrole and when a user has a subrole, he gets a group role",
                   pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def group_role_create(ctx: AirySlashContext, role: hikari.Role, subrole: hikari.Role, hierarchy: str):
    model = await GroupRoleModel.filter(guild_id=ctx.guild_id, role_id=role.id).first()
    if model:
        return await ctx.respond(embed=RespondEmbed.error("The specified group role already exists",
                                                          description="To edit an existing role use **/rolegroup manage**"),
                                 flags=hikari.MessageFlag.EPHEMERAL)

    model = GroupRoleModel(guild_id=ctx.guild_id,
                           role_id=role.id,
                           hierarchy=HierarchyRoles.try_value(hierarchy)
                           )

    await model.save()
    await EntryRoleGroupModel.get_or_create(defaults={"role_id": subrole.id}, id_id=model.id)

    description = f'{role.mention} (ID: {role.id}) \n>>> **{1}.** {subrole.mention} (ID: {subrole.id})'
    await ctx.respond(embed=RespondEmbed.success('Successfully created.', description=description))


@group_role_.child()
@lightbulb.option('role', 'Group role.', type=hikari.OptionType.ROLE)
@lightbulb.command("manage", "Manages the specified group role.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def group_role_manage(ctx: AirySlashContext, role: hikari.Role):
    view = MenuView(ctx, role)
    await view.initial_send()


@group_role_.child()
@lightbulb.command("list", "List all registered group role on this server.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def group_role_list(ctx: AirySlashContext):
    await ctx.respond(hikari.ResponseType.DEFERRED_MESSAGE_CREATE)

    models = await GroupRoleModel.filter(guild_id=ctx.guild_id).all().prefetch_related("entries")
    if len(models) == 0:
        return await ctx.respond(embed=RespondEmbed.error("Group roles are missing"))
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
    await pages.send(ctx.interaction, responded=True)
