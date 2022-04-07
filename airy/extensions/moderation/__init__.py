import datetime

import hikari
import lightbulb
from tortoise.expressions import Q

from airy.core import GuildModel, TimerModel, AirySlashContext
from airy.core.scheduler.timers import MuteEvent
from airy.utils import human_timedelta, utcnow, format_relative, RespondEmbed
from .convertors import ActionReason

mod_plugin = lightbulb.Plugin("Moderation")


async def update_mute_role_permissions(ctx: lightbulb.SlashContext, role: hikari.Role):
    success = 0
    failure = 0
    skipped = 0
    reason = f'Action done by {ctx.author.username} (ID: {ctx.author.id})'

    guild = ctx.get_guild() or await ctx.bot.rest.fetch_guild(ctx.guild_id)

    for channel in guild.get_channels().values():
        try:
            if channel.type == hikari.ChannelType.GUILD_TEXT:
                await channel.edit_overwrite(role,
                                             target_type=hikari.PermissionOverwriteType.ROLE,
                                             deny=(hikari.Permissions.SEND_MESSAGES |
                                                   hikari.Permissions.ADD_REACTIONS),
                                             reason=reason)
            elif channel.type == hikari.ChannelType.GUILD_VOICE:
                await channel.edit_overwrite(role,
                                             target_type=hikari.PermissionOverwriteType.ROLE,
                                             deny=hikari.Permissions.USE_VOICE_ACTIVITY | hikari.Permissions.SPEAK,
                                             reason=reason)
        except (hikari.ForbiddenError, hikari.HTTPError, hikari.NotFoundError):
            failure += 1
        else:
            success += 1
    else:
        skipped += 1

    return success, failure, skipped


@mod_plugin.listener(MuteEvent)
async def on_tempmute_timer_complete(event: MuteEvent):
    guild = mod_plugin.bot.cache.get_guild(event.guild_id)
    if guild is None:
        # RIP
        return

    member: hikari.Member = mod_plugin.bot.cache.get_member(event.guild_id, event.muted_user_id)
    if member is None:
        try:
            member = await event.app.rest.fetch_member(event.guild_id, event.muted_user_id)
        except hikari.HTTPError:
            return

    if event.author_id != event.muted_user_id:
        moderator = mod_plugin.bot.cache.get_member(guild, event.muted_user_id)
        if moderator is None:
            try:
                moderator = await mod_plugin.bot.rest.fetch_member(guild, event.author_id)
            except hikari.HTTPError:
                # request failed somehow
                moderator = f'Mod ID {event.author_id}'
            else:
                moderator = f'{moderator} (ID: {event.author_id})'
        else:
            moderator = f'{moderator} (ID: {event.author_id})'

        reason = f'Automatic unmute from timer made on {event.created} by {moderator}.'
    else:
        reason = f'Expiring self-mute made on {event.created} by {member}'

    config = await GuildModel.filter(guild_id=event.guild_id).first()
    config.muted_members.remove(event.muted_user_id)
    await config.save()

    try:
        await mod_plugin.bot.rest.remove_role_from_member(guild, member, event.role_id, reason=reason)
    except hikari.HTTPError:
        pass


