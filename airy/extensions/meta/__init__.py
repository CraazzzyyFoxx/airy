import datetime as dt
import logging
import platform
import time
import typing as t
from dataclasses import dataclass

import hikari
import lightbulb
from lightbulb import commands, context, decorators, plugins
from psutil import Process, virtual_memory
from pygount import SourceAnalysis

import airy
from airy.utils import chron
from airy.core import Airy

plugin = plugins.Plugin("Meta")

logger = logging.getLogger(__name__)


@dataclass
class CodeCounter:
    code: int = 0
    docs: int = 0
    empty: int = 0

    def count(self) -> "CodeCounter":
        for file in airy.ROOT_DIR.rglob("*.py"):
            analysis = SourceAnalysis.from_file(file, "pygount", encoding="utf-8")
            self.code += analysis.code_count
            self.docs += analysis.documentation_count
            self.empty += analysis.empty_count

        return self


@plugin.command
@decorators.command("ping", "Get the average DWSP latency for the bot.")
@decorators.implements(commands.slash.SlashCommand, commands.prefix.PrefixCommand)
async def cmd_ping(ctx: context.base.Context) -> None:
    await ctx.respond(
        f"Pong! DWSP latency: {ctx.bot.heartbeat_latency * 1_000:,.0f} ms."
    )


@plugin.command
@decorators.command("about", "View information about Airy.")
@decorators.implements(commands.slash.SlashCommand)
async def cmd_about(ctx: context.base.Context) -> None:
    if not (guild := ctx.get_guild()):
        return

    if not (me := guild.get_my_member()):
        return

    if not (member := ctx.member):
        return

    await ctx.respond(
        hikari.Embed(
            title="About Airy",
            description="Type `/stats` for bot runtime stats.",
            timestamp=dt.datetime.now().astimezone(),
        )
        .set_thumbnail(me.avatar_url)
        .set_author(name="Information")
        .set_footer(f"Requested by {member.display_name}", icon=member.avatar_url)
        .add_field("Author", f"<@{325216647872905216}>")
    )


@plugin.command
@decorators.command("stats", "View runtime stats for Airy.")
@decorators.implements(commands.slash.SlashCommand)
async def cmd_stats(ctx: context.base.Context) -> None:
    if not (guild := ctx.get_guild()):
        return

    if not (me := guild.get_my_member()):
        return

    if not (member := ctx.member):
        return

    with (proc := Process()).oneshot():
        uptime = chron.short_delta(
            dt.timedelta(seconds=time.time() - proc.create_time())
        )
        cpu_time = chron.short_delta(
            dt.timedelta(seconds=(cpu := proc.cpu_times()).system + cpu.user),
            ms=True,
        )
        mem_total = virtual_memory().total / (1024 ** 2)
        mem_of_total = proc.memory_percent()
        mem_usage = mem_total * (mem_of_total / 100)

    await ctx.respond(
        hikari.Embed(
            title="Runtime statistics for Airy",
            description="Type `/about` for general bot information.",
            timestamp=dt.datetime.now().astimezone(),
        )
        .set_thumbnail(me.avatar_url)
        .set_author(name="Information")
        .set_footer(f"Requested by {member.display_name}", icon=member.avatar_url)
        .add_field("Python version", platform.python_version(), inline=True)
        .add_field("Hikari version", hikari.__version__, inline=True)
        .add_field("Uptime", uptime, inline=True)
        .add_field("CPU time", cpu_time, inline=True)
        .add_field(
            "Memory usage",
            f"{mem_usage:,.3f}/{mem_total:,.0f} MiB ({mem_of_total:,.0f}%)",
            inline=True,
        )
        .add_field("Code lines", f"{ctx.bot.d.loc.code:,}", inline=True)
        .add_field("Docs lines", f"{ctx.bot.d.loc.docs:,}", inline=True)
        .add_field("Blank lines", f"{ctx.bot.d.loc.empty:,}", inline=True)
    )


@plugin.listener(lightbulb.events.CommandInvocationEvent)
async def command_invoke_listener(event: lightbulb.events.CommandInvocationEvent) -> None:
    logger.info(
        f"Command {event.command.name} was invoked by {event.context.author} in guild {event.context.guild_id}."
    )


def load(bot: Airy) -> None:
    if not bot.d.loc:
        bot.d.loc = CodeCounter().count()
    bot.add_plugin(plugin)


def unload(bot: Airy) -> None:
    bot.remove_plugin(plugin)
