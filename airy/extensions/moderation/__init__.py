import datetime

import lightbulb
import hikari

from lightbulb.utils import pag, nav
from tortoise.expressions import Q

from airy.extensions.moderation.convertors import ActionReason
from airy import utils
from airy.utils.timers import MuteEvent
from airy.core.models import GuildModel, ReminderModel
from airy.core import AirySlashContext

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
                                             deny=hikari.Permissions.SEND_MESSAGES |
                                                  hikari.Permissions.ADD_REACTIONS,
                                             reason=reason)
            elif channel.type == hikari.ChannelType.GUILD_VOICE:
                await channel.edit_overwrite(role,
                                             target_type=hikari.PermissionOverwriteType.ROLE,
                                             deny=hikari.Permissions.USE_VOICE_ACTIVITY | hikari.Permissions.SPEAK,
                                             reason=reason)
        except Exception:
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
    lightbulb.checks.has_guild_permissions(hikari.Permissions.BAN_MEMBERS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.BAN_MEMBERS)
)
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.UserBucket)
@lightbulb.option("reason", "the reason for banning the member", str, required=False,
                  modifier=lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.option("delete_message",
                  "Delete the messages after the ban? (up to 7 days, leave empty or set to 0 to not delete)", int,
                  min_value=0, max_value=7, default=0, required=False)
@lightbulb.option("user", "the user you want to ban", hikari.User, required=True)
@lightbulb.command("ban", "ban a member", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def member_ban(ctx: AirySlashContext, user: hikari.User, delete_message: int, reason: str):
    res = reason or f"'No Reason Provided.' By {ctx.author.username}"
    delete = delete_message or 0
    await ctx.respond(f"Banning **{user.username}**")
    await ctx.bot.rest.ban_member(user=user, guild=ctx.get_guild(), reason=res, delete_message_days=delete)
    await ctx.edit_last_response(f"Successfully banned `{user}` for `{res}`!")


@member_cmd.child()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.BAN_MEMBERS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.BAN_MEMBERS)
)
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.UserBucket)
@lightbulb.option("reason", "the reason for unbanning the member", str, required=False,
                  modifier=lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.option("user", "the user you want to unban (Please use their user ID)", hikari.Snowflake, required=True)
@lightbulb.command("unban", "unban a member", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def member_unban(ctx: AirySlashContext, user, reason):
    res = reason or f"'No Reason Provided.' By {ctx.author.username}"
    await ctx.respond(f"Unbanning the user ID of **{user}**")
    await ctx.bot.rest.unban_member(user=user, guild=ctx.get_guild(), reason=res)
    await ctx.edit_last_response(f"Successfully unbanned the ID of `{user}` for `{res}`!")


@member_cmd.child()
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.UserBucket)
@lightbulb.command("banlist", "see the list of banned members in this server", auto_defer=True, pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def member_banlist(ctx: AirySlashContext):
    bans = await ctx.bot.rest.fetch_bans(ctx.get_guild())
    lst = pag.EmbedPaginator()

    @lst.embed_factory()
    def build_embed(_, page_content):
        emb = hikari.Embed(title="List of Banned Members", description=page_content)
        emb.set_footer(f"{len(bans)} Members in total.")
        return emb

    for users in bans:
        lst.add_line(str(users.user))
    navigator = nav.ButtonNavigator(lst.build_pages())
    await navigator.run(ctx)


@member_cmd.child()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.KICK_MEMBERS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.KICK_MEMBERS)
)
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.UserBucket)
@lightbulb.option("reason", "the reason for kicking the member", str, required=False,
                  modifier=lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.option("user", "the user you want to kick", hikari.User, required=True)
@lightbulb.command("kick", "kick a member", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def kick(ctx: AirySlashContext, user, reason):
    res = reason or f"'No Reason Provided.' By {ctx.author.username}"
    await ctx.respond(f"Kicking **{user}**")
    await ctx.bot.rest.kick_member(user=user, guild=ctx.get_guild(), reason=res)
    await ctx.edit_last_response(f"Successfully kicked `{user}` for `{res}`!")


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
    """Unmutes members using the configured mute role.

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
        return await ctx.respond('Mute role missing', flags=hikari.MessageFlag.EPHEMERAL)
    await ctx.bot.rest.remove_role_from_member(ctx.guild_id, user, reason=reason, role=guild_config.mute_role_id)
    _ = (await ReminderModel
         .filter(Q(event='mute') & Q(extra__contains={"args": [ctx.author.id]}))
         .delete())

    await ctx.respond('Successfully unmute member')


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

    reminder = ctx.bot.get_plugin('Reminder')
    if reminder is None:
        return await ctx.respond('Sorry, this functionality is currently unavailable. Try again later?',
                                 flags=hikari.MessageFlag.EPHEMERAL)

    config = await GuildModel.filter(guild_id=ctx.guild_id).first()

    if config and not config.mute_role_id:
        return await ctx.respond('Mute role missing', flags=hikari.MessageFlag.EPHEMERAL)

    await ctx.bot.rest.add_role_to_member(ctx.guild_id, user, config.mute_role_id, reason=reason)

    config.muted_members.append(user.id)
    await config.save()

    duration = await utils.UserFriendlyTime(ctx).convert(duration)
    await reminder.create_timer(MuteEvent, duration, ctx.author.id, user.id, ctx.guild_id, config.mute_role_id)
    await ctx.respond(f'Muted {user} for {utils.format_relative(duration)}.')


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

    duration = await utils.UserFriendlyTime(ctx).convert(duration)

    if duration > (utils.utcnow() + datetime.timedelta(days=1)):
        return await ctx.respond('Duration is too long. Must be at most 24 hours.',
                                 flags=hikari.MessageFlag.EPHEMERAL)

    if duration < (utils.utcnow() + datetime.timedelta(minutes=5)):
        return await ctx.respond('Duration is too short. Must be at least 5 minutes.',
                                 flags=hikari.MessageFlag.EPHEMERAL)

    delta = utils.human_timedelta(duration, source=utils.utcnow())
    reason = f'Self-mute for {ctx.author} (ID: {ctx.author.id}) for {delta}'
    await ctx.bot.rest.add_role_to_member(ctx.guild_id, ctx.author.id, config.mute_role_id, reason=reason)

    await reminder.create_timer(MuteEvent,
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
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def channel_purge_messages(ctx: lightbulb.Context, amount: int) -> None:
    channel = ctx.channel_id

    # If the command was invoked using the PrefixCommand, it will create a message
    # before we purge the messages, so you want to delete this message first
    if isinstance(ctx, lightbulb.PrefixContext):
        await ctx.event.message.delete()

    msgs = await ctx.bot.rest.fetch_messages(channel).limit(amount)
    await ctx.bot.rest.delete_messages(channel, msgs)

    await ctx.respond(f"**{len(msgs)} messages deleted**", delete_after=5)


@channel_cmd.child()
@lightbulb.add_checks(
    lightbulb.checks.has_guild_permissions(hikari.Permissions.MANAGE_CHANNELS),
    lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.MANAGE_CHANNELS)
)
@lightbulb.option("interval", "The interval amount (in seconds)", int, min_value=0, max_value=21600, required=False)
@lightbulb.option("channel", "The channel you want to set", hikari.GuildChannel, required=True)
@lightbulb.command("slowmode", "Set the slowmode interval for a channel", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def channel_slowmode(ctx: lightbulb.Context, channel, interval):
    time = interval or 0
    if time == 0:
        await ctx.respond(f"Removing slow mode from the selected channel")
    else:
        await ctx.respond(f"Attempting to set slowmode on the selected channel for **{time} seconds**")
    await ctx.bot.rest.edit_channel(channel, rate_limit_per_user=time)
    await ctx.edit_last_response("Task Finished Successfully!")


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
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def channel_timeout(ctx: lightbulb.Context, user, reason, time: utils.UserFriendlyTime = 0):
    if time == 0:
        await ctx.respond(f"Removing timeout from **{user}**")
    else:
        now = utils.utcnow()
        time = await time.convert(ctx.options.time)

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