@mod_plugin.command()
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.UserBucket)
@lightbulb.command("member", "Commands for manage members", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def member_cmd(_: AirySlashContext):
    pass


@member_cmd.child()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MANAGE_ROLES),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS)
)
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.UserBucket)
@lightbulb.option("reason", "The reason for muting the member", str, required=False,
                  modifier=lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.option("user", "The user you want to mute", hikari.Member, required=True)
@lightbulb.command("unmute", "Unmute a member", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def member_unmute(ctx: AirySlashContext, user: hikari.Member, *, reason: ActionReason = None):
    """Unmute members using the configured mute role.

    The bot must have Manage Roles permission and be
    above the muted role in the hierarchy.

    To use this command you need to be higher than the
    mute role in the hierarchy and have Manage Roles
    permission at the server level.
    """

    if reason is None:
        reason = f'Action done by {ctx.author} (ID: {ctx.author.id})'

    guild_config = await GuildModel.filter(guild_id=ctx.guild_id).first()
    if guild_config and not guild_config.mute_role_id:
        return await ctx.respond(embed=RespondEmbed.error('Mute role missing'))
    await ctx.bot.rest.remove_role_from_member(ctx.guild_id, user, reason=reason, role=guild_config.mute_role_id)
    _ = (await TimerModel
         .filter(Q(event='mute') & Q(extra__contains={"args": [ctx.author.id]}))
         .delete())

    await ctx.respond(embed=RespondEmbed.success('Successfully unmute member'))


@member_cmd.child()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MANAGE_ROLES),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS)
)
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.UserBucket)
@lightbulb.option("reason", "The reason for muting the member", str, required=False,
                  modifier=lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.option("user", "The user you want to mute", hikari.Member, required=True)
@lightbulb.option("duration", "The duration of the mute", str, required=True,
                  modifier=lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.command("tempmute", "Temporarily mutes a member for the specified duration.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def tempmute(ctx: AirySlashContext,
                   duration: str,
                   user: hikari.Member,
                   *,
                   reason: ActionReason = None):
    """Temporarily mutes a member for the specified duration.

    The duration can be a short time form, e.g. 30d or a more human
    duration such as "until thursday at 3PM" or a more concrete time
    such as "2024-12-31".

    Note that time are in UTC.

    This has the same permissions as the `mute` command.
    """
    if reason is None:
        reason = f'Action done by {ctx.author} (ID: {ctx.author.id})'

    config = await GuildModel.filter(guild_id=ctx.guild_id).first()

    if config and not config.mute_role_id:
        return await ctx.respond('Mute role missing', flags=hikari.MessageFlag.EPHEMERAL)

    await ctx.bot.rest.add_role_to_member(ctx.guild_id, user, config.mute_role_id, reason=reason)

    config.muted_members.append(user.id)
    await config.save()

    duration = await ctx.bot.scheduler.convert_time(duration)
    await ctx.bot.scheduler.create_timer(MuteEvent, duration, ctx.author.id, user.id, ctx.guild_id, config.mute_role_id)
    await ctx.respond(f'Muted {user} for {format_relative(duration)}.')


@member_cmd.child()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MANAGE_ROLES),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS)
)
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.UserBucket)
@lightbulb.option("reason", "The reason for muting the member", str, required=False,
                  modifier=lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.option("user", "The user you want to mute", hikari.Member, required=True)
@lightbulb.command("mute", "Mute a member", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def member_mute(ctx: AirySlashContext,
                      user: hikari.User,
                      reason: ActionReason = None):
    """Mutes members using the configured mute role.

    The bot must have Manage Roles permission and be
    above the muted role in the hierarchy.

    To use this command you need to be higher than the
    mute role in the hierarchy and have Manage Roles
    permission at the server level.
    """

    config = await GuildModel.filter(guild_id=ctx.guild_id).first()
    if config is None or not config.mute_role_id:
        return await ctx.respond('Mute role missing', flags=hikari.MessageFlag.EPHEMERAL)

    if reason is None:
        reason = f'Action done by {ctx.author.username} (ID: {ctx.author.id})'

    config.muted_members.append(user.id)
    await config.save()

    await ctx.bot.rest.add_role_to_member(ctx.guild_id, user, reason=reason, role=config.mute_role_id)
    return await ctx.respond('Successfully muted member')


@member_cmd.child()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MANAGE_ROLES),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS)
)
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.GuildBucket)
@lightbulb.option("duration", "The duration of the mute", str, required=True)
@lightbulb.command("selfmute", "Temporarily mutes yourself for the specified duration.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def selfmute(ctx: AirySlashContext, duration: str):
    """Temporarily mutes yourself for the specified duration.

    The duration must be in a short time form, e.g. 4h. Can
    only mute yourself for a maximum of 24 hours and a minimum
    of 5 minutes.

    Do not ask a moderator to unmute you.
    """

    reminder = ctx.bot.get_plugin('Reminder')
    if reminder is None:
        return await ctx.respond('Sorry, this functionality is currently unavailable. Try again later?',
                                 flags=hikari.MessageFlag.EPHEMERAL)

    config = await GuildModel.filter(guild_id=ctx.guild_id).first()
    if config and not config.mute_role_id:
        return await ctx.respond('Mute role missing', flags=hikari.MessageFlag.EPHEMERAL)

    if ctx.author.id in config.muted_members:
        return await ctx.respond('Somehow you are already muted',
                                 flags=hikari.MessageFlag.EPHEMERAL)

    duration = await ctx.bot.scheduler.convert_time(duration)

    if duration > (utcnow() + datetime.timedelta(days=1)):
        return await ctx.respond('Duration is too long. Must be at most 24 hours.',
                                 flags=hikari.MessageFlag.EPHEMERAL)

    if duration < (utcnow() + datetime.timedelta(minutes=5)):
        return await ctx.respond('Duration is too short. Must be at least 5 minutes.',
                                 flags=hikari.MessageFlag.EPHEMERAL)

    delta = human_timedelta(duration, source=utcnow())
    reason = f'Self-mute for {ctx.author} (ID: {ctx.author.id}) for {delta}'
    await ctx.bot.rest.add_role_to_member(ctx.guild_id, ctx.author.id, config.mute_role_id, reason=reason)

    await ctx.bot.scheduler.create_timer(MuteEvent,
                                         duration,
                                         ctx.author.id,
                                         ctx.author.id,
                                         ctx.guild_id,
                                         config.mute_role_id)

    config.muted_members.append(ctx.author.id)
    await config.save()

    await ctx.respond(f'\N{OK HAND SIGN} Muted for {delta}. Be sure not to bother anyone about it.')


@mod_plugin.command()
@lightbulb.command("mute_role", "Shows configuration of the mute role.")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def _mute_role(_: lightbulb.SlashContext):
    pass


@_mute_role.child()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MANAGE_ROLES),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS)
)
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.GuildBucket)
@lightbulb.command("stats", "Shows configuration of the mute role.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def mute_role_stats(ctx: AirySlashContext):
    """Shows configuration of the mute role.

    To use these commands you need to have Manage Roles
    and Manage Server permission at the server level.
    """
    config = await GuildModel.filter(guild_id=ctx.guild_id).first()
    if not config:
        return ctx.respond('No mute role setup', flags=hikari.MessageFlag.EPHEMERAL)
    role = ctx.bot.cache.get_role(config.mute_role_id)
    if role is not None:
        total = len(config.muted_members)
        role = f'{role} (ID: {role.id})'
    else:
        total = 0
    await ctx.respond(f'Role: {role}\nMembers Muted: {total}')


@_mute_role.child()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MANAGE_ROLES),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS)
)
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.GuildBucket)
@lightbulb.command("update", "Updates the permission overwrites of the mute role.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def mute_role_update(ctx: AirySlashContext):
    """Updates the permission overwrites of the mute role.

    This works by blocking to Send Messages and Add Reactions
    permission on every text channel that the bot can do.

    To use these commands you need to have Manage Roles
    and Manage Server permission at the server level.
    """

    config = await GuildModel.filter(guild_id=ctx.guild_id).first()
    if config and config.mute_role_id is not None:

        role = ctx.bot.cache.get_role(config.mute_role_id) or \
               lightbulb.utils.find((await ctx.bot.rest.fetch_roles(ctx.guild_id)),
                                    predicate=lambda r: r.id == config.mute_role_id)
    else:
        return await ctx.respond('No mute role has been set up to update.', flags=hikari.MessageFlag.EPHEMERAL)

    await ctx.respond(flags=hikari.MessageFlag.LOADING)

    success, failure, skipped = await update_mute_role_permissions(ctx, role)
    total = success + failure + skipped
    await ctx.respond(f'Attempted to update {total} channel permissions. '
                      f'[Updated: {success}, Failed: {failure}, Skipped: {skipped}]')


@_mute_role.child()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MANAGE_ROLES),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS)
)
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.GuildBucket)
@lightbulb.option("name", "Role name", str, required=True,
                  modifier=lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.command("create", "Creates a mute role with the given name.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def mute_role_create(ctx: AirySlashContext, name: str):
    """Creates a mute role with the given name.

    This also updates the channel overwrites accordingly
    if wanted.

    To use these commands you need to have Manage Roles
    and Manage Server permission at the server level.
    """

    config = await GuildModel.filter(guild_id=ctx.guild_id).first()
    if config and config.mute_role_id is not None:
        return await ctx.respond('A mute role already exists.', flags=hikari.MessageFlag.EPHEMERAL)

    role = await ctx.bot.rest.create_role(ctx.guild_id,
                                          name=name,
                                          reason=f'Mute Role Created By {ctx.author} (ID: {ctx.author.id})')
    if config:
        config.mute_role_id = role.id
        await config.save(update_fields=['mute_role_id'])
    else:
        await GuildModel.create(guild_id=ctx.guild_id, mute_role_id=role.id)

    status = await ctx.confirm('Would you like to update the channel overwrites as well?')

    if status:
        return await ctx.respond('Mute role successfully created.')

    await ctx.edit_last_response("Processing...", flags=hikari.MessageFlag.LOADING, components=[])

    success, failure, skipped = await update_mute_role_permissions(ctx, role)
    await ctx.edit_last_response('Mute role successfully created. Overwrites: '
                                 f'[Updated: {success}, Failed: {failure}, Skipped: {skipped}]')


@_mute_role.child()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MANAGE_ROLES),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS)
)
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.GuildBucket)
@lightbulb.command("unbind", "Unbinds a mute role without deleting it.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def mute_role_unbind(ctx: AirySlashContext):
    """Unbinds a mute role without deleting it.

    To use these commands you need to have Manage Roles
    and Manage Server permission at the server level.
    """
    await GuildModel.filter(guild_id=ctx.guild_id).update(mute_role_id=None)
    await ctx.respond('Successfully unbound mute role.')


# =================================================================================


@mod_plugin.command()
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.UserBucket)
@lightbulb.command("channel", "Commands for manage channels")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def channel_cmd(_: lightbulb.Context):
    pass


