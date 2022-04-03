from __future__ import annotations

import typing as t

import functools
import operator

import hikari
import lightbulb
from lightbulb import Check, checks


__all__ = ("is_mod",
           "is_admin",
           "mod_or_permissions",
           "admin_or_permissions",
           "is_above_target",
           "is_invoker_above_target",
           "has_permissions",
           "bot_has_permissions")

from airy.core.models.errors import BotRoleHierarchyError, RoleHierarchyError
from airy.utils import helpers

if t.TYPE_CHECKING:
    from airy.core.models.context import AiryContext


def _guild_only(ctx: AiryContext) -> bool:
    if not ctx.guild_id:
        raise lightbulb.OnlyInGuild("This command can only be used in a guild.")
    return True


def is_mod():
    return Check(functools.partial(checks._has_guild_permissions, perms=hikari.Permissions.MANAGE_GUILD))


def is_admin():
    return Check(functools.partial(checks._has_guild_permissions, perms=hikari.Permissions.ADMINISTRATOR))


def mod_or_permissions(*perms: hikari.Permissions):
    reduced = functools.reduce(operator.or_, [hikari.Permissions.MANAGE_GUILD, *perms])
    return Check(functools.partial(checks._has_guild_permissions, perms=reduced))


def admin_or_permissions(*perms: hikari.Permissions):
    reduced = functools.reduce(operator.or_, [hikari.Permissions.ADMINISTRATOR, *perms])
    return Check(functools.partial(checks._has_guild_permissions, perms=reduced))


@lightbulb.Check  # type: ignore
async def is_above_target(ctx: AiryContext) -> bool:
    """Check if the targeted user is above the bot's top role or not.
    Used in the moderation extension."""

    if not hasattr(ctx.options, "user"):
        return True

    if not ctx.guild_id:
        return True

    me = ctx.app.cache.get_member(ctx.guild_id, ctx.app.user_id)
    assert me is not None

    if isinstance(ctx.options.user, hikari.Member):
        member = ctx.options.user
    else:
        member = ctx.app.cache.get_member(ctx.guild_id, ctx.options.user)

    if not member:
        return True

    if helpers.is_above(me, member):
        return True

    raise BotRoleHierarchyError("Target user top role is higher than bot.")


@lightbulb.Check  # type: ignore
async def is_invoker_above_target(ctx: AiryContext) -> bool:
    """Check if the targeted user is above the invoker's top role or not.
    Used in the moderation extension."""

    if not hasattr(ctx.options, "user"):
        return True

    if not ctx.member or not ctx.guild_id:
        return True

    guild = ctx.get_guild()
    assert guild is not None

    if ctx.member.id == guild.owner_id:
        return True

    if isinstance(ctx.options.user, hikari.Member):
        member = ctx.options.user
    else:
        member = ctx.app.cache.get_member(ctx.guild_id, ctx.options.user)

    if not member:
        return True

    if helpers.is_above(ctx.member, member):
        return True

    raise RoleHierarchyError("Target user top role is higher than author.")


async def _has_permissions(ctx: AiryContext, *, perms: hikari.Permissions) -> bool:
    _guild_only(ctx)
    try:
        channel, guild = (ctx.get_channel() or await ctx.app.rest.fetch_channel(ctx.channel_id)), ctx.get_guild()
    except hikari.ForbiddenError:
        raise lightbulb.BotMissingRequiredPermission(
            "Check cannot run due to missing permissions.", perms=hikari.Permissions.VIEW_CHANNEL
        )

    if guild is None:
        raise lightbulb.InsufficientCache("Some objects required for this check could not be resolved from the cache.")
    if guild.owner_id == ctx.author.id:
        return True

    assert ctx.member is not None

    if isinstance(channel, hikari.GuildThreadChannel):
        channel = ctx.app.cache.get_guild_channel(channel.parent_id)

    assert isinstance(channel, hikari.GuildChannel)

    missing_perms = ~lightbulb.utils.permissions_in(channel, ctx.member) & perms
    if missing_perms is not hikari.Permissions.NONE:
        raise lightbulb.MissingRequiredPermission(
            "You are missing one or more permissions required in order to run this command", perms=missing_perms
        )

    return True


async def _bot_has_permissions(ctx: AiryContext, *, perms: hikari.Permissions) -> bool:
    _guild_only(ctx)
    try:
        channel, guild = (ctx.get_channel() or await ctx.app.rest.fetch_channel(ctx.channel_id)), ctx.get_guild()
    except hikari.ForbiddenError:
        raise lightbulb.BotMissingRequiredPermission(
            "Check cannot run due to missing permissions.", perms=hikari.Permissions.VIEW_CHANNEL
        )

    if guild is None:
        raise lightbulb.InsufficientCache("Some objects required for this check could not be resolved from the cache.")
    member = guild.get_my_member()
    if member is None:
        raise lightbulb.InsufficientCache("Some objects required for this check could not be resolved from the cache.")
    if guild.owner_id == ctx.author.id:
        return True

    if isinstance(channel, hikari.GuildThreadChannel):
        channel = ctx.app.cache.get_guild_channel(channel.parent_id)

    assert isinstance(channel, hikari.GuildChannel)

    missing_perms = ~lightbulb.utils.permissions_in(channel, member) & perms
    if missing_perms is not hikari.Permissions.NONE:
        raise lightbulb.BotMissingRequiredPermission(
            "The bot is missing one or more permissions required in order to run this command", perms=missing_perms
        )

    return True


def has_permissions(perm1: hikari.Permissions, *perms: hikari.Permissions) -> lightbulb.Check:
    """Just a shitty attempt at making has_guild_permissions fetch the channel if it is not present."""
    reduced = functools.reduce(operator.or_, [perm1, *perms])
    return lightbulb.Check(functools.partial(_has_permissions, perms=reduced))


def bot_has_permissions(perm1: hikari.Permissions, *perms: hikari.Permissions) -> lightbulb.Check:
    """Just a shitty attempt at making bot_has_guild_permissions fetch the channel if it is not present."""
    reduced = functools.reduce(operator.or_, [perm1, *perms])
    return lightbulb.Check(functools.partial(_bot_has_permissions, perms=reduced))