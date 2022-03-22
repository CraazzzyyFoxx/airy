import typing as t

import hikari
import lightbulb

from airy.core import Airy, ActionMenusModel, AiryPlugin
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


# @plugin.command()
# @lightbulb.command("roles", "Manages Roles.")
# @lightbulb.implements(lightbulb.SlashCommandGroup)
# async def roles_cmd(_: lightbulb.Context):
#     pass
#
#
# @roles_cmd.child()
# @lightbulb.command("interaction", "Manages Interaction Roles.")
# @lightbulb.implements(lightbulb.SlashSubGroup)
# async def roles_interaction_cmd(_: lightbulb.Context):
#     pass
#
#
# @roles_interaction_cmd.child()
# @lightbulb.option('text', "Message text.",
#                   required=False,
#                   modifier=lightbulb.OptionModifier.CONSUME_REST,
#                   )
# @lightbulb.option('channel', "Text Channel",
#                   required=True,
#                   type=hikari.OptionType.CHANNEL,
#                   channel_types=[hikari.ChannelType.GUILD_TEXT])
# @lightbulb.command("create", "Create Interaction Roles.")
# @lightbulb.implements(lightbulb.SlashSubCommand)
# @pass_options('create')
# async def roles_interaction_create_cmd(ctx: lightbulb.Context, text: hikari.Message, channel: hikari.GuildTextChannel):
#     embed = EmbedConstructor()
#     await embed.start(ctx)


# @plugin.command()
# @lightbulb.command("test", "Test Embed Creator")
# @lightbulb.implements(lightbulb.SlashCommand)
# async def roles_cmd(ctx: lightbulb.SlashContext):
#     embed = EmbedConstructor()
#     await embed.start(ctx)


# def load(bot: Airy):
#     bot.add_plugin(plugin)
#
#
# def unload(bot: Airy):
#     bot.remove_plugin(plugin)