@channel_cmd.child()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.MANAGE_CHANNELS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MANAGE_CHANNELS)
)
@lightbulb.option("amount", "The number of messages to purge.", type=int, required=True, max_value=500)
@lightbulb.command("purge", "Purge messages from this channel.", aliases=["clear", "prune"], pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def channel_purge_messages(ctx: lightbulb.Context, amount: int) -> None:
    channel = ctx.channel_id

    msgs = await ctx.bot.rest.fetch_messages(channel).limit(amount)
    await ctx.bot.rest.delete_messages(channel, msgs)

    await ctx.respond(f"**{len(msgs)} messages deleted**", delete_after=5)


@channel_cmd.child()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MODERATE_MEMBERS)
)
@lightbulb.option("reason", "the reason for the timeout", str, required=False,
                  modifier=lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.option("time", "the duration of the timeout", str, required=False,
                  modifier=lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.option("user", "the user you want to be put in timeout", hikari.User, required=True)
@lightbulb.command("timeout", "Timeout a member", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def channel_timeout(ctx: AirySlashContext, user: hikari.User, reason: str, time: str = None):
    if time is None:
        await ctx.respond(f"Removing timeout from **{user}**")
    else:
        now = utcnow()
        time = await ctx.bot.scheduler.convert_time(time)

        if (time - now).days > 28:
            await ctx.respond("You can't time someone out for more than 28 days")
            return

        await ctx.respond(f"Attempting to timeout **{user}**")

    await ctx.bot.rest.edit_member(user=user, guild=ctx.guild_id, communication_disabled_until=time, reason=reason)
    await ctx.edit_last_response("Task finished successfully!")


def load(bot):
    bot.add_plugin(mod_plugin)


def unload(bot):
    bot.remove_plugin(mod_plugin)
