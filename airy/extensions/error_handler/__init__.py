from __future__ import annotations

import asyncio
import datetime
import logging
import traceback
import typing as t

import hikari
import lightbulb

from airy.core import Airy, AiryContext, AirySlashContext, AiryPrefixContext
from airy.core.models.errors import *
from airy.utils import helpers, RespondEmbed
from airy.etc.perms_str import get_perm_str
from airy.config import bot_config

logger = logging.getLogger(__name__)

ch = lightbulb.Plugin("Command Handler")


async def log_exc_to_channel(
        error_str: str, ctx: t.Optional[lightbulb.Context] = None, event: t.Optional[hikari.ExceptionEvent] = None
) -> None:
    """Log an exception traceback to the specified logging channel.

    Parameters
    ----------
    error_str : str
        The exception message to print.
    ctx : t.Optional[lightbulb.Context], optional
        The context to use for additional information, by default None
    event : t.Optional[hikari.ExceptionEvent], optional
        The event to use for additional information, by default None
    """

    error_lines = error_str.split("\n")
    paginator = lightbulb.utils.StringPaginator(max_chars=2000, prefix="```py\n", suffix="```")
    if ctx:
        if guild := ctx.get_guild():
            assert ctx.command is not None
            paginator.add_line(
                f"Error in '{guild.name}' ({ctx.guild_id}) during command '{ctx.command.name}' executed by user '{ctx.author}' ({ctx.author.id})\n"
            )

    elif event:
        paginator.add_line(
            f"Ignoring exception in listener for {event.failed_event.__class__.__name__}, callback {event.failed_callback.__name__}:\n"
        )
    else:
        paginator.add_line(f"Uncaught exception:")

    for line in error_lines:
        paginator.add_line(line)

    assert isinstance(ch.app, Airy)
    channel_id = bot_config.errors_trace_channel

    if not channel_id:
        return

    for page in paginator.build_pages():
        try:
            await ch.app.rest.create_message(channel_id, page)
        except Exception as error:
            logging.error(f"Failed sending traceback to error-logging channel: {error}")


async def application_error_handler(ctx: AiryContext, error: lightbulb.LightbulbError) -> None:
    if isinstance(error, lightbulb.CheckFailure):
        if error.causes:
            cause = error.causes[0]
        else:
            cause = error.__cause__

        if isinstance(cause, UserBlacklistedError):
            await ctx.respond(embed=RespondEmbed.error(title="Application access terminated"),
                              flags=hikari.MessageFlag.EPHEMERAL)
            return

        if isinstance(cause, lightbulb.MissingRequiredPermission):
            embed = RespondEmbed.error(title="Missing Permissions",
                                       description=f"You require "
                                                   f"`{get_perm_str(cause.missing_perms).replace('|', ', ')}` "
                                                   f"permissions to execute this command.", )
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

        if isinstance(cause, lightbulb.BotMissingRequiredPermission):
            embed = RespondEmbed.error(title="Bot Missing Permissions",
                                       description=f"The bot requires "
                                                   f"`{get_perm_str(cause.missing_perms).replace('|', ', ')}` "
                                                   f"permissions to execute this command.", )
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

        if isinstance(cause, NoVoiceChannel):
            embed = RespondEmbed.error(title="You not in voice channel",
                                       description=f"You must be in the same channel with bot")
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

        if isinstance(cause, MissingPermissionsToEditPlayer):
            embed = RespondEmbed.error(title="You don't have permissions to interact with player ",
                                       description="This can be done by Administrators and people "
                                                   "whose track is currently playing."
                                       "But this does not apply to the `play` command.")
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

    # These may be raised outside of a check too
    if isinstance(error, lightbulb.MissingRequiredPermission):
        embed = RespondEmbed.error(title="Missing Permissions",
                                   description=f"You require "
                                               f"`{get_perm_str(error.missing_perms).replace('|', ', ')}` "
                                               f"permissions to execute this command.", )
        await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return

    if isinstance(error, lightbulb.BotMissingRequiredPermission):
        embed = RespondEmbed.error(title="Bot Missing Permissions",
                                   description=f"The bot requires "
                                               f"`{get_perm_str(error.missing_perms).replace('|', ', ')}` "
                                               f"permissions to execute this command.", )
        await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return

    if isinstance(error, lightbulb.CommandIsOnCooldown):
        embed = RespondEmbed.cooldown(title="Cooldown Pending",
                                      description=f"Please retry in: "
                                                  f"`{datetime.timedelta(seconds=round(error.retry_after))}`", )
        await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return

    if isinstance(error, lightbulb.MaxConcurrencyLimitReached):
        embed = RespondEmbed.cooldown(title="Max Concurrency Reached",
                                      description=f"You have reached the maximum amount of running instances for this "
                                                  f"command. Please try again later.", )
        await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return

    if isinstance(error, BotRoleHierarchyError):
        embed = RespondEmbed.error(title="Role Hierarchy Error",
                                   description=f"The targeted user's highest role is higher "
                                               f"than the bot's highest role.", )
        await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return

    if isinstance(error, RoleHierarchyError):
        embed = RespondEmbed.error(title="Role Hierarchy Error",
                                   description=f"The targeted user's highest role is higher "
                                               f"than the your highest role.")
        await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return

    if isinstance(error, lightbulb.CommandInvocationError):
        if isinstance(error.original, asyncio.TimeoutError):
            embed = RespondEmbed.error(title="Action timed out",
                                       description=f"This command timed out.", )
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

        elif isinstance(error.original, hikari.InternalServerError):
            embed = RespondEmbed.error(title="Discord Server Error",
                                       description="This action has failed due to an issue with Discord's servers. "
                                                   "Please try again in a few moments.")
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

        elif isinstance(error.original, hikari.ForbiddenError):
            embed = RespondEmbed.error(title="Forbidden",
                                       description=f"This action has failed due to a lack of permissions."
                                                   f"\n**Error:** ```{error.original}```", )
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

        elif isinstance(error.original, RoleHierarchyError):
            embed = RespondEmbed.error(title="Role Hiearchy Error",
                                       description=f"This action failed due to trying to modify "
                                                   f"a user with a role higher or equal to your highest role.", )

            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

        elif isinstance(error.original, BotRoleHierarchyError):
            embed = RespondEmbed.error(title="Role Hiearchy Error",
                                       description=f"This action failed due to trying to modify "
                                                   f"a user with a role higher than the bot's highest role.", )
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

        if isinstance(error.original, MemberExpectedError):
            embed = RespondEmbed.error(title="Member Expected",
                                       description=f"Expected a user who is a member of this server.", )
            await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

    assert ctx.command is not None

    logging.error("Ignoring exception in command {}:".format(ctx.command.name))
    exception_msg = "\n".join(traceback.format_exception(type(error), error, error.__traceback__))
    logging.error(exception_msg)
    error = error.original if hasattr(error, "original") else error

    embed = RespondEmbed.error(title="Unhandled exception",
                               description=f"An error happened that should not have happened. "
                                           f"Please [contact us](https://discord.gg/J4Dy8dTARf) "
                                           f"with a screenshot of this message!\n"
                                           f"**Error:** ```{error.__class__.__name__}: {error}```", )

    embed.set_footer(text=f"Guild: {ctx.guild_id}")
    await log_exc_to_channel(exception_msg, ctx)

    await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)


