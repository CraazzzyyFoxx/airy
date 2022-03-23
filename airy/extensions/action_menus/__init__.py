import typing as t

import hikari
import lightbulb

from airy.core import Airy, ActionMenusModel, AiryPlugin, AirySlashContext
from airy.utils import EmbedConstructor


class RolesPlugin(AiryPlugin):
    def __init__(self):
        super().__init__()
        self.message_ids: t.List[hikari.Snowflake] = None  # type: ignore


plugin = RolesPlugin()


@plugin.listener(hikari.StartedEvent)
async def prepare_cache(_: hikari.StartedEvent):
    plugin.message_ids = await ActionMenusModel.all().values_list("message_id", flat=True)


@plugin.listener(hikari.InteractionCreateEvent)
async def on_component(event: hikari.InteractionCreateEvent):
    if not isinstance(event.interaction, hikari.ComponentInteraction):
        return
    if event.interaction.message.id not in plugin.message_ids:
        return


@plugin.command()
@lightbulb.command("actionmenus", "Manages Roles.")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def actionmenus(_: AirySlashContext):
    pass


@actionmenus.child()
@lightbulb.command("settings", "Manages Roles.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def actionmenus_settings(ctx: AirySlashContext):
    pass


# def load(bot: Airy):
#     bot.add_plugin(plugin)
#
#
# def unload(bot: Airy):
#     bot.remove_plugin(plugin)
