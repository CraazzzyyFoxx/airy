import logging

import lightbulb

from airy.core import Airy, AiryPlugin
from airy.utils import pass_options

log = logging.getLogger(__name__)

plugin = AiryPlugin(name="Admin")


@plugin.command
@lightbulb.add_checks(lightbulb.owner_only)
@lightbulb.command("shutdown", "Shut Airy down.", ephemeral=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def cmd_shutdown(ctx: lightbulb.SlashContext) -> None:
    log.info("Shutdown signal received")
    await ctx.respond("Now shutting down.")
    await ctx.bot.close()


@plugin.command
@lightbulb.add_checks(lightbulb.owner_only)
@lightbulb.command("reload", "Reloads Airy", ephemeral=True)
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def cmd_reload(_: lightbulb.SlashContext) -> None:
    pass


@cmd_reload.child()
@lightbulb.add_checks(lightbulb.owner_only)
@lightbulb.option('extension', 'Extension name', type=str, required=True)
@lightbulb.command("ext", "Reloads Airy Extension", ephemeral=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
@pass_options("ext")
async def cmd_reload_ext(ctx: lightbulb.SlashContext, extension: str) -> None:
    log.info("Shutdown signal received")
    await ctx.respond("Now shutting down.")
    ctx.bot.reload_extensions(f'airy.extensions.{extension}')


def load(bot: Airy) -> None:
    bot.add_plugin(plugin)


def unload(bot: Airy) -> None:
    bot.remove_plugin(plugin)
