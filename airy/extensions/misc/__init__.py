
import logging

import hikari
import lightbulb
from lightbulb import plugins

from airy.core import Airy, AirySlashContext
from airy.etc import ColorEnum

misc = plugins.Plugin("Misc")

logger = logging.getLogger(__name__)


@misc.command
@lightbulb.command("ping", "Check the bot's latency.")
@lightbulb.implements(lightbulb.SlashCommand)
async def ping(ctx: AirySlashContext) -> None:
    embed = hikari.Embed(
        title="🏓 Pong!",
        description=f"Latency: `{round(ctx.app.heartbeat_latency * 1000)}ms`",
        color=ColorEnum.MISC,
    )
    await ctx.respond(embed=embed)


# @misc.command
# @decorators.command("about", "View information about Airy.")
# @decorators.implements(commands.slash.SlashCommand)
# async def cmd_about(ctx: context.base.Context) -> None:
#     if not (guild := ctx.get_guild()):
#         return
#
#     if not (me := guild.get_my_member()):
#         return
#
#     if not (member := ctx.member):
#         return
#
#     await ctx.respond(
#         hikari.Embed(
#             title="About Airy",
#             description="Type `/stats` for bot runtime stats.",
#             timestamp=dt.datetime.now().astimezone(),
#         )
#         .set_thumbnail(me.avatar_url)
#         .set_author(name="Information")
#         .set_footer(f"Requested by {member.display_name}", icon=member.avatar_url)
#         .add_field("Author", f"<@{325216647872905216}>")
#     )
#
#
# @misc.command
# @decorators.command("stats", "View runtime stats for Airy.")
# @decorators.implements(commands.slash.SlashCommand)
# async def cmd_stats(ctx: context.base.Context) -> None:
#     if not (guild := ctx.get_guild()):
#         return
#
#     if not (me := guild.get_my_member()):
#         return
#
#     if not (member := ctx.member):
#         return
#
#     with (proc := Process()).oneshot():
#         uptime = chron.short_delta(
#             dt.timedelta(seconds=time.time() - proc.create_time())
#         )
#         cpu_time = chron.short_delta(
#             dt.timedelta(seconds=(cpu := proc.cpu_times()).system + cpu.user),
#             ms=True,
#         )
#         mem_total = virtual_memory().total / (1024 ** 2)
#         mem_of_total = proc.memory_percent()
#         mem_usage = mem_total * (mem_of_total / 100)
#
#     await ctx.respond(
#         hikari.Embed(
#             title="Runtime statistics for Airy",
#             description="Type `/about` for general bot information.",
#             timestamp=dt.datetime.now().astimezone(),
#         )
#         .set_thumbnail(me.avatar_url)
#         .set_author(name="Information")
#         .set_footer(f"Requested by {member.display_name}", icon=member.avatar_url)
#         .add_field("Uptime", uptime, inline=True)
#         .add_field("CPU time", cpu_time, inline=True)
#         .add_field(
#             "Memory usage",
#             f"{mem_usage:,.3f}/{mem_total:,.0f} MiB ({mem_of_total:,.0f}%)",
#             inline=True,
#         )
#         .add_field("Code lines", f"{ctx.bot.d.loc.code:,}", inline=True)
#         .add_field("Docs lines", f"{ctx.bot.d.loc.docs:,}", inline=True)
#         .add_field("Blank lines", f"{ctx.bot.d.loc.empty:,}", inline=True)
#     )


def load(bot: Airy) -> None:
    bot.add_plugin(misc)


def unload(bot: Airy) -> None:
    bot.remove_plugin(misc)