@ch.listener(lightbulb.UserCommandErrorEvent)
@ch.listener(lightbulb.MessageCommandErrorEvent)
@ch.listener(lightbulb.SlashCommandErrorEvent)
async def application_command_error_handler(event: lightbulb.CommandErrorEvent) -> None:
    assert isinstance(event.context, AirySlashContext)
    await application_error_handler(event.context, event.exception)


@ch.listener(lightbulb.UserCommandCompletionEvent)
@ch.listener(lightbulb.SlashCommandCompletionEvent)
@ch.listener(lightbulb.MessageCommandCompletionEvent)
async def application_command_completion_handler(event: lightbulb.events.CommandCompletionEvent):
    if event.context.author.id in event.context.app.owner_ids:  # Ignore cooldowns for owner c:
        if cm := event.command.cooldown_manager:
            await cm.reset_cooldown(event.context)


@ch.listener(lightbulb.PrefixCommandErrorEvent)
async def prefix_error_handler(event: lightbulb.PrefixCommandErrorEvent) -> None:
    if isinstance(event.exception, lightbulb.CheckFailure):
        return

    error = event.exception.original if hasattr(event.exception, "original") else event.exception  # type: ignore
    embed = RespondEmbed.error(title="Exception encountered",
                               description=f"```{error}```")
    await event.context.respond(embed=embed)
    raise event.exception


@ch.listener(lightbulb.events.CommandInvocationEvent)
async def command_invoke_listener(event: lightbulb.events.CommandInvocationEvent) -> None:
    logger.info(
        f"Command {event.command.name} was invoked by {event.context.author} in guild {event.context.guild_id}."
    )


@ch.listener(lightbulb.PrefixCommandInvocationEvent)
async def prefix_command_invoke_listener(event: lightbulb.PrefixCommandInvocationEvent) -> None:
    if event.context.guild_id:
        assert isinstance(event.app, Airy)
        me = event.app.cache.get_member(event.context.guild_id, event.app.user_id)
        assert me is not None

        if not helpers.includes_permissions(lightbulb.utils.permissions_for(me), hikari.Permissions.ADD_REACTIONS):
            return

    assert isinstance(event.context, AiryPrefixContext)
    await event.context.event.message.add_reaction("▶️")


@ch.listener(hikari.ExceptionEvent)
async def event_error_handler(event: hikari.ExceptionEvent) -> None:
    logging.error("Ignoring exception in listener {}:".format(event.failed_event.__class__.__name__))
    exception_msg = "\n".join(traceback.format_exception(*event.exc_info))
    logging.error(exception_msg)
    await log_exc_to_channel(exception_msg, event=event)


def load(bot: Airy) -> None:
    bot.add_plugin(ch)


def unload(bot: Airy) -> None:
    bot.remove_plugin(ch)
